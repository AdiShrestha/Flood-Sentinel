"""Supervisor-owned Python launch contracts, with explicit local limitations.

Installed dependencies are usable, frozen scripts can import frozen siblings,
and arbitrary executables, interpreter flags and shell wrappers are rejected.
This process uses the caller's OS identity; it is not a security sandbox.
"""
import hashlib
import os
import re
import sys
from pathlib import Path

from .io import EvidenceError, inside
from .schema import expect_dict, expect_enum, expect_int, expect_str

KNOWN_RUNTIMES = {
    'python-cpu-v1': {'binary': sys.executable, 'flags': ['-s', '-B'], 'kind': 'python'},
}
_PLACEHOLDERS = {'supervisor_bound': '{run_dir}', 'plan_seed': '{seed}', 'plan_id': '{experiment_id}'}
_FIELDS = {'runtime_id', 'entrypoint', 'arguments', 'network', 'cpu_seconds',
           'memory_bytes', 'process_limit', 'wall_seconds'}


def _argument_templates(arguments):
    if isinstance(arguments, list):
        templates = arguments
    elif isinstance(arguments, dict):
        # Mapping arguments are named positional roles, with fixed semantic order.
        order = ('run_dir', 'seed', 'experiment_id')
        if set(arguments) - set(order):
            raise EvidenceError('contract argument mappings only support run_dir, seed, experiment_id')
        expected = {'run_dir': 'supervisor_bound', 'seed': 'plan_seed', 'experiment_id': 'plan_id'}
        if any(value != expected[key] for key, value in arguments.items()):
            raise EvidenceError('contract argument mappings require the matching supervisor placeholder')
        templates = [_PLACEHOLDERS[arguments[key]] for key in order if key in arguments]
    else:
        raise EvidenceError('execution_contract.arguments must be a list or positional-role mapping')
    for value in templates:
        expect_str(value, 'execution_contract.arguments[]')
        if '\x00' in value:
            raise EvidenceError('NUL in execution argument')
        unknown = re.findall(r'\{([^{}]+)\}', value)
        if set(unknown) - {'run_dir', 'seed', 'experiment_id'}:
            raise EvidenceError('unknown execution argument placeholder')
    return list(templates)


def validate_contract(contract, root, frozen_code_paths):
    expect_dict(contract, 'execution_contract')
    if set(contract) - _FIELDS:
        raise EvidenceError('unknown execution contract fields: ' + ', '.join(sorted(set(contract) - _FIELDS)))
    runtime = contract.get('runtime_id')
    expect_str(runtime, 'execution_contract.runtime_id')
    if runtime not in KNOWN_RUNTIMES:
        raise EvidenceError('unknown runtime_id: ' + runtime)
    entrypoint = contract.get('entrypoint')
    expect_str(entrypoint, 'execution_contract.entrypoint')
    if not entrypoint.startswith('source/') or not entrypoint.endswith('.py'):
        raise EvidenceError('entrypoint must be a Python script under frozen source/')
    path = inside(root, entrypoint)
    if not any(entrypoint == code or entrypoint.startswith(code.rstrip('/') + '/')
               for code in frozen_code_paths):
        raise EvidenceError('entrypoint must be inside a declared frozen code_path')
    if not path.is_file():
        raise EvidenceError('entrypoint not found: ' + entrypoint)
    _argument_templates(contract.get('arguments', []))
    for field in ('cpu_seconds', 'memory_bytes', 'process_limit', 'wall_seconds'):
        if field in contract:
            expect_int(contract[field], 'execution_contract.' + field, minimum=1)
    network = contract.get('network', 'unrestricted')
    expect_enum(network, {'unrestricted', 'allowed', 'disabled'}, 'execution_contract.network')
    if network == 'disabled':
        raise EvidenceError('network=disabled requires an external isolated runner; this local runtime cannot enforce it')
    _validate_resource_support(contract)
    return contract


