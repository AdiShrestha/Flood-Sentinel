"""Independent binary metrics. Standard library only; no project metric imports."""
import math
import itertools
import random
from statistics import mean, stdev, NormalDist

class EvidenceError(ValueError):
    pass

def _vector(values, name):
    if isinstance(values, (str, bytes, dict)):
        raise EvidenceError(name+' must be a measurement vector')
    try:
        return list(map(number, values))
    except TypeError as error:
        raise EvidenceError(name+' must be a measurement vector') from error

def number(x):
    if isinstance(x, bool):
        raise EvidenceError('boolean is not a numeric measurement')
    try:
        v = float(x)
    except (TypeError, ValueError, OverflowError):
        raise EvidenceError(f'not numeric: {x!r}')
    if not math.isfinite(v):
        raise EvidenceError('non-finite measurement; never sanitize into a score')
    return v

def binary_metrics(labels, scores, threshold=0.5):
    y, s = _vector(labels, 'labels'), _vector(scores, 'scores')
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
    a = sorted(_vector(values, 'quantile values'))
    q = number(q)
    if not a or not 0 <= q <= 1:
        raise EvidenceError('invalid quantile')
    x = (len(a)-1) * q
    i = int(x)
    return a[i] if i == len(a)-1 else a[i] + (x-i)*(a[i+1]-a[i])

def _settings(seed, draws, alpha):
    if type(seed) is not int or type(draws) is not int or not 1000 <= draws <= 1000000:
        raise EvidenceError('inference requires integer seed and 1000..1000000 draws')
    alpha = number(alpha)
    if not 0 < alpha < 1:
        raise EvidenceError('invalid inference alpha')
    return alpha


def _beta_fraction(a, b, x):
    """Continued fraction for regularized incomplete beta (Lentz method)."""
    tiny = 1e-300
    c, d = 1., 1. - (a + b) * x / (a + 1.)
    d = 1. / (d if abs(d) >= tiny else tiny)
    result = d
    for m in range(1, 301):
        m2 = 2 * m
        for term in (m * (b-m) * x / ((a+m2-1) * (a+m2)),
                     -(a+m) * (a+b+m) * x / ((a+m2) * (a+m2+1))):
            d = 1. + term * d
            d = 1. / (d if abs(d) >= tiny else tiny)
            c = 1. + term / c
            if abs(c) < tiny:
                c = tiny
            change = c * d
            result *= change
        if abs(change - 1.) < 3e-14:
            return result
    raise EvidenceError('Student-t quantile did not converge')


def _regularized_beta(x, a, b):
    if x <= 0:
        return 0.
    if x >= 1:
        return 1.
    front = math.exp(math.lgamma(a+b) - math.lgamma(a) - math.lgamma(b)
                     + a * math.log(x) + b * math.log1p(-x))
    if x < (a+1) / (a+b+2):
        return front * _beta_fraction(a, b, x) / a
    return 1. - front * _beta_fraction(b, a, 1.-x) / b


def student_t_critical(alpha, degrees_of_freedom):
    """Two-sided t critical value without a third-party runtime dependency."""
    alpha = number(alpha)
    if not 0 < alpha < 1 or type(degrees_of_freedom) is not int or degrees_of_freedom < 1:
        raise EvidenceError('invalid Student-t settings')
    df = degrees_of_freedom
    low, high = 0., 1.
    def tail(value):
        return _regularized_beta(df / (df + value * value), df / 2., .5)
    while tail(high) > alpha:
        high *= 2
        if not math.isfinite(high * high):
            raise EvidenceError('unrepresentable Student-t critical value')
    for _ in range(80):
        middle = (low + high) / 2
        if tail(middle) > alpha:
            low = middle
        else:
            high = middle
    return (low + high) / 2


def _extreme(value, observed):
    # A scale-relative tolerance avoids erasing evidence when effects are tiny.
    tolerance = max(math.ulp(abs(observed)) * 8, abs(observed) * 1e-12)
    return abs(value) >= abs(observed) - tolerance


