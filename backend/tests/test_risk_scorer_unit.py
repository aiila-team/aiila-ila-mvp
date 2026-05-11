from app.services.risk_scorer import RiskScorer


def test_normalize_clamps():
    s = RiskScorer()
    assert s._normalize(-5.0) == 0.0
    assert s._normalize(25.0) == 10.0
    assert s._normalize(3.3333) == 3.33


def test_score_to_level_buckets():
    s = RiskScorer()
    assert s._score_to_level(1.0) == "low"
    assert s._score_to_level(4.0) == "medium"
    assert s._score_to_level(7.0) == "high"
    assert s._score_to_level(9.5) == "critical"
