from app.api.listings import _escape_like, _search_tokens


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


def test_escape_like_passthrough_for_plain_text():
    assert _escape_like("balkon") == "balkon"


def test_escape_like_escapes_percent():
    assert _escape_like("50%") == "50\\%"


def test_escape_like_escapes_underscore():
    assert _escape_like("a_b") == "a\\_b"


def test_escape_like_escapes_backslash_first():
    # Backslash must be escaped first so we don't double-escape what the
    # other replaces inject.
    assert _escape_like("a\\b") == "a\\\\b"
    assert _escape_like("a\\%b") == "a\\\\\\%b"
