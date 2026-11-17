"""Statistics students implement (M2 judge calibration, M4 paired bootstrap).

Rules: a judge is a classifier -- measure it like one. A higher mean is not
"better" until the paired CI of the difference excludes 0.
Reference values to self-check are in tests/test_lab9_stats.py.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from scipy import stats as scipy_stats

POS = "FAIL"   # the judge's job is to FIND failures, so FAIL is the positive class


def confusion(human: Sequence[str], judge: Sequence[str]) -> dict[str, int]:
    """tp/fp/fn/tn with FAIL as positive."""
    tp = sum(1 for h, j in zip(human, judge) if h == POS and j == POS)
    fp = sum(1 for h, j in zip(human, judge) if h != POS and j == POS)
    fn = sum(1 for h, j in zip(human, judge) if h == POS and j != POS)
    tn = sum(1 for h, j in zip(human, judge) if h != POS and j != POS)
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn}


def precision_recall(human: Sequence[str], judge: Sequence[str]) -> tuple[float, float]:
    """precision = tp/(tp+fp), recall = tp/(tp+fn); return 0.0 when the denominator is 0"""
    c = confusion(human, judge)
    p_denom = c["tp"] + c["fp"]
    r_denom = c["tp"] + c["fn"]
    
    p = c["tp"] / p_denom if p_denom > 0 else 0.0
    r = c["tp"] / r_denom if r_denom > 0 else 0.0
    return p, r


def cohen_kappa(human: Sequence[str], judge: Sequence[str]) -> float:
    """kappa = (p_o - p_e) / (1 - p_e). Raise ValueError when undefined (p_e == 1):
    a constant judge has no signal and must FAIL calibration, not pass on a technicality."""
    c = confusion(human, judge)
    n = c["tp"] + c["fp"] + c["fn"] + c["tn"]
    if n == 0:
        return 0.0

    p_o = (c["tp"] + c["tn"]) / n
    
    # Marginal probabilities
    p_h_pos = (c["tp"] + c["fn"]) / n
    p_j_pos = (c["tp"] + c["fp"]) / n
    p_h_neg = (c["tn"] + c["fp"]) / n
    p_j_neg = (c["tn"] + c["fn"]) / n
    
    p_e = (p_h_pos * p_j_pos) + (p_h_neg * p_j_neg)

    if p_e == 1.0:
        raise ValueError("Cohen's kappa is undefined because p_e == 1 (constant judge).")
        
    return (p_o - p_e) / (1 - p_e)


def rogan_gladen(observed_rate: float, sensitivity: float, specificity: float) -> float:
    """Correct an observed failure rate for judge error; clip to [0, 1].
    Formula: (p_obs + spec - 1) / (sens + spec - 1)"""
    denom = sensitivity + specificity - 1
    if denom == 0:
        return 0.0
    val = (observed_rate + specificity - 1) / denom
    return max(0.0, min(1.0, val))


def paired_bootstrap(a: Sequence[float], b: Sequence[float], *, n_resamples: int = 1000,
                     rng: int = 2027, confidence: float = 0.95) -> tuple[float, float, float]:
    """a[i], b[i] = per-item mean over seeds, SAME items, SAME order.
    Return (mean(a)-mean(b), lo, hi) with scipy.stats.bootstrap(paired=True, method="percentile",
    rng=numpy.random.default_rng(rng)). If a == b everywhere return (0.0, 0.0, 0.0)."""
    if list(a) == list(b):
        return 0.0, 0.0, 0.0

    a_arr = np.array(a)
    b_arr = np.array(b)
    d = float(np.mean(a_arr) - np.mean(b_arr))

    # Dùng paired bootstrap theo đúng docstring
    res = scipy_stats.bootstrap(
        (a_arr, b_arr),
        statistic=lambda x, y: np.mean(x) - np.mean(y),
        paired=True,
        method="percentile",
        rng=np.random.default_rng(rng),
        confidence_level=confidence,
        n_resamples=n_resamples
    )
    
    return d, float(res.confidence_interval.low), float(res.confidence_interval.high)


def pass_at_k(n: int, c: int, k: int) -> float:
    """Probability that AT LEAST ONE of k trials drawn from n (c of them passing) passes.
    Unbiased estimator (Chen et al. 2021): 1 - C(n-c, k) / C(n, k). Raise ValueError if k > n."""
    if k > n:
        raise ValueError("k cannot be greater than n")
    if n - c < k:
        return 1.0
    # Dùng math.comb (Python 3.8+)
    import math
    return 1.0 - (math.comb(n - c, k) / math.comb(n, k))


def pass_hat_k(n: int, c: int, k: int) -> float:
    """pass^k (tau-bench, Yao et al. 2024): probability that ALL k trials drawn from n pass.
    Unbiased estimator: C(c, k) / C(n, k). Raise ValueError if k > n.
    pass^k <= pass@1 <= pass@k; a reliable agent keeps pass^k close to pass@1."""
    if k > n:
        raise ValueError("k cannot be greater than n")
    if c < k:
        return 0.0
    import math
    return math.comb(c, k) / math.comb(n, k)