"""Tests for the _extract_json helper in openai_provider."""
from __future__ import annotations

import pytest

from app.providers.openai_provider import _extract_json


class TestExtractJsonCodeFences:
    """Cases where the input contains markdown code fences."""

    def test_json_language_tag(self) -> None:
        text = '```json\n{"key": "value"}\n```'
        assert _extract_json(text) == '{"key": "value"}'

    def test_no_language_tag(self) -> None:
        text = '```\n{"key": "value"}\n```'
        assert _extract_json(text) == '{"key": "value"}'

    def test_prose_before_and_after_fence(self) -> None:
        text = 'Here is the result:\n```json\n{"score": 42}\n```\nDone.'
        assert _extract_json(text) == '{"score": 42}'

    def test_fence_with_leading_trailing_whitespace_inside(self) -> None:
        text = "```json\n\n  {\"a\": 1}  \n\n```"
        assert _extract_json(text) == '{"a": 1}'

    def test_whitespace_only_around_fence_markers(self) -> None:
        # Extra blank lines before and after the fences
        text = "\n\n```json\n{\"x\": true}\n```\n\n"
        assert _extract_json(text) == '{"x": true}'

    def test_multiple_code_blocks_returns_first(self) -> None:
        text = '```json\n{"first": 1}\n```\nsome text\n```json\n{"second": 2}\n```'
        assert _extract_json(text) == '{"first": 1}'

    def test_nested_braces_inside_fence(self) -> None:
        text = '```json\n{"outer": {"inner": [1, 2, 3]}}\n```'
        assert _extract_json(text) == '{"outer": {"inner": [1, 2, 3]}}'

    def test_multiline_json_inside_fence(self) -> None:
        text = '```json\n{\n  "key": "value",\n  "num": 99\n}\n```'
        assert _extract_json(text) == '{\n  "key": "value",\n  "num": 99\n}'


class TestExtractJsonRawBraces:
    """Cases where there are no code fences; extraction uses brace heuristic."""

    def test_plain_json_object(self) -> None:
        text = '{"name": "Alice", "age": 30}'
        assert _extract_json(text) == '{"name": "Alice", "age": 30}'

    def test_prose_surrounding_json(self) -> None:
        text = 'The analysis result is {"status": "ok"} as expected.'
        assert _extract_json(text) == '{"status": "ok"}'

    def test_prose_before_json_only(self) -> None:
        text = 'Result: {"found": true}'
        assert _extract_json(text) == '{"found": true}'

    def test_prose_after_json_only(self) -> None:
        text = '{"done": false} — that is all.'
        assert _extract_json(text) == '{"done": false}'

    def test_nested_braces_raw(self) -> None:
        text = '{"outer": {"a": {"b": 1}}}'
        assert _extract_json(text) == '{"outer": {"a": {"b": 1}}}'

    def test_last_closing_brace_used(self) -> None:
        # rfind("}") must reach the outermost closing brace
        text = 'prefix {"k": {"v": 1}} suffix'
        assert _extract_json(text) == '{"k": {"v": 1}}'

    def test_leading_whitespace_stripped_before_search(self) -> None:
        text = '   {"trimmed": true}   '
        assert _extract_json(text) == '{"trimmed": true}'


class TestExtractJsonFallthrough:
    """Cases where no JSON markers exist; original text is returned."""

    def test_plain_string_no_braces(self) -> None:
        text = "no json here at all"
        assert _extract_json(text) == "no json here at all"

    def test_only_opening_brace(self) -> None:
        # start != -1 but end == -1 → falls through
        text = "{ incomplete"
        assert _extract_json(text) == "{ incomplete"

    def test_only_closing_brace(self) -> None:
        # start == -1 → falls through
        text = "incomplete }"
        assert _extract_json(text) == "incomplete }"

    def test_closing_before_opening_brace(self) -> None:
        # end < start → condition `end > start` is False → falls through
        text = "} then {"
        assert _extract_json(text) == "} then {"

    def test_empty_string(self) -> None:
        result = _extract_json("")
        assert result == ""

    def test_whitespace_only_string(self) -> None:
        # strip() leaves empty string; no braces found
        result = _extract_json("   ")
        assert result == ""


class TestExtractJsonReturnType:
    """Invariant: _extract_json always returns a str."""

    @pytest.mark.parametrize(
        "text",
        [
            "",
            "no markers",
            '{"valid": "json"}',
            '```json\n{"fenced": true}\n```',
            '```\n{"fenced": true}\n```',
        ],
    )
    def test_always_returns_str(self, text: str) -> None:
        assert isinstance(_extract_json(text), str)


# ---------------------------------------------------------------------------
# New: JS-style // comments (pass-through — repair is handled by _repair_json)
# ---------------------------------------------------------------------------


class TestExtractJsonComments:
    """_extract_json does not strip comments — it only extracts boundaries.

    Comment removal is delegated to _repair_json. These tests document the
    exact boundary behaviour so that future refactors cannot silently alter it.
    """

    def test_js_line_comment_passed_through_raw_braces(self) -> None:
        # _extract_json isolates the JSON text; comments survive extraction
        text = '{"a": 1, // comment\n"b": 2}'
        result = _extract_json(text)
        # brace heuristic: from first { to last }
        assert result == '{"a": 1, // comment\n"b": 2}'

    def test_js_line_comment_inside_fence_preserved(self) -> None:
        text = '```json\n{"x": 1 // inline\n}\n```'
        result = _extract_json(text)
        assert result == '{"x": 1 // inline\n}'

    def test_block_comment_passed_through_unchanged(self) -> None:
        # /* */ block comments are NOT removed by _repair_json either —
        # this documents the current implementation boundary.
        text = '{"key": /* comment */ "value"}'
        result = _extract_json(text)
        assert result == '{"key": /* comment */ "value"}'


