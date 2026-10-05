"""Portable review archives with optional externally verifiable signatures.

Checksums alone establish byte consistency. A signed manifest authenticates its
metadata and file membership against a separately trusted public key, subject to
the disclosed local signing identity; it does not establish scientific validity.
"""
import hashlib
import json
import os
import re
import stat
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from .io import EvidenceError, sha, unique_object, reject_constant, finite_float
from .supervisor import sign_receipt, verify_receipt_signature

MANIFEST = 'BUNDLE_MANIFEST.json'
MAX_MEMBERS = 100000
MAX_UNCOMPRESSED_BYTES = 8 * 1024**3


def member_name(name):
    if not isinstance(name, str):
        raise EvidenceError('bundle member name must be a string')
    path = PurePosixPath(name)
    if (not name or path.is_absolute() or '..' in path.parts or '\\' in name or
            ':' in name or '\x00' in name or str(path) != name or name == '.'):
        raise EvidenceError('unsafe bundle member: ' + name)
    return name


def create_bundle(destination, files, metadata, *, sign_manifest=False):
    """Create an atomic archive; signing is explicit and fails closed."""
    destination = Path(destination)
    if not isinstance(files, dict) or not isinstance(metadata, dict):
        raise EvidenceError('bundle files and metadata must be objects')
    for name, path in files.items():
        member_name(name)
        path = Path(path)
        if path.is_symlink() or not stat.S_ISREG(path.stat().st_mode):
            raise EvidenceError('bundle source must be a regular file: ' + name)
    if MANIFEST in files:
        raise EvidenceError('bundle manifest name is reserved')
    manifest = dict(metadata, schema_version=1,
                    files={name: sha(path) for name, path in sorted(files.items())})
    manifest.setdefault('assurance_level', 'STRUCTURALLY_VALIDATED')
    manifest.setdefault('release_status', manifest.get('status', 'unknown'))
    manifest['artifact_type'] = 'factory_bundle_manifest'
    manifest['trust_profile'] = 'same_user_local' if sign_manifest else 'unsigned_checksums'
    if sign_manifest:
        manifest = sign_receipt(manifest)
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=destination.parent, prefix='.bundle-', suffix='.tmp')
    os.close(descriptor)
    try:
        with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED) as archive:
            for name, path in sorted(files.items()):
                info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0))
                info.compress_type=zipfile.ZIP_DEFLATED
                info.external_attr=(stat.S_IFREG | 0o644) << 16
                with Path(path).open('rb') as source,archive.open(info,'w',force_zip64=True) as target:
                    for chunk in iter(lambda:source.read(1024*1024),b''):
                        target.write(chunk)
            info=zipfile.ZipInfo(MANIFEST,date_time=(1980,1,1,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=(stat.S_IFREG | 0o644) << 16
            archive.writestr(info, json.dumps(manifest, sort_keys=True, indent=2, allow_nan=False) + '\n')
        verify_bundle(temporary, require_signature=sign_manifest)
        os.replace(temporary, destination)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return manifest


def verify_bundle(path, public_key_path=None, *, require_signature=False):
    """Check bytes, and authenticate metadata only when a trusted key is supplied.

    Returned metadata is the manifest itself. ``manifest_signature_verified``
    distinguishes authenticated provenance from unsigned byte consistency.
    """
    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            if len(infos)>MAX_MEMBERS or sum(info.file_size for info in infos)>MAX_UNCOMPRESSED_BYTES:
                raise EvidenceError('bundle exceeds member count or uncompressed byte limit')
            names = [member_name(info.filename) for info in infos]
            if len(names) != len(set(names)) or MANIFEST not in names:
                raise EvidenceError('duplicate members or missing bundle manifest')
            for info in infos:
                if info.orig_filename != info.filename:
                    raise EvidenceError('unsafe truncated bundle member name')
                mode = (info.external_attr >> 16) & 0o170000
                if info.is_dir() or mode not in (0, stat.S_IFREG):
                    raise EvidenceError('bundle must contain regular files only')
            if archive.getinfo(MANIFEST).file_size > 16 * 1024 * 1024:
                raise EvidenceError('bundle manifest exceeds 16 MiB limit')
            manifest = json.loads(archive.read(MANIFEST), object_pairs_hook=unique_object,
                                  parse_constant=reject_constant, parse_float=finite_float)
            if (not isinstance(manifest, dict) or type(manifest.get('schema_version')) is not int or
                    manifest['schema_version'] != 1 or not isinstance(manifest.get('files'), dict)):
                raise EvidenceError('invalid bundle manifest')
            if set(manifest['files']) != set(names) - {MANIFEST}:
                raise EvidenceError('bundle membership differs from manifest')
            for name, expected in manifest['files'].items():
                if not isinstance(expected, str) or not re.fullmatch(r'[0-9a-f]{64}', expected):
                    raise EvidenceError('invalid bundle digest: ' + name)
                h = hashlib.sha256()
                with archive.open(name) as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                        h.update(chunk)
                if h.hexdigest() != expected:
                    raise EvidenceError('bundle hash mismatch: ' + name)
            signature_verified = False
            if public_key_path is not None or require_signature:
                if manifest.get('artifact_type') != 'factory_bundle_manifest':
                    raise EvidenceError('bundle manifest signature domain is invalid')
                verify_receipt_signature(manifest, public_key_path)
                signature_verified = True
            result = dict(manifest)
            result['manifest_signature_verified'] = signature_verified
            result['verification_scope'] = ('signed manifest and byte integrity' if signature_verified else
                                             'byte integrity only; release and assurance metadata are untrusted')
            return result
    except EvidenceError:
        raise
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, NotImplementedError, zipfile.BadZipFile) as ex:
        raise EvidenceError(f'invalid bundle: {ex}') from ex
