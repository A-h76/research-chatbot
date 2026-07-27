from backend.medical_understanding.security.regex_guard import RegexGuard


def test_compiles_a_safe_pattern():
    guard = RegexGuard()
    pattern = guard.safe_compile(r"diabetes|hypertension")
    assert pattern is not None
    assert guard.safe_search(pattern, "patient has diabetes") is not None


def test_rejects_catastrophic_backtracking_shape():
    guard = RegexGuard()
    assert guard.safe_compile(r"(a+)+$") is None


def test_rejects_overly_long_pattern():
    guard = RegexGuard(max_pattern_length=50)
    assert guard.safe_compile("a" * 100) is None


def test_rejects_invalid_regex_syntax():
    guard = RegexGuard()
    assert guard.safe_compile("[unclosed") is None


def test_compile_cache_returns_same_pattern_object():
    guard = RegexGuard()
    first = guard.safe_compile(r"diabetes")
    second = guard.safe_compile(r"diabetes")
    assert first is second


def test_safe_finditer_finds_all_matches():
    guard = RegexGuard()
    pattern = guard.safe_compile(r"\bcat\b")
    matches = guard.safe_finditer(pattern, "cat sat on the cat mat")
    assert len(matches) == 2


def test_safe_search_on_none_pattern_from_failed_compile_is_not_called():
    # A caller checking safe_compile()'s return before using it is the
    # documented contract — this just confirms a rejected pattern really
    # is None, not something that would blow up safe_search if misused.
    guard = RegexGuard()
    assert guard.safe_compile("(a+)+$") is None
