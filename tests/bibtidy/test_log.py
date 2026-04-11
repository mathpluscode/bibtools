#!/usr/bin/env python3
"""Tests for log.py runtime detection."""

import os

import pytest

import log


def _clear_codex_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in list(os.environ):
        if key.startswith("CODEX_"):
            monkeypatch.delenv(key, raising=False)


class TestPlatformSuffix:
    def test_defaults_to_claude_without_codex_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _clear_codex_env(monkeypatch)
        assert log._platform_suffix() == ".cc.log"

    @pytest.mark.parametrize("env_name", ["CODEX_THREAD_ID", "CODEX_SHELL", "CODEX_INTERNAL_ORIGINATOR_OVERRIDE"])
    def test_uses_codex_suffix_for_codex_runtime(self, monkeypatch: pytest.MonkeyPatch, env_name: str) -> None:
        _clear_codex_env(monkeypatch)
        monkeypatch.setenv(env_name, "1")
        assert log._platform_suffix() == ".codex.log"
