"""Independent binary metrics. Standard library only; no project metric imports."""
import math
import itertools
import random
from statistics import mean, stdev

class EvidenceError(ValueError):
    pass

def number(x):
    if isinstance(x, bool):
        raise EvidenceError('boolean is not a numeric measurement')
    try:
        v = float(x)
    except (TypeError, ValueError):
        raise EvidenceError(f'not numeric: {x!r}')
    if not math.isfinite(v):
        raise EvidenceError('non-finite measurement; never sanitize into a score')
    return v

def binary_metrics(labels, scores, threshold=0.5):
    y, s = list(map(number, labels)), list(map(number, scores))
    threshold = number(threshold)
    if len(y) != len(s) or not y or set(y) != {0., 1.}:
        raise EvidenceError('binary evaluation requires both classes and equal nonempty vectors')
    if any(not 0 <= v <= 1 for v in s) or not 0 <= threshold <= 1:
        raise EvidenceError('probabilities/threshold outside [0,1]')
    n, pos = len(y), sum(y)
    neg = n - pos
    # Increasing scores, average ranks for ties (Mann-Whitney definition).
    ordered = sorted(zip(s, y))
    rank_sum, i = 0., 0
    while i < n:
        j = i + 1
        while j < n and ordered[j][0] == ordered[i][0]:
            j += 1
        rank_sum += (i + 1 + j) / 2 * sum(z[1] for z in ordered[i:j])
        i = j
    auroc = (rank_sum - pos * (pos + 1) / 2) / (pos * neg)
    # Non-interpolated average precision: grouped thresholds, not trapezoidal PR area.
    ordered.reverse()
    tp, seen, ap, i = 0., 0, 0., 0
    while i < n:
        j = i + 1
        while j < n and ordered[j][0] == ordered[i][0]:
            j += 1
        added = sum(z[1] for z in ordered[i:j])
        tp += added
        seen += j - i
        ap += (added / pos) * (tp / seen)
        i = j
    pred = [int(v >= threshold) for v in s]
    tp = sum(a == 1 and b == 1 for a, b in zip(y, pred))
    fp = sum(a == 0 and b == 1 for a, b in zip(y, pred))
    fn = sum(a == 1 and b == 0 for a, b in zip(y, pred))
    eps = 1e-15  # Only log-loss boundary handling; input NaN/Inf is rejected above.
    return {'auroc': auroc, 'average_precision': ap,
            'accuracy': sum(a == b for a, b in zip(y, pred)) / n,
            'f1': 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.,
            'brier': mean((a-b)**2 for a,b in zip(y,s)),
            'log_loss': -mean(a*math.log(min(1-eps,max(eps,b))) +
                             (1-a)*math.log(min(1-eps,max(eps,1-b))) for a,b in zip(y,s))}

def quantile(values, q):
    a = sorted(map(number, values))
    if not a or not 0 <= q <= 1:
        raise EvidenceError('invalid quantile')
    x = (len(a)-1) * q
    i = int(x)
    return a[i] if i == len(a)-1 else a[i] + (x-i)*(a[i+1]-a[i])

def paired_inference(a, b, *, seed=314159, draws=10000, alpha=0.05):
    """Paired mean difference, percentile CI, two-sided sign-flip randomization test.

    Units must be exchangeable under the null; inference is conditional on those
    units. Does not turn repeated predictions into independent population samples.
    """
    if len(a) != len(b) or len(a) < 2:
        raise EvidenceError('paired inference needs >=2 aligned independent units')
    d = [number(x)-number(y) for x,y in zip(a,b)]
    n = len(d); observed = mean(d)
    if not 0 < alpha < 1 or draws < 1000:
        raise EvidenceError('invalid inference settings')
    rng = random.Random(seed)
    boot = [mean(rng.choices(d, k=n)) for _ in range(draws)]
    if n <= 16:
        extreme = sum(abs(sum(x*t for x,t in zip(d,signs))/n) >= abs(observed)-1e-14
                      for signs in itertools.product((-1,1), repeat=n))
        p = extreme / (2**n)
        method = 'exact_two_sided_paired_sign_flip'
    else:
        extreme = sum(abs(sum(x*rng.choice((-1,1)) for x in d)/n) >= abs(observed)-1e-14
                      for _ in range(draws))
        p = (extreme+1)/(draws+1)
        method = 'monte_carlo_two_sided_paired_sign_flip_plus_one'
    sd = stdev(d)
    return {'effect': observed, 'ci': [quantile(boot,alpha/2),quantile(boot,1-alpha/2)],
            'p_raw': p, 'paired_dz': observed/sd if sd > 0 else None,
            'n_units': n, 'test': method, 'ci_method': 'paired_percentile_bootstrap',
            'degenerate_variance': sd == 0, 'draws': draws, 'analysis_seed': seed}

def holm(pvalues):
    vals = [number(x) for x in pvalues]
    if any(not 0 <= p <= 1 for p in vals):
        raise EvidenceError('invalid p-value')
    out = [0.] * len(vals); prior = 0.
    for rank, i in enumerate(sorted(range(len(vals)), key=lambda j: vals[j])):
        prior = max(prior, min(1., (len(vals)-rank)*vals[i]))
        out[i] = prior
    return out
