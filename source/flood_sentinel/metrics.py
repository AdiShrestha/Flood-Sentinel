"""Reference metric arithmetic with ties and non-estimable cohorts explicit."""
import numpy as np


def aligned(y, score):
    labels = np.asarray(y)
    scores = np.asarray(score, dtype=float)
    if labels.ndim != 1 or scores.ndim != 1 or not len(labels) or len(labels) != len(scores):
        raise ValueError('Nonempty aligned 1D labels and scores required.')
    if not np.isin(labels, [0, 1]).all() or not np.isfinite(scores).all():
        raise ValueError('Labels must be binary and scores finite.')
    return labels.astype(int), scores


def ranking_metrics(y, score):
    """AUROC uses tied average ranks; AP uses threshold groups, not trapezoidal PR area."""
    y, s = aligned(y, score); pos = int(y.sum()); neg = len(y)-pos
    auc = None
    if pos and neg:
        order = np.argsort(s, kind='stable'); ranks = np.empty(len(s), dtype=float)
        i = 0
        while i < len(s):
            j = i+1
            while j < len(s) and s[order[j]] == s[order[i]]: j += 1
            ranks[order[i:j]] = (i+1+j)/2
            i = j
        auc = float((ranks[y == 1].sum() - pos*(pos+1)/2)/(pos*neg))
    ap = None
    if pos:
        order = np.argsort(-s, kind='stable'); tp = 0; area = 0.; i = 0
        while i < len(s):
            j = i+1
            while j < len(s) and s[order[j]] == s[order[i]]: j += 1
            added = int(y[order[i:j]].sum()); tp += added
            area += added/pos * tp/j
            i = j
        ap = float(area)
    return {'auroc': auc, 'average_precision': ap, 'n_positive': pos, 'n_negative': neg,
            'auroc_estimable': bool(pos and neg)}


def probability_metrics(y, probability, *, threshold: float):
    """All six factory metrics; only genuine probabilities may enter proper scoring rules."""
    y, p = aligned(y, probability)
    if not np.isfinite(threshold) or not 0 <= threshold <= 1 or ((p < 0) | (p > 1)).any():
        raise ValueError('Probabilities and threshold must lie in [0,1]; raw anomalies require a fitted adapter.')
    pred = p >= threshold; tp = int(np.sum(pred & (y == 1)))
    fp = int(np.sum(pred & (y == 0))); fn = int(np.sum(~pred & (y == 1)))
    ranks = ranking_metrics(y, p)
    # Clip each class likelihood independently, matching the factory oracle.
    # Clipping p once and then using 1-p changes the p=1 boundary by rounding.
    positive = np.clip(p, 1e-15, 1-1e-15)
    negative = np.clip(1-p, 1e-15, 1-1e-15)
    return {'auroc': ranks['auroc'], 'average_precision': ranks['average_precision'],
            'accuracy': float(np.mean(pred == y)), 'f1': float(2*tp/(2*tp+fp+fn)) if 2*tp+fp+fn else 0.,
            'brier': float(np.mean((p-y)**2)),
            'log_loss': float(-np.mean(y*np.log(positive)+(1-y)*np.log(negative)))}


def holm(p_values):
    p = np.asarray(p_values, dtype=float)
    if p.ndim != 1 or not np.isfinite(p).all() or ((p < 0) | (p > 1)).any():
        raise ValueError('Finite p-values in [0,1] required.')
    order = np.argsort(p); out = np.empty_like(p); previous = 0.
    for rank, index in enumerate(order):
        previous = max(previous, (len(p)-rank)*p[index]); out[index] = min(1., previous)
    return out.tolist()


def paired_cluster_interval(differences, *, n_resamples: int, seed: int, confidence: float = .95):
    """Bootstrap a mean of already paired independent cluster effects, not prediction rows.

    The caller must justify the cluster definition; a function cannot establish
    geographical independence or whether this mean matches the preregistered estimand.
    """
    d = np.asarray(differences, dtype=float)
    if d.ndim != 1 or len(d) < 2 or not np.isfinite(d).all():
        raise ValueError('At least two finite paired cluster effects required; undefined AUCs cannot be replaced by .5.')
    if type(n_resamples) is not int or n_resamples < 100 or not 0 < confidence < 1:
        raise ValueError('Declare >=100 bootstrap draws and confidence in (0,1).')
    rng = np.random.default_rng(seed)
    means = np.array([rng.choice(d, len(d), replace=True).mean() for _ in range(n_resamples)])
    alpha = (1-confidence)/2
    lo, hi = np.quantile(means, [alpha, 1-alpha])
    return {'mean_difference': float(d.mean()), 'ci': [float(lo), float(hi)],
            'n_clusters': len(d), 'resamples': n_resamples, 'seed': seed,
            'method': 'paired independent-cluster percentile bootstrap; assumptions require review'}
