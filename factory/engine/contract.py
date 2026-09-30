"""Typed execution contract. The project declares what to run; the supervisor
constructs how to run it. No shell wrappers, no free-form interpreter flags,
no executable paths from the plan.

The plan stores a structured contract object. The supervisor resolves
``runtime_id`` to a preinstalled runtime and builds the argv itself.
"""
import hashlib
import os
import re
import sys
from pathlib import Path

from .metrics import EvidenceError
from .schema import (ValidationError, expect_dict, expect_enum, expect_float,
                     expect_int, expect_str)

# Known runtimes the supervisor can resolve. Each maps to a concrete binary
# and a set of hardening flags. Extending this requires a supervisor update,
# not a plan change.
KNOWN_RUNTIMES = {
    'python-cpu-v1': {
        'binary': sys.executable,
        'flags': ['-I', '-P', '-B', '-S'] if sys.version_info >= (3, 11) else ['-I', '-B', '-S'],
        'kind': 'python',
    },
}

# Patterns that indicate shell/interpreter injection attempts in entrypoints
_DANGEROUS_ENTRYPOINT_RE = re.compile(
    r'(?:^-|;|&&|\|\||`|\$\(|[<>]|\.\.[\\/])'
)

# Inline-code flags that must never appear
_INLINE_FLAGS = frozenset({'-c', '--command', '/c', '-e', '--eval', '-m'})

# Interpreter prefixes to detect wrapped execution
_INTERPRETER_PREFIXES = (
    'sh', 'bash', 'zsh', 'fish', 'dash', 'cmd', 'powershell', 'pwsh',
    'python', 'pypy', 'node', 'ruby', 'perl', 'env',
)


def validate_contract(contract, root, frozen_code_paths):
    """Validate a typed execution contract from the plan.

    Returns the validated contract dict. Raises EvidenceError on any problem.
    """
    expect_dict(contract, 'execution_contract')

    # runtime_id
    runtime_id = contract.get('runtime_id')
    expect_str(runtime_id, 'execution_contract.runtime_id')
    if runtime_id not in KNOWN_RUNTIMES:
        raise EvidenceError(
            f'unknown runtime_id: {runtime_id}; '
            f'available: {sorted(KNOWN_RUNTIMES)}'
        )

    # entrypoint must be a frozen code_path
    entrypoint = contract.get('entrypoint')
    expect_str(entrypoint, 'execution_contract.entrypoint')
    if _DANGEROUS_ENTRYPOINT_RE.search(entrypoint):
        raise EvidenceError(f'dangerous entrypoint: {entrypoint}')
    if not any(entrypoint == cp or entrypoint.startswith(cp.rstrip('/') + '/')
               for cp in frozen_code_paths):
        raise EvidenceError(
            f'entrypoint {entrypoint} must be inside a declared frozen code_path'
        )
    ep_path = root / entrypoint
    if not ep_path.is_file():
        raise EvidenceError(f'entrypoint not found: {entrypoint}')
    if ep_path.is_symlink():
        raise EvidenceError(f'entrypoint is a symlink: {entrypoint}')

    # arguments — only well-known placeholders
    args = contract.get('arguments', {})
    expect_dict(args, 'execution_contract.arguments')
    allowed_arg_values = {'supervisor_bound', 'plan_seed', 'plan_id'}
    for k, v in args.items():
        expect_str(v, f'execution_contract.arguments.{k}')

    # resource limits
    if 'cpu_seconds' in contract:
        expect_int(contract['cpu_seconds'], 'execution_contract.cpu_seconds', minimum=1)
    if 'memory_bytes' in contract:
        expect_int(contract['memory_bytes'], 'execution_contract.memory_bytes', minimum=1)
    if 'process_limit' in contract:
        expect_int(contract['process_limit'], 'execution_contract.process_limit', minimum=1)

    # network policy
    if 'network' in contract:
        expect_enum(contract['network'], {'disabled', 'allowed'}, 'execution_contract.network')

    return contract


