import pytest

from parch.typst_emit import typst_emit


def test_literal_passes_through():
    assert typst_emit(t"hello") == "hello"


def test_interpolation_uses_str():
    value = 15
    assert typst_emit(t"[{value}]") == "[15]"


def test_empty_format_spec_is_identity_str():
    source_id = "2026-01-15"
    text = "15"
    assert typst_emit(t"padded_link(<{source_id}>)[{text}]") == "padded_link(<2026-01-15>)[15]"
    n = 3
    assert typst_emit(t"{n:}") == "3"


def test_nonempty_format_spec_raises():
    value = "x"
    with pytest.raises(ValueError, match="format_spec"):
        typst_emit(t"{value:str}")
