#!/usr/bin/env python3
"""Standalone bundle verifier. Does NOT import gatekeeper or any engine module.

This is the independent verifier specified by the trust model: it must not use
the project's own gatekeeper.py to verify the gatekeeper's claims. It verifies:

  - ZIP membership and byte integrity
  - Bundle manifest schema
  - Receipt signatures (when keys are available)
  - Assurance level consistency

Usage:
    python3 verify_bundle_standalone.py <archive.zip> [--public-key <key.pub>]
"""
import argparse
import base64
import hashlib
import hmac
import json
import sys
import zipfile
from pathlib import Path

MANIFEST = 'BUNDLE_MANIFEST.json'


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':')).encode()


def _verify_receipt_sig(receipt_data, pub_key_bytes, scheme):
    if not isinstance(receipt_data, dict):
        return False, "receipt is not a JSON object"
    sig_b64 = receipt_data.get('supervisor_signature')
    rec_scheme = receipt_data.get('signature_scheme')
    if not sig_b64 or not rec_scheme:
        return False, "receipt missing supervisor signature or scheme"
    if rec_scheme != scheme:
        return False, f"signature scheme mismatch: receipt has {rec_scheme}, key is {scheme}"
    try:
        sig = base64.b64decode(sig_b64)
    except Exception:
        return False, "malformed base64 signature"
    to_verify = {k: v for k, v in receipt_data.items()
                 if k not in ('supervisor_signature', 'signature_scheme', 'public_key_id')}
    payload = canonical(to_verify)
    if scheme == 'ed25519':
        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
            pub = Ed25519PublicKey.from_public_bytes(pub_key_bytes)
            pub.verify(sig, payload)
            return True, None
        except Exception as e:
            return False, f"ed25519 signature verification failed: {e}"
    elif scheme == 'hmac-sha256':
        expected = hmac.new(pub_key_bytes, payload, hashlib.sha256).digest()
        if hmac.compare_digest(sig, expected):
            return True, None
        return False, "hmac signature mismatch"
    else:
        return False, f"unsupported signature scheme: {scheme}"


def verify_bundle(path, public_key_path=None):
    """Verify bundle integrity without importing any engine module."""
    errors = []
    path = Path(path)

    if not path.is_file():
        return {'status': 'FAIL', 'errors': ['archive not found']}

    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            names = [i.filename for i in infos]

            # Check for unsafe names
            for name in names:
                if not name or '..' in name or name.startswith('/') or '\\' in name:
                    errors.append(f'unsafe member name: {name}')

            # Duplicates
            if len(names) != len(set(names)):
                errors.append('duplicate members in archive')

            # Manifest present
            if MANIFEST not in names:
                errors.append('missing bundle manifest')
                return {'status': 'FAIL', 'errors': errors}

            # No symlinks or directories
            for info in infos:
                if info.is_dir() or (info.external_attr >> 16) & 0o170000 == 0o120000:
                    errors.append(f'bundle contains non-regular file: {info.filename}')

            # Size limit on manifest
            manifest_info = archive.getinfo(MANIFEST)
            if manifest_info.file_size > 16 * 1024 * 1024:
                errors.append('manifest exceeds 16 MiB limit')
                return {'status': 'FAIL', 'errors': errors}

            # Parse manifest
            raw = archive.read(MANIFEST)
            try:
                manifest = json.loads(raw)
            except json.JSONDecodeError as e:
                errors.append(f'invalid manifest JSON: {e}')
                return {'status': 'FAIL', 'errors': errors}

            if not isinstance(manifest, dict):
                errors.append('manifest must be an object')
                return {'status': 'FAIL', 'errors': errors}

            if manifest.get('schema_version') != 1:
                errors.append(f'unsupported schema_version: {manifest.get("schema_version")}')

            files = manifest.get('files')
            if not isinstance(files, dict):
                errors.append('manifest.files must be an object')
                return {'status': 'FAIL', 'errors': errors}

            # Membership check
            archive_members = set(names) - {MANIFEST}
            manifest_members = set(files.keys())
            extra_in_archive = archive_members - manifest_members
            extra_in_manifest = manifest_members - archive_members
            if extra_in_archive:
                errors.append(f'archive has unlisted members: {sorted(extra_in_archive)}')
            if extra_in_manifest:
                errors.append(f'manifest lists missing members: {sorted(extra_in_manifest)}')

            # Byte integrity
            for name, expected_hash in files.items():
                if name not in archive_members:
                    continue
                h = hashlib.sha256()
                with archive.open(name) as f:
                    for chunk in iter(lambda: f.read(1024 * 1024), b''):
                        h.update(chunk)
                if h.hexdigest() != expected_hash:
                    errors.append(f'hash mismatch: {name}')

            signatures_verified = 0
            if public_key_path and not errors:
                pk_path = Path(public_key_path)
                if not pk_path.is_file():
                    errors.append(f'public key file not found: {public_key_path}')
                else:
                    try:
                        pk_content = pk_path.read_text().strip()
                        lines = pk_content.splitlines()
                        scheme = 'hmac-sha256'
                        key_b64 = pk_content
                        if lines and lines[0].startswith('#'):
                            scheme = lines[0].lstrip('#').strip()
                            key_b64 = '\n'.join(lines[1:]).strip()
                        pub_bytes = base64.b64decode(key_b64)

                        for name in archive_members:
                            if name.endswith('execution.json'):
                                try:
                                    receipt_json = json.loads(archive.read(name))
                                    ok, msg = _verify_receipt_sig(receipt_json, pub_bytes, scheme)
                                    if not ok:
                                        errors.append(f'invalid receipt signature in {name}: {msg}')
                                    else:
                                        signatures_verified += 1
                                except Exception as e:
                                    errors.append(f'could not verify receipt in {name}: {e}')
                    except Exception as e:
                        errors.append(f'failed to load public key: {e}')

    except (zipfile.BadZipFile, OSError) as e:
        return {'status': 'FAIL', 'errors': [f'cannot open archive: {e}']}

    result = {
        'status': 'PASS' if not errors else 'FAIL',
        'files_checked': len(files) if not errors else 0,
        'signatures_verified': signatures_verified if not errors else 0,
        'errors': errors,
        'release_status': manifest.get('release_status', 'unknown'),
        'factory_version': manifest.get('factory_version', 'unknown'),
        'assurance_level': manifest.get('assurance_level', 'unknown'),
        'scope': 'standalone verification: membership, byte integrity, and supervisor signatures',
    }

    return result



def main():
    parser = argparse.ArgumentParser(description='Standalone bundle verifier')
    parser.add_argument('archive', help='Path to the bundle ZIP')
    parser.add_argument('--public-key', help='Path to supervisor public key')
    args = parser.parse_args()

    result = verify_bundle(args.archive, args.public_key)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result['status'] == 'PASS' else 1)


if __name__ == '__main__':
    main()
