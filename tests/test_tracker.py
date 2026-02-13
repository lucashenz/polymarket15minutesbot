from tracker.probability import normalize_binary_probabilities


def test_normalize_basic_pair():
    a, b = normalize_binary_probabilities(0.43, 0.57)
    assert round(a, 3) == 0.43
    assert round(b, 3) == 0.57


def test_normalize_with_discrepancy():
    a, b = normalize_binary_probabilities(0.60, 0.50)
    assert round(a + b, 8) == 1.0
    assert a > b


def test_normalize_none_cases():
    a, b = normalize_binary_probabilities(None, 0.2)
    assert a is None
    assert b == 1.0
