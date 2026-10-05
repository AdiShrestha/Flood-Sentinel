"""Ed25519 receipts for observed local execution.

A local worker has the supervisor's OS identity and can read its signing key.
These signatures detect accidental edits and support verification against an
externally pinned public key; they do not establish an isolation boundary or
sealed evaluation. Stronger provenance requires an external execution service.
"""
import base64
import hashlib
import locale
import os
import platform
import re
import stat
import sys
import tempfile
import time
import uuid
from pathlib import Path

from .io import canonical, digest, EvidenceError

_KEY_ENV = 'FACTORY_SUPERVISOR_KEY'
SCHEME_ED25519 = 'ed25519'
# Kept as a compatibility name; symmetric receipts are never accepted.
SCHEME_HMAC_SHA256 = 'hmac-sha256'
_SIGNATURE_FIELDS = frozenset({'supervisor_signature', 'signature_scheme', 'public_key_id'})


def _key_path():
    configured = os.environ.get(_KEY_ENV)
    return Path(configured) if configured else Path.home() / '.factory' / 'supervisor.key'


def _key_dir():
    return _key_path().parent


def _pub_key_path():
    return _key_path().with_suffix('.pub')


def _try_ed25519():
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        return True
    except ImportError:
        return False


def _require_ed25519():
    if not _try_ed25519():
        raise EvidenceError('Ed25519 signing requires the cryptography package; no symmetric fallback is permitted')


def _regular(path):
    if path.is_symlink() or not stat.S_ISREG(path.stat().st_mode):
        raise EvidenceError('supervisor key must be a regular, non-symlink file')


def _parse_public_key(text):
    lines = text.strip().splitlines()
    if len(lines) != 2 or lines[0].strip() != '# ed25519':
        raise EvidenceError('supervisor public key must use Ed25519; legacy HMAC keys require explicit rotation')
    try:
        public = base64.b64decode(lines[1].strip(), validate=True)
    except (ValueError, TypeError) as ex:
        raise EvidenceError('malformed supervisor public key') from ex
    if len(public) != 32:
        raise EvidenceError('Ed25519 public key must contain 32 bytes')
    return public


def _write_key(path, data, mode):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix='.supervisor-', suffix='.tmp')
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def init_supervisor_keys(force=False):
    """Create a private Ed25519 key without ever publishing its secret."""
    _require_ed25519()
    priv, pub = _key_path(), _pub_key_path()
    if not force and (priv.exists() or pub.exists()):
        if not priv.exists() or not pub.exists():
            raise EvidenceError('incomplete supervisor keypair; restore it or explicitly rotate keys')
        _load_keys()
        return priv, pub, SCHEME_ED25519
    if priv.is_symlink() or pub.is_symlink():
        raise EvidenceError('supervisor key paths cannot be symlinks')
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization
    key = Ed25519PrivateKey.generate()
    private = key.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw,
                                serialization.NoEncryption())
    public = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    _write_key(priv, private, 0o600)
    _write_key(pub, ('# ed25519\n' + base64.b64encode(public).decode() + '\n').encode(), 0o644)
    return priv, pub, SCHEME_ED25519


def supervisor_public_key():
    """Read public material only; verification must never generate private keys."""
    path = _pub_key_path()
    try:
        _regular(path)
        text = path.read_text(encoding='ascii')
        public = _parse_public_key(text)
    except (OSError, UnicodeError) as ex:
        raise EvidenceError('cannot load supervisor public key: ' + str(ex)) from ex
    return {'public_key': text, 'public_key_id': hashlib.sha256(public).hexdigest()[:16],
            'signature_scheme': SCHEME_ED25519, 'trust_profile': 'same_user_local'}


def _load_keys():
    _require_ed25519()
    try:
        priv = _key_path()
        _regular(priv)
        if priv.stat().st_mode & 0o077:
            raise EvidenceError('supervisor private key permissions must be 0600')
        private = priv.read_bytes()
        public = _parse_public_key(supervisor_public_key()['public_key'])
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives import serialization
        expected = Ed25519PrivateKey.from_private_bytes(private).public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        if expected != public:
            raise EvidenceError('supervisor private/public keypair does not match')
        return private, public, SCHEME_ED25519
    except (OSError, ValueError) as ex:
        raise EvidenceError('cannot load supervisor signing key: ' + str(ex)) from ex