def resolve_contract(contract, run_dir, seed, experiment_id):
    """Resolve a validated contract into a concrete argv and preexec function.

    The supervisor owns this logic. The project never provides an executable
    path, shell wrapper, or interpreter flags.

    Returns (argv, preexec_fn, env_updates).
    """
    runtime = KNOWN_RUNTIMES[contract['runtime_id']]
    binary = runtime['binary']
    flags = list(runtime['flags'])

    # Build argv: binary + flags + entrypoint + resolved arguments
    entrypoint = contract['entrypoint']
    argv = [binary] + flags + [entrypoint]

    # Resolve argument placeholders
    args = contract.get('arguments', {})
    for key, value in sorted(args.items()):
        if value == 'supervisor_bound':
            argv.append(str(Path(run_dir).resolve()))
        elif value == 'plan_seed':
            argv.append(str(seed))
        elif value == 'plan_id':
            argv.append(str(experiment_id))
        else:
            argv.append(value)

    # Resource limits via preexec_fn
    preexec = _build_preexec(contract)

    # Environment updates
    env_updates = {
        'PYTHONDONTWRITEBYTECODE': '1',
    }

    return argv, preexec, env_updates


def _build_preexec(contract):
    """Build a preexec_fn that sets resource limits on the child process."""
    import resource

    cpu = contract.get('cpu_seconds')
    mem = contract.get('memory_bytes')
    nproc = contract.get('process_limit')

    if not any([cpu, mem, nproc]):
        return None

    def _set_limits():
        if cpu:
            resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu))
        if mem:
            try:
                resource.setrlimit(resource.RLIMIT_AS, (mem, mem))
            except (ValueError, OSError):
                pass  # RLIMIT_AS not available on all platforms
        if nproc:
            try:
                resource.setrlimit(resource.RLIMIT_NPROC, (nproc, nproc))
            except (ValueError, OSError):
                pass  # RLIMIT_NPROC not available on all platforms

    return _set_limits


def command_to_contract(command, code_paths):
    """Convert a legacy command array to a typed contract (with deprecation).

    This enables backward compatibility while moving to the contract model.
    Returns (contract_dict, deprecation_warning).
    """
    if not command or not isinstance(command, list):
        raise EvidenceError('command must be a nonempty list')

    # Find the entrypoint: the first argument that matches a code_path
    entrypoint = None
    for arg in command:
        if isinstance(arg, str):
            for cp in code_paths:
                if arg == cp or arg.startswith(cp.rstrip('/') + '/'):
                    entrypoint = arg
                    break
        if entrypoint:
            break

    if not entrypoint:
        raise EvidenceError(
            'command must reference at least one declared frozen code_path'
        )

    # Detect inline code attempts in the legacy format too
    for i, token in enumerate(command):
        if not isinstance(token, str):
            raise EvidenceError('command elements must be strings')
        # Shell metacharacters
        if any(z in token for z in (';', '&&', '||', '`', '$(', '>', '<')):
            raise EvidenceError('command must be a safe argv list, not shell text')
        # Check for inline-code flags
        exe = Path(token).name.lower()
        if any(exe == p or exe.startswith(p) for p in _INTERPRETER_PREFIXES):
            rest = command[i + 1:]
            # Check for directly attached forms like -cexec(...)
            for arg in rest:
                low = arg.lower()
                if low in _INLINE_FLAGS:
                    raise EvidenceError(
                        'experiment command must execute frozen code_paths; '
                        'inline shell/interpreter code is not permitted'
                    )
                # Attached forms: -cexec(...), -c'code'
                for flag in _INLINE_FLAGS:
                    if low.startswith(flag) and len(low) > len(flag):
                        raise EvidenceError(
                            'experiment command must execute frozen code_paths; '
                            f'attached inline code flag {flag} is not permitted'
                        )

    # Build the contract
    contract = {
        'runtime_id': 'python-cpu-v1',
        'entrypoint': entrypoint,
        'arguments': {
            'run_dir': 'supervisor_bound',
            'seed': 'plan_seed',
            'experiment_id': 'plan_id',
        },
        'network': 'disabled',
    }

    warning = (
        'experiment uses legacy command array; migrate to execution_contract '
        'for typed validation and resource limits'
    )

    return contract, warning


def runtime_binary_hash():
    """SHA-256 of the current Python interpreter binary."""
    h = hashlib.sha256()
    try:
        with open(sys.executable, 'rb') as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b''):
                h.update(chunk)
    except OSError:
        return 'unavailable'
    return h.hexdigest()
