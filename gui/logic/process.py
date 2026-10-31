"""Runs external commands and streams their output to a log callback."""

from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Sequence
from pathlib import Path

USER_AGENT = "DiffSingerNorwegian-GUI"
CHUNK_SIZE = 1 << 20


class CancelledError(Exception):
    """Raised inside a task when the user pressed Cancel."""


CancelCheck = Callable[[], None]


def _progress_line(percent: int, done: int, total: int) -> str:
    filled = percent // 5
    bar = "#" * filled + "-" * (20 - filled)
    return f"[{bar}] {percent:3d}% ({done / 1_048_576:.1f} / {total / 1_048_576:.1f} MB)"


def _download_once(
    url: str,
    target: Path,
    emit: Callable[[str], None],
    should_cancel: CancelCheck | None,
    timeout: float,
) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    last_shown = -5
    written = 0
    with urllib.request.urlopen(request, timeout=timeout) as response:
        total = int(response.headers.get("Content-Length") or 0)
        with target.open("wb") as handle:
            while True:
                if should_cancel is not None:
                    should_cancel()
                chunk = response.read(CHUNK_SIZE)
                if not chunk:
                    break
                handle.write(chunk)
                written += len(chunk)
                if total > 0:
                    percent = min(int(written * 100 / total), 100)
                    if percent - last_shown >= 5 or written >= total:
                        last_shown = percent
                        emit(_progress_line(percent, written, total))
    if total > 0 and written != total:
        raise OSError(f"incomplete download ({written} of {total} bytes)")


def download_file(
    url: str,
    destination: Path,
    emit: Callable[[str], None],
    *,
    should_cancel: CancelCheck | None = None,
    retries: int = 2,
    timeout: float = 60.0,
) -> None:
    """Download ``url`` to ``destination``, emitting a progress bar every 5%.

    The file is written to a ``.part`` sibling and renamed only once complete,
    so an interrupted download can never be mistaken for a finished one. Failed
    attempts are retried a few times before the error is reported.
    """
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(destination.name + ".part")
    last_error: Exception | None = None

    for attempt in range(retries + 1):
        if attempt:
            if should_cancel is not None:
                should_cancel()
            delay = min(2.0 * attempt, 8.0)
            emit(f"Retrying download in {delay:g}s (attempt {attempt + 1}/{retries + 1})...")
            time.sleep(delay)
        try:
            _download_once(url, partial, emit, should_cancel, timeout)
        except CancelledError:
            partial.unlink(missing_ok=True)
            raise
        except Exception as exc:  # noqa: BLE001 - retried, then reported with context
            last_error = exc
            partial.unlink(missing_ok=True)
            emit(f"Download failed: {exc}")
        else:
            os.replace(partial, destination)
            emit(f"Downloaded {destination.name}.")
            return

    raise RuntimeError(f"could not download {url}: {last_error}")


def _drain_lines(lines: queue.Queue[str | None], emit: Callable[[str], None]) -> bool:
    """Emit everything available; return False once the reader signalled EOF."""
    while True:
        try:
            line = lines.get_nowait()
        except queue.Empty:
            return True
        if line is None:
            return False
        if line:
            emit(line)


def _terminate(process: subprocess.Popen[str]) -> None:
    """Stop a process and, on Windows, the whole tree it started."""
    if process.poll() is not None:
        return
    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                capture_output=True,
                check=False,
            )
        else:
            process.terminate()
        process.wait(timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        process.kill()
        process.wait(timeout=5)


def run_streamed(
    command: Sequence[str | Path],
    emit: Callable[[str], None],
    cwd: Path | None = None,
    passthrough: bool = False,
    *,
    should_cancel: CancelCheck | None = None,
) -> None:
    """Run a command, forwarding each output line to ``emit``.

    With ``passthrough`` the command writes straight to the terminal this app
    was started from instead, so long tools such as MFA keep their full output
    (progress bars, warnings) there; only the command line goes to ``emit``.
    If there is no terminal to write to, the output is captured as usual.

    ``should_cancel`` is called while the command runs; it raises
    CancelledError to stop the command (and its child processes).

    Raises RuntimeError if the command exits with a non-zero status.
    """
    args = [str(part) for part in command]
    emit("$ " + " ".join(args))
    inherit = passthrough and sys.stdout is not None
    kwargs: dict[str, object] = {"cwd": str(cwd) if cwd else None}
    if inherit:
        process: subprocess.Popen[str] = subprocess.Popen(args, **kwargs)  # type: ignore[arg-type]
    else:
        process = subprocess.Popen(  # type: ignore[call-overload]
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            **kwargs,
        )

    lines: queue.Queue[str | None] = queue.Queue()
    reader: threading.Thread | None = None
    if not inherit:
        assert process.stdout is not None

        def pump() -> None:
            try:
                for line in process.stdout:  # type: ignore[union-attr]
                    lines.put(line.rstrip())
            finally:
                lines.put(None)

        reader = threading.Thread(target=pump, daemon=True)
        reader.start()

    try:
        running = True
        while process.poll() is None:
            if should_cancel is not None:
                should_cancel()
            if running:
                running = _drain_lines(lines, emit)
            time.sleep(0.1)
        if running:
            # The process is gone but its last lines may still be in flight.
            deadline = time.monotonic() + 2.0
            while running and time.monotonic() < deadline:
                running = _drain_lines(lines, emit)
                if running:
                    time.sleep(0.05)
        code = process.returncode
    except BaseException:
        _terminate(process)
        raise
    finally:
        if process.stdout is not None:
            if reader is not None:
                reader.join(timeout=2.0)
            process.stdout.close()

    if code != 0:
        raise RuntimeError(f"command exited with status {code}")
