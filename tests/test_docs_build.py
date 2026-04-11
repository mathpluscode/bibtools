#!/usr/bin/env python3
"""Tests for docs/build.py helpers."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


_MODULE_PATH = Path(__file__).resolve().parents[1] / "docs" / "build.py"
_SPEC = spec_from_file_location("docs_build", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
linkify = _MODULE.linkify


def test_linkify_preserves_query_params() -> None:
    result = linkify("see https://example.com?a=1&b=2 for more")
    assert 'href="https://example.com?a=1&amp;b=2"' in result
    assert ">https://example.com?a=1&amp;b=2</a>" in result


def test_linkify_escapes_non_url_text() -> None:
    result = linkify('5 < 6 and "ok" https://example.com?a=1&b=2')
    assert "5 &lt; 6 and &quot;ok&quot;" in result
    assert 'href="https://example.com?a=1&amp;b=2"' in result