def paired_inference(a, b, *, seed=314159, draws=10000, alpha=0.05):
    """Paired mean difference, Student-t CI, two-sided sign-flip test.

    The CI assumes independent, normally distributed paired differences. The
    randomization test requires sign exchangeability under its null. For seed
    units both are conditional on the fixed test corpus, not population inference.
    """
    a, b = _vector(a, 'paired A'), _vector(b, 'paired B')
    if len(a) != len(b) or len(a) < 2:
        raise EvidenceError('paired inference needs >=2 aligned independent units')
    d = [number(x)-number(y) for x,y in zip(a,b)]
    if not all(math.isfinite(value) for value in d):
        raise EvidenceError('unrepresentable paired difference')
    n = len(d); observed = mean(d)
    alpha = _settings(seed, draws, alpha)
    rng = random.Random(seed)
    if n <= 16:
        extreme = sum(_extreme(mean(x*t for x,t in zip(d,signs)), observed)
                      for signs in itertools.product((-1,1), repeat=n))
        p = extreme / (2**n)
        method = 'exact_two_sided_paired_sign_flip'
    else:
        extreme = sum(_extreme(mean(x*rng.choice((-1,1)) for x in d), observed)
                      for _ in range(draws))
        p = (extreme+1)/(draws+1)
        method = 'monte_carlo_two_sided_paired_sign_flip_plus_one'
    sd = stdev(d)
    margin = student_t_critical(alpha, n-1) * sd / math.sqrt(n)
    if not math.isfinite(margin):
        raise EvidenceError('unrepresentable confidence interval')
    return {'effect': observed, 'ci': [observed-margin, observed+margin],
            'p_raw': p, 'paired_dz': observed/sd if sd > 0 else None,
            'n_units': n, 'test': method, 'ci_method': 'paired_student_t',
            'degenerate_variance': sd == 0, 'draws': draws, 'analysis_seed': seed,
            'inference_scope': 'fixed_test_corpus',
            'assumptions': ['independent paired seed differences',
                            'sign-exchangeability under the null',
                            'normal paired differences for Student-t CI']}


def _metric_value(labels, scores, metric, threshold):
    """Compute only the requested metric in resampling's inner loop."""
    n = len(labels)
    if metric == 'accuracy':
        return sum(label == (score >= threshold) for label, score in zip(labels, scores)) / n
    if metric == 'brier':
        return mean((label-score)**2 for label, score in zip(labels, scores))
    if metric == 'log_loss':
        return -mean(math.log(min(1-1e-15, max(1e-15, score if label else 1-score)))
                     for label, score in zip(labels, scores))
    if metric == 'f1':
        positive = sum(score >= threshold for score in scores)
        true_positive = sum(label and score >= threshold for label, score in zip(labels, scores))
        denominator = positive + sum(labels)
        return 2 * true_positive / denominator if denominator else 0.
    return binary_metrics(labels, scores, threshold)[metric]


def _bca_interval(boot, observed, jackknife_strata, alpha):
    """Bias-corrected accelerated paired bootstrap with explicit degeneracy."""
    if not boot or min(boot) == max(boot):
        return None
    normal = NormalDist()
    fraction = (sum(value < observed for value in boot)
                + .5 * sum(value == observed for value in boot)) / len(boot)
    # Finite Monte Carlo tail resolution; never pass +/-infinity to inv_cdf.
    fraction = min(1-.5/len(boot), max(.5/len(boot), fraction))
    bias = normal.inv_cdf(fraction)
    # Separate case/control samples require the multi-sample jackknife scaling:
    # (n_s-1)*(mean(leave-one-out_s)-theta_i)/n_s, for each stratum s.
    changes = []
    for jackknife in jackknife_strata:
        center = mean(jackknife)
        size = len(jackknife)
        changes.extend((size-1) * (center-value) / size for value in jackknife)
    denominator = 6 * sum(value*value for value in changes)**1.5
    acceleration = sum(value**3 for value in changes) / denominator if denominator else 0.
    adjusted = []
    for probability in (alpha/2, 1-alpha/2):
        z = normal.inv_cdf(probability)
        divisor = 1-acceleration*(bias+z)
        if divisor <= 0:
            return None
        adjusted.append(normal.cdf(bias+(bias+z)/divisor))
    if adjusted[0] >= adjusted[1]:
        return None
    return [quantile(boot, probability) for probability in adjusted]


