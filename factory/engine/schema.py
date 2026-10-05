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
    try:
        fv = float(v)
    except (OverflowError, ValueError):
        raise ValidationError(field, 'must be a representable finite number', v) from None
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
    if not isinstance(v, str) or v not in allowed:
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
    expect_dict(obj, field)
    c = obj.get('convergence_evidence', obj)
    expect_dict(c, f'{field}.convergence_evidence')

    expect_int(c.get('epochs_trained'), f'{field}.epochs_trained', minimum=1)

    early = c.get('early_stopping_triggered')
    if early is not None:
        expect_bool(early, f'{field}.early_stopping_triggered')

    justification = c.get('justification')
    if justification is not None:
        expect_str(justification, f'{field}.justification', min_len=0)

    curve = c.get('loss_curve')
    if curve is not None:
        expect_list(curve, f'{field}.loss_curve', min_len=0)
        for i, value in enumerate(curve):
            expect_float(value, f'{field}.loss_curve[{i}]', minimum=0)

    threshold = c.get('criterion_threshold')
    if threshold is not None:
        t = expect_float(threshold, f'{field}.criterion_threshold')
        if t <= 0:
            raise ValidationError(f'{field}.criterion_threshold', 'must be > 0', threshold)

    return c


def validate_split_manifest(obj, field='manifest'):
    """Strict validation for split integrity manifests."""
    expect_dict(obj, field)

    counts = obj.get('test_label_distribution', obj.get('label_distribution'))
    if counts is None:
        raise ValidationError(f'{field}.test_label_distribution', 'missing label distribution')
    expect_dict(counts, f'{field}.test_label_distribution')
    if not counts:
        raise ValidationError(f'{field}.test_label_distribution', 'label distribution must not be empty')

    for k, v in counts.items():
        expect_int(v, f'{field}.test_label_distribution.{k}', minimum=0)

    justification = obj.get('sample_size_justification')
    if justification is not None:
        expect_str(justification, f'{field}.sample_size_justification', min_len=0)

    return obj


def validate_plausibility_entry(entry, field='entry'):
    """Validate a single plausibility entry for type correctness."""
    expect_dict(entry, field)
    # p_value must be a real number if present, not a string
    p = entry.get('p_value', entry.get('p'))
    if 'p_value' in entry or 'p' in entry:
        expect_float(p, f'{field}.p_value', minimum=0, maximum=1)
        if 'p_value' in entry and 'p' in entry:
            expect_float(entry['p'], f'{field}.p', minimum=0, maximum=1)
            if entry['p'] != p:
                raise ValidationError(field, 'conflicting p_value and p aliases')
    # confidence_interval must be [low, high] of numbers
    ci = entry.get('confidence_interval', entry.get('ci'))
    if 'confidence_interval' in entry or 'ci' in entry:
        expect_list(ci, f'{field}.confidence_interval', min_len=2, max_len=2)
        for i, v in enumerate(ci):
            expect_float(v, f'{field}.confidence_interval[{i}]')
        if ci[0] > ci[1]:
            raise ValidationError(f'{field}.confidence_interval', 'lower endpoint exceeds upper endpoint', ci)
        if 'confidence_interval' in entry and 'ci' in entry and entry['ci'] != ci:
            raise ValidationError(field, 'conflicting confidence_interval and ci aliases')
    return entry


def validate_reproduction_manifest(obj, field='manifest'):
    """Strict validation for reproducibility manifests."""
    expect_dict(obj, field)
    a = obj.get('original', obj.get('result'))
    b = obj.get('replay', obj.get('reproduction'))
    if not isinstance(a, dict):
        raise ValidationError(f'{field}.original', 'must be an object', a)
    if not isinstance(b, dict):
        raise ValidationError(f'{field}.replay', 'must be an object', b)

    tol = obj.get('tolerance', 1e-6)
    expect_float(tol, f'{field}.tolerance', minimum=0)
    if not a or not b:
        raise ValidationError(field, 'original and replay must contain measurements')
    for name, values in (('original', a), ('replay', b)):
        for key, value in values.items():
            expect_float(value, f'{field}.{name}.{key}')

    return obj


def validate_json_value(value, field='value', *, depth=0):
    """Validate native JSON types recursively before hashing or executing a config."""
    if depth > 100:
        raise ValidationError(field, 'JSON nesting exceeds 100 levels')
    if value is None or type(value) in (str, bool):
        return value
    if type(value) in (int, float):
        expect_float(value, field)
    elif isinstance(value, list):
        expect_list(value, field)
        for i, item in enumerate(value):
            validate_json_value(item, f'{field}[{i}]', depth=depth + 1)
    elif isinstance(value, dict):
        for key, item in value.items():
            expect_str(key, f'{field}.key', min_len=0)
            validate_json_value(item, f'{field}.{key}', depth=depth + 1)
    else:
        raise ValidationError(field, 'must be a JSON value', value)
    return value