def sign_receipt(receipt_dict):
    """Sign canonical payload bytes. Key creation is an explicit initialization step."""
    if not isinstance(receipt_dict, dict):
        raise EvidenceError('receipt must be a JSON object')
    private, public, scheme = _load_keys()
    payload = {key: value for key, value in receipt_dict.items() if key not in _SIGNATURE_FIELDS}
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    signature = Ed25519PrivateKey.from_private_bytes(private).sign(canonical(payload))
    return dict(payload, supervisor_signature=base64.b64encode(signature).decode(),
                signature_scheme=scheme, public_key_id=hashlib.sha256(public).hexdigest()[:16])


def verify_receipt_signature(receipt_dict, public_key_path=None, *, public_key=None):
    """Verify against an explicitly supplied key or configured public file only."""
    _require_ed25519()
    if not isinstance(receipt_dict, dict):
        raise EvidenceError('receipt must be a JSON object')
    if receipt_dict.get('signature_scheme') != SCHEME_ED25519:
        raise EvidenceError('receipt is missing an Ed25519 supervisor signature')
    try:
        if public_key is not None and public_key_path is not None:
            raise EvidenceError('choose one supervisor public key source')
        if public_key is None:
            path = Path(public_key_path) if public_key_path is not None else _pub_key_path()
            _regular(path)
            public_key = path.read_text(encoding='ascii')
        public = _parse_public_key(public_key)
        if receipt_dict.get('public_key_id') != hashlib.sha256(public).hexdigest()[:16]:
            raise EvidenceError('receipt signed by unknown supervisor key')
        signature = base64.b64decode(receipt_dict.get('supervisor_signature', ''), validate=True)
        payload = {key: value for key, value in receipt_dict.items() if key not in _SIGNATURE_FIELDS}
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        Ed25519PublicKey.from_public_bytes(public).verify(signature, canonical(payload))
    except EvidenceError:
        raise
    except Exception as ex:
        raise EvidenceError('receipt signature verification failed: ' + str(ex)) from ex
    return True


def execution_binding(record):
    """Bind the entire execution wrapper, including failure metadata."""
    return digest({key: value for key, value in record.items()
                   if key != 'supervisor_receipt'})


def validate_run_nonce(value):
    """One canonical UUID4 identity for each reserved local execution."""
    try:parsed=uuid.UUID(value) if isinstance(value,str) else None
    except (ValueError,AttributeError):parsed=None
    if parsed is None or parsed.version!=4 or str(parsed)!=value:
        raise EvidenceError('execution nonce must be a canonical UUID4')
    return value


def validate_execution_ledger(ledger, *, project_id, epoch, freeze_sha256, run_prefix, experiment_ids):
    """Validate signed reservation identities independently of their signature."""
    if (not isinstance(ledger,dict) or ledger.get('artifact_type')!='factory_execution_ledger' or
            type(ledger.get('epoch')) is not int or ledger['epoch']!=epoch or
            ledger.get('project_id')!=project_id or ledger.get('freeze_sha256')!=freeze_sha256 or
            not isinstance(ledger.get('attempts'),dict)):
        raise EvidenceError('execution ledger identity differs from frozen epoch')
    if not set(ledger['attempts'])<=set(experiment_ids):
        raise EvidenceError('execution ledger reserves an unknown experiment')
    nonces=set()
    for eid,entry in ledger['attempts'].items():
        if not isinstance(entry,dict) or set(entry)!={'run_nonce','attempt_path','execution_sha256'}:
            raise EvidenceError('invalid execution reservation shape')
        nonce=validate_run_nonce(entry['run_nonce'])
        if nonce in nonces:raise EvidenceError('execution nonce reused across reservations')
        nonces.add(nonce)
        if entry['attempt_path']!=run_prefix+'/'+eid+'/attempt0001':
            raise EvidenceError('execution reservation path differs from experiment identity')
        checksum=entry['execution_sha256']
        if checksum is not None and (not isinstance(checksum,str) or not re.fullmatch('[0-9a-f]{64}',checksum)):
            raise EvidenceError('invalid reserved execution digest')
    return nonces