def paired_group_inference(labels, score_pairs, groups, metric, *, thresholds=None,
                           seed=314159, draws=2000, alpha=0.05):
    """Compare trained models by paired swaps and BCa resampling of test groups.

    ``score_pairs`` contains aligned (A, B) prediction vectors for each repeated
    training seed. One group's model assignment swaps across every seed together;
    seeds never multiply independent test units. The statistic is the mean of
    per-seed pooled-cohort metric differences, oriented as improvement for A.

    Population inference is conditional on the supplied trained models and
    independent, representative test groups. Swaps require group-level model
    assignment exchangeability under the sharp null; BCa coverage is approximate.
    """
    alpha = _settings(seed, draws, alpha)
    if not isinstance(metric, str) or metric not in {'auroc', 'average_precision', 'accuracy', 'f1', 'brier', 'log_loss'}:
        raise EvidenceError('unsupported group-inference metric')
    y = _vector(labels, 'group labels')
    if not isinstance(groups, (list, tuple)):
        raise EvidenceError('group IDs must be an aligned vector')
    if not y or set(y) != {0., 1.} or len(groups) != len(y):
        raise EvidenceError('group inference needs aligned binary labels and groups')
    grouped = {}
    for index, group in enumerate(groups):
        if not isinstance(group, str) or not group.strip():
            raise EvidenceError('group inference requires nonempty string group IDs')
        grouped.setdefault(group, []).append(index)
    units = list(grouped.values())
    n = len(units)
    if n < 2 or not isinstance(score_pairs, (list, tuple)) or not score_pairs:
        raise EvidenceError('group inference needs >=2 independent groups and score pairs')
    if thresholds is None:
        thresholds = [(.5, .5)] * len(score_pairs)
    if not isinstance(thresholds, (list, tuple)):
        raise EvidenceError('threshold pairs must be an aligned vector')
    if len(thresholds) != len(score_pairs):
        raise EvidenceError('threshold pairs are not aligned to score pairs')
    pairs = []
    for pair, threshold_pair in zip(score_pairs, thresholds):
        if not isinstance(pair, (list, tuple)) or len(pair) != 2 or not isinstance(threshold_pair, (list, tuple)) or len(threshold_pair) != 2:
            raise EvidenceError('each prediction/threshold pair needs two vectors/values')
        a, b = (_vector(vector, 'group scores') for vector in pair)
        ta, tb = map(number, threshold_pair)
        if len(a) != len(y) or len(b) != len(y) or any(not 0 <= value <= 1 for value in a+b+[ta,tb]):
            raise EvidenceError('unaligned or invalid group prediction probabilities')
        pairs.append((a, b, ta, tb))
    sign = -1 if metric in ('brier', 'log_loss') else 1
    all_indices = list(range(len(y)))
    def statistic(indices, swaps=None):
        ys = [y[index] for index in indices]
        if set(ys) != {0., 1.}:
            raise EvidenceError('group resample lacks a class; empirical CI is not estimable')
        differences = []
        for a, b, ta, tb in pairs:
            av = [b[index] if swaps and index in swaps else a[index] for index in indices]
            bv = [a[index] if swaps and index in swaps else b[index] for index in indices]
            # Thresholds are part of each method. Swapping its assignment must
            # also swap its per-item decision threshold for classification metrics.
            if swaps and metric in ('accuracy', 'f1') and ta != tb:
                av = [float(value >= (tb if index in swaps else ta)) for index, value in zip(indices, av)]
                bv = [float(value >= (ta if index in swaps else tb)) for index, value in zip(indices, bv)]
                threshold_a = threshold_b = .5
            else:
                threshold_a, threshold_b = ta, tb
            differences.append(sign * (_metric_value(ys, av, metric, threshold_a)
                                       - _metric_value(ys, bv, metric, threshold_b)))
        return mean(differences)
    observed = statistic(all_indices)
    rng = random.Random(seed)
    exact = n <= 12
    assignments = itertools.product((False, True), repeat=n) if exact else (
        [bool(rng.getrandbits(1)) for _ in range(n)] for _ in range(draws))
    extreme, permutation_count = 0, 0
    for assignment in assignments:
        swaps = {index for selected, unit in zip(assignment, units) if selected for index in unit}
        extreme += _extreme(statistic(all_indices, swaps), observed)
        permutation_count += 1
    p = extreme / permutation_count if exact else (extreme+1)/(permutation_count+1)
    # For single-class clusters, a case/control bootstrap fixes the observed
    # numbers of clusters per class. Mixed clusters are sampled as whole groups.
    homogeneous = all(len({y[index] for index in unit}) == 1 for unit in units)
    strata = [[i for i, unit in enumerate(units) if y[unit[0]] == label]
              for label in (0., 1.)] if homogeneous else [list(range(n))]
    boot = []
    invalid = 0
    for _ in range(draws):
        selected = [group for stratum in strata for group in rng.choices(stratum, k=len(stratum))]
        indices = [index for group in selected for index in units[group]]
        try:
            boot.append(statistic(indices))
        except EvidenceError:
            invalid += 1
    jackknife_strata = []
    for stratum in strata:
        jackknife = []
        for group in stratum:
            excluded = set(units[group])
            try:
                jackknife.append(statistic([index for index in all_indices if index not in excluded]))
            except EvidenceError:
                pass
        jackknife_strata.append(jackknife)
    # Never silently discard non-estimable resamples or claim zero-width
    # population uncertainty when an empirical distribution is degenerate.
    ci = (_bca_interval(boot, observed, jackknife_strata, alpha)
          if not invalid and all(len(jackknife)==len(stratum) and len(stratum)>=2
                                 for jackknife,stratum in zip(jackknife_strata,strata)) else None)
    degenerate = ci is None
    if ci is None:
        bound = -math.log(1e-15) if metric == 'log_loss' else 1.
        ci = [-bound, bound]
    return {'effect': observed, 'ci': ci, 'p_raw': p, 'paired_dz': None,
            'n_units': n, 'n_seed_pairs': len(pairs),
            'test': ('exact' if exact else 'monte_carlo') + '_two_sided_paired_group_swap' + ('' if exact else '_plus_one'),
            'ci_method': 'paired_cluster_BCa' if not degenerate else 'nonestimable_BCa_metric_range',
            'bootstrap_stratification': 'label_homogeneous_groups' if homogeneous else 'none',
            'invalid_bootstrap_draws': invalid, 'degenerate_variance': degenerate,
            'draws': draws, 'analysis_seed': seed,
            'inference_scope': 'test_population_conditional_on_trained_models',
            'assumptions': ['independent representative test groups',
                            'group-level model-assignment exchangeability under the sharp null',
                            'BCa confidence interval coverage is approximate',
                            'training population and split variability are not estimated']}

def holm(pvalues):
    vals = _vector(pvalues, 'p-values')
    if any(not 0 <= p <= 1 for p in vals):
        raise EvidenceError('invalid p-value')
    out = [0.] * len(vals); prior = 0.
    for rank, i in enumerate(sorted(range(len(vals)), key=lambda j: vals[j])):
        prior = max(prior, min(1., (len(vals)-rank)*vals[i]))
        out[i] = prior
    return out
