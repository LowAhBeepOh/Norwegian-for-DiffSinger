from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from gui.logic import process


def _fake_urlretrieve(url, destination, reporthook):
    total = 100
    for block in range(0, 101):
        reporthook(block, 1, total)
    return destination, None


class DownloadProgressTests(unittest.TestCase):
    def test_emits_progress_bar_up_to_100_percent(self) -> None:
        lines: list[str] = []
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "file.bin"
            with mock.patch.object(process.urllib.request, "urlretrieve", _fake_urlretrieve):
                process.download_file("https://example.invalid/file.bin", target, lines.append)
        self.assertTrue(lines)
        self.assertTrue(lines[-1].startswith("[" + "#" * 20 + "]"))
        self.assertIn("100%", lines[-1])
        # Throttled: about one line per 5% rather than one per block.
        self.assertLessEqual(len(lines), 22)


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


if __name__ == "__main__":
    unittest.main()
