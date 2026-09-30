"""Strict typed schema validation. No implicit coercion, no justification bypass.

Every standalone validator and the certification path use these same functions.
There is one implementation path, not a permissive diagnostic path and a stricter
release path.
"""
from .metrics import EvidenceError


class ValidationError(EvidenceError):
    """Structured validation failure with field path and reason."""
    def __init__(self, field, reason, value=None):
        self.field = field
        self.reason = reason
        self.failed_value = value
        super().__init__(f'{field}: {reason}')


def expect_bool(v, field='value'):
    """Accept only JSON booleans True/False. Reject strings, ints, None."""
    if type(v) is not bool:
        raise ValidationError(field, 'must be a JSON boolean (true/false)', v)
    return v


def expect_int(v, field='value', *, minimum=None, maximum=None):
    """Accept only Python int. Reject bool, float, str."""
    if type(v) is not int:
        raise ValidationError(field, 'must be an integer', v)
    if minimum is not None and v < minimum:
        raise ValidationError(field, f'must be >= {minimum}', v)
    if maximum is not None and v > maximum:
        raise ValidationError(field, f'must be <= {maximum}', v)
    return v


def expect_float(v, field='value', *, finite=True, minimum=None, maximum=None):
    """Accept int or float, reject bool and str. Optionally enforce finite."""
    import math
    if type(v) is bool:
        raise ValidationError(field, 'boolean is not a number', v)
    if not isinstance(v, (int, float)):
        raise ValidationError(field, 'must be a number', v)
    fv = float(v)
    if finite and not math.isfinite(fv):
        raise ValidationError(field, 'must be finite', v)
    if minimum is not None and fv < minimum:
        raise ValidationError(field, f'must be >= {minimum}', v)
    if maximum is not None and fv > maximum:
        raise ValidationError(field, f'must be <= {maximum}', v)
    return fv


def expect_str(v, field='value', *, min_len=1, max_len=10000):
    """Accept only str with bounded length. Reject None, int, list."""
    if not isinstance(v, str):
        raise ValidationError(field, 'must be a string', v)
    if len(v) < min_len:
        raise ValidationError(field, f'must have length >= {min_len}', v)
    if len(v) > max_len:
        raise ValidationError(field, f'must have length <= {max_len}', v)
    return v


def expect_list(v, field='value', *, min_len=0, max_len=100000, element_validator=None):
    """Accept only list with minimum cardinality. Reject dict, str, None."""
    if not isinstance(v, list):
        raise ValidationError(field, 'must be a list', v)
    if len(v) < min_len:
        raise ValidationError(field, f'must have at least {min_len} elements', v)
    if len(v) > max_len:
        raise ValidationError(field, f'must have at most {max_len} elements', v)
    if element_validator:
        for i, item in enumerate(v):
            element_validator(item, f'{field}[{i}]')
    return v


def expect_dict(v, field='value', *, required_keys=None):
    """Accept only dict. Optionally check required keys."""
    if not isinstance(v, dict):
        raise ValidationError(field, 'must be an object', v)
    if required_keys:
        missing = set(required_keys) - set(v.keys())
        if missing:
            raise ValidationError(field, f'missing required keys: {sorted(missing)}', v)
    return v


def expect_enum(v, allowed, field='value'):
    """Exact match against allowed values. No case folding, no coercion."""
    if v not in allowed:
        raise ValidationError(field, f'must be one of {sorted(allowed) if isinstance(allowed, set) else list(allowed)}', v)
    return v


def expect_id(v, field='value', *, seen=None):
    """String matching [A-Za-z0-9_-]{1,80} with optional duplicate detection."""
    import re
    expect_str(v, field, min_len=1, max_len=80)
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', v):
        raise ValidationError(field, 'must match [A-Za-z0-9_-]{1,80}', v)
    if seen is not None:
        if v in seen:
            raise ValidationError(field, f'duplicate identifier: {v}', v)
        seen.add(v)
    return v


