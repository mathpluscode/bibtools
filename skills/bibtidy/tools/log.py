#!/usr/bin/env python3
"""Logging helper that tees stdout/stderr to a .bib.log file."""

from __future__ import annotations

import os
import sys


class _Tee:
    """Write to both the original stream and a log file."""

    def __init__(self, original: object, log_file: object) -> None:
        self.original = original
        self.log_file = log_file

    def write(self, data: str) -> int:
        self.original.write(data)
        self.log_file.write(data)
        return len(data)

    def flush(self) -> None:
        self.original.flush()
        self.log_file.flush()


def _is_codex_runtime() -> bool:
    """Return True when running inside a Codex process."""
    return any(
        os.environ.get(name) for name in ("CODEX_THREAD_ID", "CODEX_SHELL", "CODEX_INTERNAL_ORIGINATOR_OVERRIDE")
    )


def _platform_suffix() -> str:
    """Return a platform-specific log suffix based on the runtime environment."""
    if _is_codex_runtime():
        return ".codex.log"
    return ".cc.log"


def setup(bib_path: str) -> None:
    """Tee stdout and stderr to ``<bib_path>.<platform>.log`` (append mode)."""
    log_path = bib_path + _platform_suffix()
    log_file = open(log_path, "a", encoding="utf-8")  # noqa: SIM115
    sys.stdout = _Tee(sys.stdout, log_file)  # type: ignore[assignment]
    sys.stderr = _Tee(sys.stderr, log_file)  # type: ignore[assignment]
