"""Local receipt integrity, not an independently isolated evaluation service.

Ed25519 requires cryptography; HMAC is symmetric authentication, not Ed25519.
Workers running as the same OS user can read that user's private key. Moving
the key outside the project does not establish a supervisor trust boundary.
HMAC public metadata contains only a fingerprint; verification requires the
private key. Historical HMAC metadata disclosed its secret and is rejected.
"""
import base64
import hashlib
import hmac
import json
import locale
import os
import platform
import sys
import time
import math
from pathlib import Path

from .io import canonical, sha, EvidenceError

# Key storage location — outside any project workspace
_DEFAULT_KEY_DIR = Path.home() / '.factory'
_KEY_ENV = 'FACTORY_SUPERVISOR_KEY'

# Signature schemes
SCHEME_ED25519 = 'ed25519'
SCHEME_HMAC_SHA256 = 'hmac-sha256'


def _key_dir():
    """Resolve the supervisor key directory."""
    env = os.environ.get(_KEY_ENV)
    if env:
        return Path(env).parent
    return _DEFAULT_KEY_DIR


def _key_path():
    """Resolve the path to the supervisor private key."""
    env = os.environ.get(_KEY_ENV)
    if env:
        return Path(env)
    return _DEFAULT_KEY_DIR / 'supervisor.key'


def _pub_key_path():
    """Resolve the path to the supervisor public key."""
    return _key_path().with_suffix('.pub')


def _try_ed25519():
    """Check if real Ed25519 is available."""
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PrivateKey,
        )
        return True
    except ImportError:
        return False


def init_supervisor_keys(force=False):
    """Generate supervisor keypair if it doesn't exist.

    Returns (private_key_path, public_key_path, scheme).
    """
    priv = _key_path()
    pub = _pub_key_path()

    if priv.exists() and pub.exists() and not force:
        scheme = pub.read_text().splitlines()[0].strip() if pub.exists() else SCHEME_HMAC_SHA256
        if scheme.startswith('#'):
            scheme = scheme.lstrip('#').strip()
        return priv, pub, scheme

    priv.parent.mkdir(parents=True, exist_ok=True)

    if _try_ed25519():
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives import serialization

        private_key = Ed25519PrivateKey.generate()
        priv_bytes = private_key.private_bytes(
            serialization.Encoding.Raw,
            serialization.PrivateFormat.Raw,
            serialization.NoEncryption()
        )
        pub_bytes = private_key.public_key().public_bytes(
            serialization.Encoding.Raw,
            serialization.PublicFormat.Raw
        )
        priv.write_bytes(priv_bytes)
        os.chmod(priv, 0o600)
        pub.write_text(f'# {SCHEME_ED25519}\n{base64.b64encode(pub_bytes).decode()}\n')
        return priv, pub, SCHEME_ED25519
    else:
        # HMAC-SHA256 fallback: generate a 32-byte secret
        secret = os.urandom(32)
        priv.write_bytes(secret)
        os.chmod(priv, 0o600)
        pub.write_text(f'# {SCHEME_HMAC_SHA256}\nfingerprint-sha256:{hashlib.sha256(secret).hexdigest()}\n')
        return priv, pub, SCHEME_HMAC_SHA256


def _load_keys():
    """Load the supervisor keys. Returns (private_bytes, public_info, scheme)."""
    priv = _key_path()
    pub = _pub_key_path()

    if not priv.exists() or not pub.exists():
        init_supervisor_keys()

    priv_bytes = priv.read_bytes()
    pub_lines = pub.read_text().splitlines()
    if len(pub_lines) != 2 or pub_lines[0] not in ('# '+SCHEME_ED25519, '# '+SCHEME_HMAC_SHA256) or len(priv_bytes) != 32:
        raise EvidenceError('invalid supervisor key metadata')
    scheme = pub_lines[0][2:]
    try:
        if scheme == SCHEME_ED25519:
            pub_data = base64.b64decode(pub_lines[1], validate=True)
            if len(pub_data) != 32: raise ValueError('wrong public key length')
        else:
            prefix = 'fingerprint-sha256:'
            if not pub_lines[1].startswith(prefix):
                raise EvidenceError('legacy HMAC public metadata exposed its secret; retain failed evidence and rotate this key explicitly')
            pub_data = bytes.fromhex(pub_lines[1][len(prefix):])
            if pub_data != hashlib.sha256(priv_bytes).digest(): raise ValueError('fingerprint mismatch')
    except EvidenceError:
        raise
    except ValueError as ex:
        raise EvidenceError('invalid supervisor public metadata') from ex
    return priv_bytes, pub_data, scheme