def verify_execution_record(record, *, project_id, epoch, experiment, freeze, engine_hash,
                            public_key_path=None):
    """Authenticate the nested receipt and its complete execution/plan bindings."""
    if not isinstance(record, dict):
        raise EvidenceError('execution record must be an object')
    if 'receipt_error' in record:
        raise EvidenceError('execution record contains receipt_error; no evidence admitted')
    if (type(record.get('epoch')) is not int or type(record.get('seed')) is not int
            or type(record.get('exit_code')) is not int):
        raise EvidenceError('execution epoch, seed and exit code must be JSON integers')
    if record.get('experiment_id')!=experiment['id'] or record['seed']!=experiment['seed']:
        raise EvidenceError('execution identity differs from frozen experiment')
    validate_run_nonce(record.get('run_nonce'))
    signed = record.get('supervisor_receipt')
    key = freeze.get('supervisor_public_key')
    if isinstance(key, dict):
        key = key.get('public_key')
    verify_receipt_signature(signed, public_key_path, public_key=key if public_key_path is None else None)
    expected = {
        'execution_binding': execution_binding(record),
        'project_id': project_id, 'epoch': epoch, 'experiment_id': experiment['id'],
        'seed': experiment['seed'], 'snapshot_merkle_root': freeze.get('snapshot_merkle_root'),
        'input_root': digest(freeze['files']), 'inputs_after_root': digest(record.get('inputs_after')),
        'output_root': digest(record.get('outputs')), 'engine_sha256': engine_hash,
        'launch_spec': digest(record.get('argv_template', record.get('argv'))),
        'interpreter_hash': record.get('interpreter_hash'),
        'dependency_lock_hash': record.get('dependency_lock_hash'),
        'exit_status': record.get('exit_code'), 'started_at': record.get('started_at'),
        'finished_at': record.get('finished_at'), 'run_nonce': record.get('run_nonce'),
        'supervisor_version': record.get('factory_version'),
        'runtime_id': record.get('runtime_id', 'python-cpu-v1'),
        'trust_profile': 'same_user_local',
    }
    if record.get('epoch') != epoch or record.get('engine_sha256') != engine_hash:
        raise EvidenceError('execution epoch/engine binding mismatch')
    if record.get('inputs_before') != freeze['files'] or record.get('inputs_after') != freeze['files']:
        raise EvidenceError('execution inputs changed or differ from frozen inputs')
    if freeze.get('supervisor_public_key_id') and signed.get('public_key_id') != freeze['supervisor_public_key_id']:
        raise EvidenceError('execution receipt differs from frozen supervisor key identity')
    for field, value in expected.items():
        if type(signed.get(field)) is not type(value) or signed.get(field) != value:
            raise EvidenceError('supervisor receipt binding mismatch: ' + field)
    return signed


def build_receipt(*, run_nonce, project_id, epoch, experiment_id,
                  snapshot_merkle_root, input_root, runtime_id,
                  interpreter_hash, dependency_lock_hash, launch_spec,
                  seed, output_root, exit_status, cpu_time, memory_peak,
                  started_at, finished_at, supervisor_version, policy_version,
                  execution_binding=None, engine_sha256=None, inputs_after_root=None,
                  trust_profile='same_user_local'):
    receipt = {
        'receipt_version': 1, 'run_nonce': run_nonce, 'project_id': project_id,
        'epoch': epoch, 'experiment_id': experiment_id, 'snapshot_merkle_root': snapshot_merkle_root,
        'input_root': input_root, 'runtime_id': runtime_id, 'interpreter_hash': interpreter_hash,
        'dependency_lock_hash': dependency_lock_hash, 'launch_spec': launch_spec, 'seed': seed,
        'output_root': output_root, 'exit_status': exit_status,
        'resource_observations': {'cpu_time_seconds': cpu_time, 'memory_peak_bytes': memory_peak},
        'started_at': started_at, 'finished_at': finished_at,
        'supervisor_version': supervisor_version, 'policy_version': policy_version,
        'execution_binding': execution_binding, 'engine_sha256': engine_sha256,
        'inputs_after_root': inputs_after_root, 'trust_profile': trust_profile,
    }
    return sign_receipt(receipt)


def runtime_attestation():
    """Observe the local runtime; filesystem paths and hostnames are not needed."""
    try:
        loc = locale.getlocale()
    except Exception:
        loc = ('unknown', 'unknown')
    return {
        'interpreter_hash': _interpreter_hash(), 'python_version': sys.version,
        'platform_system': platform.system(), 'platform_release': platform.release(),
        'platform_machine': platform.machine(), 'locale': str(loc),
        'timezone': str(time.timezone), 'encoding': sys.getdefaultencoding(),
        'byte_order': sys.byteorder, 'trust_profile': 'same_user_local',
        'dependency_isolation': 'installed_runtime_not_isolated',
    }


def _interpreter_hash():
    h = hashlib.sha256()
    try:
        with open(sys.executable, 'rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                h.update(chunk)
    except OSError as ex:
        raise EvidenceError('cannot hash runtime interpreter: ' + str(ex)) from ex
    return h.hexdigest()
