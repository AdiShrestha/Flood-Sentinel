"""Strict serialization, bounded paths, content hashing and atomic writes."""
import csv
import hashlib
import json
import os
import math
import tempfile
from pathlib import Path
from .metrics import EvidenceError

def reject_constant(v):
    raise EvidenceError('non-standard JSON constant: '+v)

def unique_object(pairs):
    d = {}
    for k,v in pairs:
        if k in d:
            raise EvidenceError('duplicate JSON key: '+k)
        d[k] = v
    return d

def read_json(p):
    try:
        return json.loads(Path(p).read_text(encoding='utf-8'),parse_constant=reject_constant,
                          parse_float=finite_float,object_pairs_hook=unique_object)
    except (OSError, ValueError) as e:
        raise EvidenceError(f'{p}: {e}') from e

def finite_float(value):
    result = float(value)
    if not math.isfinite(result):
        raise EvidenceError('non-finite JSON number: '+value)
    return result

def canonical(obj):
    return json.dumps(obj,sort_keys=True,separators=(',',':'),allow_nan=False).encode()

def digest(obj):
    return hashlib.sha256(canonical(obj)).hexdigest()

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):
            h.update(b)
    return h.hexdigest()

def _normalize_path(name):
    """Normalize a relative path, rejecting dot-segment tricks."""
    import posixpath
    # Normalize to remove . and resolve .. (which we also reject below)
    normalized = posixpath.normpath(name)
    # posixpath.normpath converts 'a/./b' to 'a/b' — if the input differs
    # from the normalized form, someone is using dot-segment tricks.
    if normalized != name and name != normalized + '/' and not name.endswith('/'):
        raise EvidenceError(f'path contains dot-segment tricks: {name} (normalized: {normalized})')
    return normalized

# File extensions that are dangerous if imported/executed without explicit hash
_DANGEROUS_EXTENSIONS = frozenset({
    '.pyc', '.pyo', '.so', '.dylib', '.dll', '.pyd',
})

def inside(root, name):
    # Preserve the caller's lexical workspace path for stable relative artifact
    # IDs while performing containment against its canonical real path. This
    # matters on macOS where /var and /private/var are aliases.
    root_lex = Path(root)
    root_real = root_lex.resolve()
    name = str(name)
    # Reject null bytes — they truncate C-level path operations
    if '\x00' in name:
        raise EvidenceError(f'null byte in path: {name!r}')
    # Normalize backslashes to forward slashes and reject if result differs
    # (backslash traversal like project\\..\\..\\etc\\passwd)
    if '\\' in name:
        raise EvidenceError(f'backslash in path: {name}')
    # Normalize the path to catch dot-segment tricks like project/./audit_report.json
    name = _normalize_path(name)
    rel = Path(name)
    if rel.is_absolute() or '..' in rel.parts or not rel.parts:
        raise EvidenceError(f'unsafe relative path: {name}')
    p = root_lex / rel
    # Reject symlinks in evidence paths, including newly introduced links.
    cur = root_lex
    for part in rel.parts:
        cur = cur / part
        if cur.is_symlink():
            raise EvidenceError(f'symlink evidence path: {name}')
    if not p.resolve().is_relative_to(root_real):
        raise EvidenceError(f'path escapes root: {name}')
    return p

def write_json(p, obj):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    data=json.dumps(obj,indent=2,sort_keys=True,allow_nan=False)+'\n'
    # Unique same-directory staging tolerates interrupted writes and concurrent
    # callers without following a predictable temporary-file symlink.
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=p.parent,
                                         prefix='.'+p.name+'.',suffix='.tmp',delete=False) as f:
            tmp = Path(f.name)
            f.write(data);f.flush();os.fsync(f.fileno())
        os.replace(tmp,p)
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)

def read_csv(p, required):
    with Path(p).open(newline='') as f:
        reader=csv.DictReader(f)
        names=reader.fieldnames or []
        if len(names)!=len(set(names)) or not set(required)<=set(names):
            raise EvidenceError(f'{p}: missing/duplicate CSV columns; required {required}')
        rows=list(reader)
    if not rows or any(None in r or any(v is None for v in r.values()) for r in rows):
        raise EvidenceError(f'{p}: empty or malformed CSV')
    return rows

def _reject_special_file(f):
    """Reject device files, FIFOs, sockets — anything that isn't a regular file or directory."""
    import stat
    try:
        mode = f.lstat().st_mode
    except OSError:
        raise EvidenceError(f'cannot stat: {f}')
    if stat.S_ISFIFO(mode):
        raise EvidenceError(f'FIFO in frozen inputs: {f}')
    if stat.S_ISSOCK(mode):
        raise EvidenceError(f'socket in frozen inputs: {f}')
    if stat.S_ISBLK(mode) or stat.S_ISCHR(mode):
        raise EvidenceError(f'device file in frozen inputs: {f}')

def inventory(root, paths, *, reject_dangerous_ext=True):
    # Canonicalize once so macOS /var -> /private/var aliases cannot make
    # otherwise-valid files appear outside the workspace during hashing.
    root = Path(os.path.realpath(root))
    out={}
    for name in paths:
        p=inside(root,name)
        if not p.exists():
            raise EvidenceError('missing frozen input: '+name)
        files=sorted(p.rglob('*')) if p.is_dir() else [p]
        for f in files:
            if f.is_symlink():
                raise EvidenceError('symlink in frozen inputs')
            _reject_special_file(f)
            if f.is_file() and '__pycache__' not in f.parts:
                ext = f.suffix.lower()
                if ext in _DANGEROUS_EXTENSIONS:
                    if reject_dangerous_ext:
                        raise EvidenceError(
                            f'dangerous binary in frozen inputs: {f.name} '
                            f'({ext} files can be imported without source and must be '
                            f'explicitly whitelisted)'
                        )
                    continue
                out[str(f.relative_to(root))]=sha(f)
    if not out:
        raise EvidenceError('empty input inventory')
    return out

def merkle_root(file_hashes):
    """Compute a Merkle root over a dict of {path: sha256_hex}.

    Files are sorted by path to produce a deterministic root.
    Returns the hex digest of the Merkle root.
    """
    if not file_hashes:
        raise EvidenceError('cannot compute merkle root of empty inventory')
    h = hashlib.sha256()
    for path in sorted(file_hashes.keys()):
        h.update(path.encode('utf-8'))
        h.update(bytes.fromhex(file_hashes[path]))
    return h.hexdigest()
