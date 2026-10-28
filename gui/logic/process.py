"""Runs external commands and streams their output to a log callback."""

from __future__ import annotations

import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path


def run_streamed(
    command: Sequence[str | Path],
    emit: Callable[[str], None],
    cwd: Path | None = None,
) -> None:
    """Run a command, forwarding each output line to ``emit``.

    Raises RuntimeError if the command exits with a non-zero status.
    """
    args = [str(part) for part in command]
    emit("$ " + " ".join(args))
    with subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(cwd) if cwd else None,
    ) as proc:
        assert proc.stdout is not None
        for line in proc.stdout:
            line = line.rstrip()
            if line:
                emit(line)
        code = proc.wait()
    if code != 0:
        raise RuntimeError(f"command exited with status {code}")
