#!/usr/bin/env python3
"""Independent bundle byte/signature verification; imports no factory modules.

An external public-key pin authenticates a signed manifest and its metadata.
Without that pin, PASS means internal byte consistency only. Local signatures
never establish OS isolation, label sealing, truthful telemetry or valid science.
"""
import argparse
import base64
import hashlib
import json
import math
import re
import stat
import sys
import zipfile
from pathlib import Path, PurePosixPath

MANIFEST = 'BUNDLE_MANIFEST.json'
SIGNATURE_FIELDS = {'supervisor_signature', 'signature_scheme', 'public_key_id'}


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def _unique(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError('duplicate JSON key: ' + key)
        obj[key] = value
    return obj


def _constant(value):
    raise ValueError('non-standard JSON constant: ' + value)


def _float(value):
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError('non-finite JSON number')
    return parsed


def _json(raw):
    return json.loads(raw, object_pairs_hook=_unique, parse_constant=_constant, parse_float=_float)


def _safe_name(name):
    path = PurePosixPath(name)
    return (bool(name) and not path.is_absolute() and '..' not in path.parts and '\\' not in name
            and ':' not in name and '\x00' not in name and str(path) == name and name != '.')


def _load_public(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError('public key must be a regular non-symlink file')
    lines = path.read_text(encoding='ascii').strip().splitlines()
    if len(lines) != 2 or lines[0].strip() != '# ed25519':
        raise ValueError('public key must use Ed25519; symmetric keys are not public verification keys')
    public = base64.b64decode(lines[1].strip(), validate=True)
    if len(public) != 32:
        raise ValueError('Ed25519 public key must contain 32 bytes')
    return public


def _verify_receipt_sig(receipt_data, pub_key_bytes, scheme='ed25519'):
    if not isinstance(receipt_data, dict):
        return False, 'signed payload must be an object'
    if scheme != 'ed25519' or receipt_data.get('signature_scheme') != 'ed25519':
        return False, 'receipt missing Ed25519 supervisor signature'
    if receipt_data.get('public_key_id') != sha256_bytes(pub_key_bytes)[:16]:
        return False, 'receipt signed by unknown supervisor key'
    try:
        signature = base64.b64decode(receipt_data.get('supervisor_signature', ''), validate=True)
        payload = {key: value for key, value in receipt_data.items() if key not in SIGNATURE_FIELDS}
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        Ed25519PublicKey.from_public_bytes(pub_key_bytes).verify(signature, canonical(payload))
    except Exception as ex:
        return False, 'Ed25519 signature verification failed: ' + str(ex)
    return True, None


def _check_record(record, public, files):
    # Historical flat receipts remain independently signature-checkable.
    nested = isinstance(record, dict) and 'supervisor_receipt' in record
    signed = record.get('supervisor_receipt') if nested else record
    ok, error = _verify_receipt_sig(signed, public)
    if not ok:
        return error
    if not nested:
        return None
    wrapper = {key: value for key, value in record.items() if key != 'supervisor_receipt'}
    if signed.get('execution_binding') != sha256_bytes(canonical(wrapper)):
        return 'execution wrapper differs from signed receipt'
    bindings = {
        'run_nonce': record.get('run_nonce'), 'epoch': record.get('epoch'),
        'experiment_id': record.get('experiment_id'), 'seed': record.get('seed'),
        'input_root': sha256_bytes(canonical(record.get('inputs_before'))),
        'inputs_after_root': sha256_bytes(canonical(record.get('inputs_after'))),
        'output_root': sha256_bytes(canonical(record.get('outputs'))),
        'engine_sha256': record.get('engine_sha256'),
        'launch_spec': sha256_bytes(canonical(record.get('argv_template', record.get('argv')))),
        'interpreter_hash': record.get('interpreter_hash'),
        'dependency_lock_hash': record.get('dependency_lock_hash'),
        'exit_status': record.get('exit_code'), 'started_at': record.get('started_at'),
        'finished_at': record.get('finished_at'), 'snapshot_merkle_root': record.get('snapshot_merkle_root'),
        'runtime_id': record.get('runtime_id', 'python-cpu-v1'),
        'supervisor_version': record.get('factory_version'),
    }
    for field, expected in bindings.items():
        if signed.get(field) != expected:
            return 'receipt binding mismatch: ' + field
    outputs = record.get('outputs')
    if not isinstance(outputs, dict):
        return 'execution outputs must be an object'
    for name, value in outputs.items():
        if files.get(name) != value:
            return 'receipt output missing or differs from archive: ' + str(name)
    return None


def verify_bundle(path, public_key_path=None, *, require_manifest_signature=False):
    """Verify bytes and optionally externally pinned manifest/receipt signatures."""
    errors = []
    checked = 0
    signatures = 0
    manifest_verified = False
    manifest = {}
    try:
        with zipfile.ZipFile(Path(path)) as archive:
            infos = archive.infolist()
            if len(infos)>100000 or sum(info.file_size for info in infos)>8*1024**3:
                raise ValueError('bundle exceeds member count or uncompressed byte limit')
            names = [info.filename for info in infos]
            if len(names) != len(set(names)):
                raise ValueError('duplicate members in archive')
            if MANIFEST not in names:
                raise ValueError('missing bundle manifest')
            for info in infos:
                if info.orig_filename != info.filename or not _safe_name(info.orig_filename):
                    raise ValueError('unsafe member name: ' + info.filename)
                mode = (info.external_attr >> 16) & 0o170000
                if info.is_dir() or mode not in (0, stat.S_IFREG):
                    raise ValueError('bundle contains non-regular file: ' + info.filename)
            if archive.getinfo(MANIFEST).file_size > 16 * 1024 * 1024:
                raise ValueError('manifest exceeds 16 MiB limit')
            candidate = _json(archive.read(MANIFEST))
            if (not isinstance(candidate, dict) or type(candidate.get('schema_version')) is not int or
                    candidate['schema_version'] != 1 or not isinstance(candidate.get('files'), dict)):
                raise ValueError('invalid bundle manifest schema')
            manifest = candidate
            files = manifest['files']
            if set(files) != set(names) - {MANIFEST}:
                raise ValueError('archive membership differs from manifest')
            for name, expected in files.items():
                if not isinstance(expected, str) or not re.fullmatch(r'[0-9a-f]{64}', expected):
                    raise ValueError('invalid digest in manifest: ' + name)
                h = hashlib.sha256()
                with archive.open(name) as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                        h.update(chunk)
                if h.hexdigest() != expected:
                    raise ValueError('hash mismatch: ' + name)
                checked += 1
            if require_manifest_signature and public_key_path is None:
                raise ValueError('an external public-key pin is required for authenticated verification')
            if public_key_path is not None:
                public = _load_public(public_key_path)
                if 'supervisor_signature' in manifest or require_manifest_signature:
                    if manifest.get('artifact_type') != 'factory_bundle_manifest':
                        raise ValueError('invalid manifest signature domain')
                    ok, error = _verify_receipt_sig(manifest, public)
                    if not ok:
                        raise ValueError('manifest signature: ' + str(error))
                    manifest_verified = True
                for name in sorted(files):
                    if name.endswith('/execution.json') or name == 'execution.json':
                        if archive.getinfo(name).file_size > 16 * 1024 * 1024:
                            raise ValueError('execution record exceeds 16 MiB limit')
                        error = _check_record(_json(archive.read(name)), public, files)
                        if error:
                            errors.append('invalid receipt signature/binding in ' + name + ': ' + error)
                        else:
                            signatures += 1
            level = manifest.get('assurance_level', 'STRUCTURALLY_VALIDATED')
            if manifest.get('trust_profile') == 'same_user_local' and level in {
                    'SUPERVISOR_ATTESTED', 'SEALED_EVALUATION_ATTESTED',
                    'INDEPENDENT_REVIEW_COMPLETE', 'READY_FOR_HUMAN_SUBMISSION_REVIEW'}:
                errors.append('assurance level exceeds the local execution trust boundary')
    except (OSError, ValueError, TypeError, KeyError, RuntimeError, NotImplementedError,
            UnicodeError, zipfile.BadZipFile) as ex:
        errors.append('invalid bundle: ' + str(ex))
    trusted = manifest_verified and not errors
    return {
        'status': 'PASS' if not errors else 'FAIL', 'files_checked': checked,
        'signatures_verified': signatures, 'manifest_signature_verified': manifest_verified,
        'authenticity_verified': trusted, 'metadata_trusted': trusted, 'errors': errors,
        'release_status': manifest.get('release_status', 'unknown') if trusted else 'UNVERIFIED_METADATA',
        'factory_version': manifest.get('factory_version', 'unknown'),
        'assurance_level': manifest.get('assurance_level', 'unknown') if trusted else 'UNVERIFIED_METADATA',
        'scope': ('externally pinned manifest and receipt signatures; byte integrity; local signing identity'
                  if trusted else 'byte consistency only; release and assurance claims are unverified'),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', help='Path to the bundle ZIP')
    parser.add_argument('--public-key', help='Externally trusted Ed25519 public key; requires signed manifest')
    args = parser.parse_args()
    result = verify_bundle(args.archive, args.public_key, require_manifest_signature=bool(args.public_key))
    print(json.dumps(result, indent=2))
    sys.exit(0 if result['status'] == 'PASS' else 1)


if __name__ == '__main__':
    main()