def validate_training_manifest(obj, field='manifest'):
    """Strict validation for training sufficiency manifests."""
    import math
    expect_dict(obj, field)
    c = obj.get('convergence_evidence', obj)
    expect_dict(c, f'{field}.convergence_evidence')

    epochs = c.get('epochs_trained')
    if type(epochs) is bool or not isinstance(epochs, (int, float)):
        raise ValidationError(f'{field}.epochs_trained', 'must be a finite number > 0', epochs)
    if not math.isfinite(float(epochs)) or epochs <= 0:
        raise ValidationError(f'{field}.epochs_trained', 'must be a finite number > 0', epochs)

    early = c.get('early_stopping_triggered')
    if early is not None:
        expect_bool(early, f'{field}.early_stopping_triggered')

    justification = c.get('justification')
    if justification is not None:
        expect_str(justification, f'{field}.justification', min_len=0)

    curve = c.get('loss_curve')
    if curve is not None:
        expect_list(curve, f'{field}.loss_curve', min_len=0)

    threshold = c.get('criterion_threshold')
    if threshold is not None:
        t = expect_float(threshold, f'{field}.criterion_threshold')
        if t <= 0:
            raise ValidationError(f'{field}.criterion_threshold', 'must be > 0', threshold)

    return c


def validate_split_manifest(obj, field='manifest'):
    """Strict validation for split integrity manifests."""
    import math
    expect_dict(obj, field)

    counts = obj.get('test_label_distribution', obj.get('label_distribution'))
    if counts is None:
        raise ValidationError(f'{field}.test_label_distribution', 'missing label distribution')
    expect_dict(counts, f'{field}.test_label_distribution')
    if not counts:
        raise ValidationError(f'{field}.test_label_distribution', 'label distribution must not be empty')

    for k, v in counts.items():
        if type(v) is bool:
            raise ValidationError(f'{field}.test_label_distribution.{k}', 'boolean is not a count', v)
        if not isinstance(v, (int, float)):
            raise ValidationError(f'{field}.test_label_distribution.{k}', 'must be a number', v)
        if not math.isfinite(float(v)) or v < 0:
            raise ValidationError(f'{field}.test_label_distribution.{k}', 'must be finite and >= 0', v)

    justification = obj.get('sample_size_justification')
    if justification is not None:
        expect_str(justification, f'{field}.sample_size_justification', min_len=0)

    return obj


def validate_plausibility_entry(entry, field='entry'):
    """Validate a single plausibility entry for type correctness."""
    expect_dict(entry, field)
    # p_value must be a real number if present, not a string
    p = entry.get('p_value', entry.get('p'))
    if p is not None:
        if type(p) is bool:
            raise ValidationError(f'{field}.p_value', 'boolean is not a p-value', p)
        if not isinstance(p, (int, float)):
            raise ValidationError(f'{field}.p_value', 'must be a number', p)
    # confidence_interval must be [low, high] of numbers
    ci = entry.get('confidence_interval', entry.get('ci'))
    if ci is not None:
        expect_list(ci, f'{field}.confidence_interval', min_len=2, max_len=2)
        for i, v in enumerate(ci):
            expect_float(v, f'{field}.confidence_interval[{i}]')
    return entry


def validate_reproduction_manifest(obj, field='manifest'):
    """Strict validation for reproducibility manifests."""
    import math
    expect_dict(obj, field)
    a = obj.get('original', obj.get('result'))
    b = obj.get('replay', obj.get('reproduction'))
    if not isinstance(a, dict):
        raise ValidationError(f'{field}.original', 'must be an object', a)
    if not isinstance(b, dict):
        raise ValidationError(f'{field}.replay', 'must be an object', b)

    tol = obj.get('tolerance', 1e-6)
    if tol is not None:
        t = expect_float(tol, f'{field}.tolerance')
        if not math.isfinite(t) or t < 0:
            raise ValidationError(f'{field}.tolerance', 'must be finite and >= 0', tol)

    return obj