def sign_receipt(receipt_dict):
    """Sign a receipt dictionary. Returns the receipt with 'supervisor_signature' added.

    The receipt is canonicalized (sorted keys, compact JSON) before signing.
    The signature covers the canonical bytes.
    """
    priv_bytes, pub_data, scheme = _load_keys()

    # Remove any prior signature before signing
    to_sign = {k: v for k, v in receipt_dict.items()
               if k not in ('supervisor_signature', 'signature_scheme', 'public_key_id')}
    payload = canonical(to_sign)

    if scheme == SCHEME_ED25519:
        if not _try_ed25519(): raise EvidenceError('Ed25519 dependency unavailable; cannot downgrade the stored scheme')
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        private_key = Ed25519PrivateKey.from_private_bytes(priv_bytes)
        sig = private_key.sign(payload)
        sig_b64 = base64.b64encode(sig).decode()
    elif scheme == SCHEME_HMAC_SHA256:
        sig = hmac.new(priv_bytes, payload, hashlib.sha256).digest()
        sig_b64 = base64.b64encode(sig).decode()
        scheme = SCHEME_HMAC_SHA256

    pub_id = hashlib.sha256(pub_data).hexdigest()[:16]

    signed = dict(receipt_dict)
    signed['supervisor_signature'] = sig_b64
    signed['signature_scheme'] = scheme
    signed['public_key_id'] = pub_id

    return signed


def verify_receipt_signature(receipt_dict):
    """Verify the supervisor signature on a receipt.

    Returns True if valid, raises EvidenceError if invalid or missing.
    """
    sig_b64 = receipt_dict.get('supervisor_signature')
    scheme = receipt_dict.get('signature_scheme')
    key_id = receipt_dict.get('public_key_id')

    if not sig_b64 or not scheme:
        raise EvidenceError('receipt is missing supervisor signature')

    to_verify = {k: v for k, v in receipt_dict.items()
                 if k not in ('supervisor_signature', 'signature_scheme', 'public_key_id')}
    payload = canonical(to_verify)

    priv_data, pub_data, stored_scheme = _load_keys()
    if scheme != stored_scheme: raise EvidenceError('receipt signature scheme differs from the stored key scheme')

    # Verify key identity
    expected_id = hashlib.sha256(pub_data).hexdigest()[:16]
    if key_id != expected_id:
        raise EvidenceError('receipt signed by unknown supervisor key')

    try:
        sig = base64.b64decode(sig_b64, validate=True)
    except Exception:
        raise EvidenceError('receipt signature is malformed or truncated')

    if scheme == SCHEME_ED25519 and _try_ed25519():
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        public_key = Ed25519PublicKey.from_public_bytes(pub_data)
        try:
            public_key.verify(sig, payload)
        except Exception:
            raise EvidenceError('receipt signature verification failed')
    elif scheme == SCHEME_HMAC_SHA256:
        expected = hmac.new(priv_data, payload, hashlib.sha256).digest()
        if not hmac.compare_digest(sig, expected):
            raise EvidenceError('receipt signature verification failed')
    else:
        raise EvidenceError(f'unknown signature scheme: {scheme}')

    return True


def build_receipt(*, run_nonce, project_id, epoch, experiment_id,
                  snapshot_merkle_root, input_root, runtime_id,
                  interpreter_hash, dependency_lock_hash, launch_spec,
                  seed, output_root, exit_status, cpu_time, memory_peak,
                  started_at, finished_at, supervisor_version, policy_version,
                  wall_time=None):
    """Build a complete supervisor receipt binding all 16 required fields."""
    for value in (cpu_time, memory_peak, wall_time):
        if value is not None and (isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value < 0):
            raise EvidenceError('resource observations must be measured finite nonnegative numbers or unavailable (None)')
    receipt = {
        'receipt_version': 1,
        'run_nonce': run_nonce,
        'project_id': project_id,
        'epoch': epoch,
        'experiment_id': experiment_id,
        'snapshot_merkle_root': snapshot_merkle_root,
        'input_root': input_root,
        'runtime_id': runtime_id,
        'interpreter_hash': interpreter_hash,
        'dependency_lock_hash': dependency_lock_hash,
        'launch_spec': launch_spec,
        'seed': seed,
        'output_root': output_root,
        'exit_status': exit_status,
        'resource_observations': {
            'cpu_time_seconds': cpu_time,
            'memory_peak_bytes': memory_peak,
            'wall_time_seconds': wall_time,
        },
        'started_at': started_at,
        'finished_at': finished_at,
        'supervisor_version': supervisor_version,
        'policy_version': policy_version,
    }
    return sign_receipt(receipt)


def runtime_attestation():
    """Capture current runtime environment for binding into receipts."""
    try:
        loc = locale.getlocale()
    except Exception:
        loc = ('unknown', 'unknown')

    return {
        'interpreter_binary': sys.executable,
        'interpreter_hash': _interpreter_hash(),
        'python_version': sys.version,
        'platform_system': platform.system(),
        'platform_release': platform.release(),
        'platform_machine': platform.machine(),
        'platform_node': platform.node(),
        'locale': str(loc),
        'timezone': str(time.timezone),
        'encoding': sys.getdefaultencoding(),
        'byte_order': sys.byteorder,
    }


def _interpreter_hash():
    """SHA-256 of the running interpreter binary."""
    h = hashlib.sha256()
    try:
        with open(sys.executable, 'rb') as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b''):
                h.update(chunk)
    except OSError:
        return 'unavailable'
    return h.hexdigest()