def _validate_resource_support(contract):
    limits = {'cpu_seconds': 'RLIMIT_CPU', 'memory_bytes': 'RLIMIT_AS', 'process_limit': 'RLIMIT_NPROC'}
    if not any(field in contract for field in limits):
        return
    try:
        import resource
    except ImportError as ex:
        raise EvidenceError('requested resource limits are unsupported by this runtime') from ex
    for field, name in limits.items():
        if field not in contract:
            continue
        if not hasattr(resource, name):
            raise EvidenceError(field + ' is unsupported by this platform')
        if field == 'memory_bytes' and sys.platform == 'darwin':
            raise EvidenceError('memory_bytes enforcement is unsupported on macOS; use an external isolated runner')
        if field == 'process_limit' and (getattr(os, 'geteuid', lambda: -1)() == 0 or sys.platform != 'linux'):
            raise EvidenceError('process_limit enforcement requires an unprivileged Linux runner')


def contract_argv_template(contract):
    """Logical launch identity, unchanged after relocating a review bundle."""
    if contract.get('runtime_id') not in KNOWN_RUNTIMES:
        raise EvidenceError('unknown runtime_id')
    return ['runtime:' + contract['runtime_id']] + list(KNOWN_RUNTIMES[contract['runtime_id']]['flags']) + [
        contract['entrypoint']] + _argument_templates(contract.get('arguments', []))


def resolve_contract(contract, run_dir, seed, experiment_id):
    runtime = KNOWN_RUNTIMES[contract['runtime_id']]
    if contract.get('network') == 'disabled':
        raise EvidenceError('network=disabled cannot be enforced by the local runtime')
    _validate_resource_support(contract)
    argv = [runtime['binary']] + list(runtime['flags']) + [contract['entrypoint']]
    for template in _argument_templates(contract.get('arguments', [])):
        argv.append(template.replace('{run_dir}', str(Path(run_dir).resolve()))
                    .replace('{seed}', str(seed)).replace('{experiment_id}', str(experiment_id)))
    return argv, _build_preexec(contract), {'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONNOUSERSITE': '1'}


def _build_preexec(contract):
    _validate_resource_support(contract)
    fields = {'cpu_seconds': 'RLIMIT_CPU', 'memory_bytes': 'RLIMIT_AS', 'process_limit': 'RLIMIT_NPROC'}
    configured = {field: contract[field] for field in fields if field in contract}
    if not configured:
        return None
    import resource

    def set_limits():
        # An unsupported/failed limit aborts child launch rather than silently degrading.
        for field, value in configured.items():
            resource.setrlimit(getattr(resource, fields[field]), (value, value))
    return set_limits


def command_to_contract(command, code_paths):
    """Translate legacy Python-script argv exactly, preserving argument semantics."""
    if not isinstance(command, list) or len(command) < 2 or any(not isinstance(arg, str) or not arg or '\x00' in arg for arg in command):
        raise EvidenceError('command must be a nonempty Python-script argv list')
    interpreter, entrypoint = command[:2]
    # Bare interpreter aliases are labels; the supervisor always selects its own binary.
    aliases = {'python', 'python3', 'python' + str(sys.version_info.major) + '.' + str(sys.version_info.minor)}
    if interpreter not in aliases and interpreter != sys.executable:
        raise EvidenceError('legacy command must use the supervisor Python interpreter; executable paths and wrappers are forbidden')
    if entrypoint.startswith('-') or not entrypoint.startswith('source/') or not entrypoint.endswith('.py'):
        raise EvidenceError('legacy command must execute a frozen source Python script')
    if not any(entrypoint == code or entrypoint.startswith(code.rstrip('/') + '/') for code in code_paths):
        raise EvidenceError('legacy command entrypoint must be inside a declared frozen code_path')
    if any(token in entrypoint for token in (';', '&&', '||', '`', '$(', '>', '<', '\\')):
        raise EvidenceError('unsafe legacy entrypoint')
    contract = {'runtime_id': 'python-cpu-v1', 'entrypoint': entrypoint,
                'arguments': list(command[2:]), 'network': 'unrestricted'}
    _argument_templates(contract['arguments'])
    return contract, 'legacy command converted to supervisor-owned execution_contract'


def runtime_binary_hash():
    h = hashlib.sha256()
    try:
        with open(sys.executable, 'rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                h.update(chunk)
    except OSError as ex:
        raise EvidenceError('cannot hash runtime interpreter: ' + str(ex)) from ex
    return h.hexdigest()
