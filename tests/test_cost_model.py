from eval.cost_model import expected_cost, precision_recall_at
from eval.protocols import Trial

TRIALS = [
    Trial("s1.flac", "spoof"),
    Trial("s2.flac", "spoof"),
    Trial("b1.flac", "bonafide"),
    Trial("b2.flac", "bonafide"),
]
# perfectly separable: spoof scores high, bonafide scores low
SCORES = {"s1.flac": 0.9, "s2.flac": 0.8, "b1.flac": 0.2, "b2.flac": 0.1}


def test_expected_cost_zero_at_perfect_threshold():
    cost, p_fa, p_fr = expected_cost(SCORES, TRIALS, threshold=0.5, fraud_loss=100.0, support_cost=5.0)
    assert cost == 0.0
    assert p_fa == 0.0
    assert p_fr == 0.0


def test_expected_cost_penalizes_false_accepts():
    # threshold above every score -> nothing flagged -> both spoof trials get through
    cost, p_fa, p_fr = expected_cost(SCORES, TRIALS, threshold=1.0, fraud_loss=100.0, support_cost=5.0)
    assert p_fa == 1.0
    assert p_fr == 0.0
    assert cost == 100.0


def test_expected_cost_penalizes_false_rejects():
    # threshold below every score -> everything flagged -> both bonafide trials bounced
    cost, p_fa, p_fr = expected_cost(SCORES, TRIALS, threshold=0.0, fraud_loss=100.0, support_cost=5.0)
    assert p_fa == 0.0
    assert p_fr == 1.0
    assert cost == 5.0


def test_precision_recall_at_perfect_threshold():
    precision, recall = precision_recall_at(SCORES, TRIALS, threshold=0.5)
    assert precision == 1.0
    assert recall == 1.0


def test_nan_scores_excluded():
    scores = dict(SCORES)
    scores["s1.flac"] = float("nan")
    cost, p_fa, p_fr = expected_cost(scores, TRIALS, threshold=0.5, fraud_loss=100.0, support_cost=5.0)
    assert cost == 0.0  # s1 excluded, remaining trials still perfectly separated