# ---------------------------------------------------------------------------
# New: trailing commas — extraction is unaffected (repair is separate)
# ---------------------------------------------------------------------------


class TestExtractJsonTrailingCommas:
    """_extract_json returns the raw text; trailing-comma removal is in _repair_json."""

    def test_trailing_comma_in_object_extracted_verbatim(self) -> None:
        text = '{"a": 1, "b": 2,}'
        result = _extract_json(text)
        assert result == '{"a": 1, "b": 2,}'

    def test_trailing_comma_in_array_extracted_verbatim(self) -> None:
        text = '{"items": [1, 2, 3,]}'
        result = _extract_json(text)
        assert result == '{"items": [1, 2, 3,]}'

    def test_trailing_comma_inside_fence_extracted_verbatim(self) -> None:
        text = '```json\n{"x": [1,]}\n```'
        result = _extract_json(text)
        assert result == '{"x": [1,]}'


# ---------------------------------------------------------------------------
# New: single-quoted JSON
# ---------------------------------------------------------------------------


class TestExtractJsonSingleQuotes:
    """Single-quoted JSON is not valid JSON; _extract_json extracts boundaries only."""

    def test_single_quoted_object_extracted_by_brace_heuristic(self) -> None:
        text = "{'key': 'value'}"
        result = _extract_json(text)
        # braces are found — extraction succeeds; parsing would still fail
        assert result == "{'key': 'value'}"

    def test_single_quoted_inside_fence_extracted(self) -> None:
        text = "```json\n{'a': 1}\n```"
        result = _extract_json(text)
        assert result == "{'a': 1}"


# ---------------------------------------------------------------------------
# New: unicode escape sequences
# ---------------------------------------------------------------------------


class TestExtractJsonUnicodeEscapes:
    """Unicode escapes inside strings are transparent to _extract_json."""

    def test_unicode_escape_in_value_extracted_cleanly(self) -> None:
        text = '{"name": "caf\\u00e9"}'
        result = _extract_json(text)
        assert result == '{"name": "caf\\u00e9"}'

    def test_unicode_escape_in_key_extracted_cleanly(self) -> None:
        text = '{"\\u0061": 1}'  # \u0061 == "a"
        result = _extract_json(text)
        assert result == '{"\\u0061": 1}'

    def test_unicode_escape_inside_fence_extracted_cleanly(self) -> None:
        text = '```json\n{"emoji": "\\u2764"}\n```'
        result = _extract_json(text)
        assert result == '{"emoji": "\\u2764"}'


# ---------------------------------------------------------------------------
# New: deeply nested JSON
# ---------------------------------------------------------------------------


class TestExtractJsonDeeplyNested:
    """Deeply nested objects and arrays rely on the brace heuristic."""

    def test_five_levels_deep_raw(self) -> None:
        text = '{"l1": {"l2": {"l3": {"l4": {"l5": "deep"}}}}}'
        result = _extract_json(text)
        assert result == '{"l1": {"l2": {"l3": {"l4": {"l5": "deep"}}}}}'

    def test_five_levels_deep_in_fence(self) -> None:
        payload = '{"a": {"b": {"c": {"d": {"e": 42}}}}}'
        text = f"```json\n{payload}\n```"
        result = _extract_json(text)
        assert result == payload

    def test_nested_arrays_inside_objects(self) -> None:
        text = '{"matrix": [[1, [2, [3, [4]]]], 5]}'
        result = _extract_json(text)
        assert result == '{"matrix": [[1, [2, [3, [4]]]], 5]}'


# ---------------------------------------------------------------------------
# New: newlines in string values
# ---------------------------------------------------------------------------


class TestExtractJsonNewlinesInStrings:
    """Newlines embedded in string values should be preserved through extraction."""

    def test_escaped_newline_in_value_preserved_raw(self) -> None:
        text = '{"summary": "line1\\nline2"}'
        result = _extract_json(text)
        assert result == '{"summary": "line1\\nline2"}'

    def test_literal_newline_in_value_preserved_raw(self) -> None:
        # Literal newline inside the string — unusual but some LLMs emit it
        text = '{"text": "hello\nworld"}'
        result = _extract_json(text)
        assert result == '{"text": "hello\nworld"}'

    def test_multiline_value_inside_fence(self) -> None:
        payload = '{"note": "first line\\nsecond line"}'
        text = f"```json\n{payload}\n```"
        result = _extract_json(text)
        assert result == payload


# ---------------------------------------------------------------------------
# New: multiple JSON objects with no fences (brace heuristic behaviour)
# ---------------------------------------------------------------------------


class TestExtractJsonMultipleObjects:
    """When no fence is present, brace heuristic spans first { to last }.

    This means multiple adjacent JSON objects are returned as one blob —
    documenting exact behaviour so callers understand the contract.
    """

    def test_two_json_objects_spans_first_to_last_brace(self) -> None:
        # rfind("}") reaches the closing brace of the second object
        text = '{"a": 1} {"b": 2}'
        result = _extract_json(text)
        assert result == '{"a": 1} {"b": 2}'

    def test_json_object_followed_by_prose_and_another_object(self) -> None:
        text = 'result: {"x": 1} and also {"y": 2} end'
        result = _extract_json(text)
        assert result == '{"x": 1} and also {"y": 2}'
