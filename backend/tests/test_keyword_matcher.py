from app.services.keyword_matcher import _corpus, _match_one


def test_exact_substring():
    c = _corpus("hello world", None)
    assert _match_one("world", c) == "exact"
    assert _match_one("missing", c) is None


def test_phrase_multiword():
    c = _corpus("The quick brown fox", None)
    assert _match_one("quick brown", c) == "phrase"


def test_phrase_quoted():
    c = _corpus('He said "attack" here', None)
    assert _match_one('"attack"', c) == "phrase"


def test_wildcard_token():
    c = _corpus("prefix bombing suffix", None)
    assert _match_one("bomb*", c) == "wildcard"
