"""Runs external commands and streams their output to a log callback."""

from __future__ import annotations

import subprocess
import urllib.request
from collections.abc import Callable, Sequence
from pathlib import Path


def download_file(url: str, destination: Path, emit: Callable[[str], None]) -> None:
    """Download ``url`` to ``destination``, emitting a progress bar about every 5%."""
    last_shown = -5

    def report(block_count: int, block_size: int, total_size: int) -> None:
        nonlocal last_shown
        if total_size <= 0:
            return
        done = min(block_count * block_size, total_size)
        percent = int(done * 100 / total_size)
        if percent - last_shown < 5 and done < total_size:
            return
        last_shown = percent
        filled = percent // 5
        bar = "#" * filled + "-" * (20 - filled)
        emit(f"[{bar}] {percent:3d}% ({done / 1_048_576:.1f} / {total_size / 1_048_576:.1f} MB)")

    urllib.request.urlretrieve(url, destination, report)


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
