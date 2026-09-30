"""Portable review archives: verify membership and bytes without extracting files.

Checksums detect corruption; they are not signatures or proof of honest producers.
"""
import hashlib
import json
import os
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from .io import EvidenceError, sha, unique_object, reject_constant, finite_float

MANIFEST = 'BUNDLE_MANIFEST.json'

def member_name(name):
    p = PurePosixPath(name)
    if (not name or p.is_absolute() or '..' in p.parts or '\\' in name or
            ':' in name or str(p) != name or name == '.'):
        raise EvidenceError('unsafe bundle member: '+name)
    return name

def create_bundle(destination, files, metadata):
    """files maps archive names to inspected local paths; no extraction occurs."""
    destination = Path(destination)
    for name in files:
        member_name(name)
    if MANIFEST in files:
        raise EvidenceError('bundle manifest name is reserved')
    manifest = dict(metadata, schema_version=1,
                    files={name: sha(path) for name,path in sorted(files.items())})
    # v3.3.0: Include assurance level and release status if available
    if 'assurance_level' not in manifest and 'factory_version' in manifest:
        manifest['assurance_level'] = manifest.get('assurance_level', 'STRUCTURALLY_VALIDATED')
    if 'release_status' not in manifest:
        manifest['release_status'] = manifest.get('status', 'unknown')
    destination.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp = tempfile.mkstemp(dir=destination.parent,prefix='.bundle-',suffix='.tmp')
    os.close(fd)
    try:
        with zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED) as archive:
            for name,path in sorted(files.items()):
                archive.write(path,name)
            archive.writestr(MANIFEST,json.dumps(manifest,sort_keys=True,indent=2,allow_nan=False)+'\n')
        verify_bundle(tmp)
        os.replace(tmp,destination)
    finally:
        Path(tmp).unlink(missing_ok=True)
    return manifest

def verify_bundle(path):
    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            names = [member_name(i.filename) for i in infos]
            if len(names)!=len(set(names)) or MANIFEST not in names:
                raise EvidenceError('duplicate members or missing bundle manifest')
            if any(i.is_dir() or (i.external_attr >> 16) & 0o170000 == 0o120000 for i in infos):
                raise EvidenceError('bundle must contain regular files, not symlinks or directory entries')
            if archive.getinfo(MANIFEST).file_size > 16*1024*1024:
                raise EvidenceError('bundle manifest exceeds 16 MiB limit')
            manifest = json.loads(archive.read(MANIFEST),object_pairs_hook=unique_object,
                                  parse_constant=reject_constant,parse_float=finite_float)
            if not isinstance(manifest,dict) or manifest.get('schema_version')!=1 or not isinstance(manifest.get('files'),dict):
                raise EvidenceError('invalid bundle manifest')
            if set(manifest['files']) != set(names)-{MANIFEST}:
                raise EvidenceError('bundle membership differs from manifest')
            for name,expected in manifest['files'].items():
                h=hashlib.sha256()
                with archive.open(name) as f:
                    for chunk in iter(lambda:f.read(1024*1024),b''):
                        h.update(chunk)
                if h.hexdigest()!=expected:
                    raise EvidenceError('bundle hash mismatch: '+name)
            return manifest
    except (OSError,ValueError,KeyError,RuntimeError,zipfile.BadZipFile) as ex:
        raise EvidenceError(f'invalid bundle: {ex}') from ex