def validate_split_support(counts, group_count, *, min_class_count, min_test_groups,
                           field='split'):
    """Shared binary support policy; prose never overrides a frozen numeric floor."""
    expect_dict(counts, field + '.label_counts')
    expect_int(group_count, field + '.group_count', minimum=0)
    expect_int(min_class_count, field + '.min_class_count', minimum=2)
    expect_int(min_test_groups, field + '.min_test_groups', minimum=2)
    for label in ('0', '1'):
        expect_int(counts.get(label, 0), field + '.label_counts.' + label,
                   minimum=min_class_count)
    if group_count < min_test_groups:
        raise ValidationError(field + '.group_count',
                              f'must be >= frozen minimum {min_test_groups}', group_count)
    return {'label_counts': dict(counts), 'group_count': group_count}


def validate_training_trace(policy, rows, epochs_trained, checkpoint_epoch,
                            field='training'):
    """Shared stopping/checkpoint check over the actual numbered validation trace.

    A supported stopping event verifies a preregistered rule, rather than proving
    global optimization or adequate research quality.
    """
    from statistics import mean
    from .metrics import number
    expect_dict(policy, field + '.policy')
    mode = expect_enum(policy.get('mode'), {'fixed', 'early_stopping'}, field + '.mode')
    minimum = expect_int(policy.get('min_epochs'), field + '.min_epochs', minimum=2)
    maximum = expect_int(policy.get('max_epochs'), field + '.max_epochs', minimum=minimum)
    expect_list(rows, field + '.history', min_len=minimum, max_len=maximum)
    expect_int(epochs_trained, field + '.epochs_trained', minimum=minimum, maximum=maximum)
    if epochs_trained != len(rows):
        raise ValidationError(field + '.epochs_trained', 'differs from raw history length')
    expect_int(checkpoint_epoch, field + '.checkpoint_epoch', minimum=1, maximum=len(rows))
    losses = []
    for i, row in enumerate(rows, 1):
        expect_dict(row, f'{field}.history[{i-1}]')
        raw_epoch = row.get('epoch')
        if not (type(raw_epoch) is int or isinstance(raw_epoch, str) and raw_epoch.isdigit()):
            raise ValidationError(field + '.history.epoch', 'must be an integer epoch')
        if int(raw_epoch) != i:
            raise ValidationError(field + '.history.epoch', 'noncontiguous/duplicate training history')
        for key in ('train_loss', 'validation_loss'):
            value = number(row.get(key))
            if value < 0:
                raise ValidationError(field + '.' + key, 'loss must be nonnegative')
        losses.append(number(row['validation_loss']))
    if mode == 'early_stopping':
        patience = expect_int(policy.get('patience'), field + '.patience', minimum=2)
        delta = expect_float(policy.get('min_delta'), field + '.min_delta', minimum=0)
        best, best_epoch, bad, stop = float('inf'), 0, 0, None
        for epoch, loss in enumerate(losses, 1):
            if loss < best - delta:
                best, best_epoch, bad = loss, epoch, 0
            else:
                bad += 1
            if epoch >= minimum and bad >= patience:
                stop = epoch
                break
        if stop != len(rows):
            raise ValidationError(field, 'early-stop event not supported by validation trace; budget exhaustion is not convergence')
        if checkpoint_epoch != best_epoch:
            raise ValidationError(field + '.checkpoint_epoch', 'violates frozen validation selection')
        return {'mode': mode, 'stop_epoch': stop, 'checkpoint_epoch': best_epoch}
    window = expect_int(policy.get('tail_window'), field + '.tail_window', minimum=2)
    tolerance = expect_float(policy.get('relative_tolerance'), field + '.relative_tolerance', minimum=0, maximum=.05)
    if tolerance == 0 or maximum < 2 * window:
        raise ValidationError(field, 'fixed training needs positive tolerance and two tail windows')
    if len(rows) != maximum:
        raise ValidationError(field, 'fixed budget not completed')
    previous = mean(losses[-2 * window:-window])
    drift = abs(mean(losses[-window:]) - previous) / max(abs(previous), 1e-12)
    if drift > tolerance:
        raise ValidationError(field, 'validation still changing at budget cap; extend prospectively')
    best_epoch = min(range(len(losses)), key=losses.__getitem__) + 1
    if checkpoint_epoch != best_epoch:
        raise ValidationError(field + '.checkpoint_epoch', 'fixed-budget best checkpoint mismatch')
    return {'mode': mode, 'relative_tail_drift': drift, 'checkpoint_epoch': best_epoch}
