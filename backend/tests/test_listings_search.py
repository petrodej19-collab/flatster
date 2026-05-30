from app.api.listings import _search_tokens


def test_empty_string_returns_empty_list():
    assert _search_tokens("") == []


def test_whitespace_only_returns_empty_list():
    assert _search_tokens("   \t\n  ") == []


def test_single_token_lowercased():
    assert _search_tokens("Tržaška") == ["tržaška"]


def test_multiple_tokens_split_on_whitespace():
    assert _search_tokens("novogradnja balkon") == ["novogradnja", "balkon"]


def test_consecutive_spaces_collapsed():
    assert _search_tokens("novogradnja   balkon") == ["novogradnja", "balkon"]
