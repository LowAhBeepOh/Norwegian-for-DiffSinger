from __future__ import annotations

import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

from gui.logic import process


class FakeResponse:
    """Minimal stand-in for the object urlopen() returns."""

    def __init__(self, payload: bytes) -> None:
        self._payload = payload
        self._offset = 0
        self.headers = {"Content-Length": str(len(payload))}

    def read(self, size: int = -1) -> bytes:
        end = self._offset + size if size > 0 else None
        chunk = self._payload[self._offset:end]
        self._offset += len(chunk)
        return chunk

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *_exc: object) -> bool:
        return False


class DownloadProgressTests(unittest.TestCase):
    def test_emits_progress_and_writes_the_file_atomically(self) -> None:
        lines: list[str] = []
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "file.bin"
            with mock.patch.object(
                process.urllib.request, "urlopen", lambda *_a, **_k: FakeResponse(b"x" * 100)
            ):
                process.download_file("https://example.invalid/file.bin", target, lines.append)

            self.assertTrue(target.is_file())
            self.assertFalse(target.with_name("file.bin.part").exists())

        self.assertTrue(
            any(line.startswith("[" + "#" * 20 + "]") and "100%" in line for line in lines),
            lines,
        )
        # Throttled: about one line per 5% rather than one per chunk.
        self.assertLessEqual(sum(1 for line in lines if line.startswith("[")), 22)

    def test_retries_a_failed_download(self) -> None:
        lines: list[str] = []
        calls = {"count": 0}

        def flaky(*_args, **_kwargs):
            calls["count"] += 1
            if calls["count"] == 1:
                raise urllib.error.URLError("connection dropped")
            return FakeResponse(b"ok")

        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "file.bin"
            with (
                mock.patch.object(process.urllib.request, "urlopen", flaky),
                mock.patch.object(process.time, "sleep"),
            ):
                process.download_file("https://example.invalid/file.bin", target, lines.append)

            self.assertEqual(calls["count"], 2)
            self.assertEqual(target.read_bytes(), b"ok")

        self.assertTrue(any("Retrying download" in line for line in lines))

    def test_failure_leaves_no_destination_file(self) -> None:
        def broken(*_args, **_kwargs):
            raise urllib.error.URLError("no network")

        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "file.bin"
            with (
                mock.patch.object(process.urllib.request, "urlopen", broken),
                mock.patch.object(process.time, "sleep"),
                self.assertRaises(RuntimeError),
            ):
                process.download_file(
                    "https://example.invalid/file.bin", target, lambda _: None, retries=1
                )

            self.assertFalse(target.exists())
            self.assertFalse(target.with_name("file.bin.part").exists())


class RunStreamedTests(unittest.TestCase):
    def test_passthrough_sends_output_to_terminal_instead_of_log(self) -> None:
        lines: list[str] = []
        process.run_streamed(
            [sys.executable, "-c", "print('hello')"], lines.append, passthrough=True
        )
        # The child's output went straight to stdout; only the command is logged.
        self.assertEqual(lines, ["$ " + sys.executable + " -c print('hello')"])

    def test_passthrough_still_reports_failure(self) -> None:
        with self.assertRaises(RuntimeError):
            process.run_streamed(
                [sys.executable, "-c", "raise SystemExit(3)"],
                lambda _: None,
                passthrough=True,
            )

    def test_captured_output_still_reaches_the_log(self) -> None:
        lines: list[str] = []
        process.run_streamed([sys.executable, "-c", "print('hei')"], lines.append)
        self.assertIn("hei", lines)

    def test_cancel_stops_the_running_command(self) -> None:
        def cancel() -> None:
            raise process.CancelledError()

        with self.assertRaises(process.CancelledError):
            process.run_streamed(
                [sys.executable, "-c", "import time; time.sleep(30)"],
                lambda _: None,
                should_cancel=cancel,
            )


if __name__ == "__main__":
    unittest.main()
