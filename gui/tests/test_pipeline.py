"""Tests for the one-click pipeline."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from gui.logic import pipeline
from gui.logic.htk import read_htk
from gui.logic.process import CancelledError

TEXTGRID = '''File type = "ooTextFile"
Object class = "TextGrid"

xmin = 0
xmax = 0.8
tiers? <exists>
size = 1
item []:
    item [1]:
        class = "IntervalTier"
        name = "phones"
        xmin = 0
        xmax = 0.8
        intervals: size = 2
        intervals [1]:
            xmin = 0
            xmax = 0.4
            text = "AH2"
        intervals [2]:
            xmin = 0.4
            xmax = 0.8
            text = ""
'''


class PipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.parent = Path(self._dir.name) / "dataset"
        self.textgrids = self.parent / "textgrids"
        self.textgrids.mkdir(parents=True)
        self.labs = self.parent / "labs"
        (self.textgrids / "a.TextGrid").write_text(TEXTGRID, encoding="utf-8")

    def tearDown(self) -> None:
        self._dir.cleanup()

    def test_convert_fix_and_check_run_in_order(self) -> None:
        lines: list[str] = []
        progress: list[float] = []
        steps = pipeline.run(
            self.parent,
            pipeline.Options(transcribe=False, align=False, breathing=False),
            lines.append,
            progress=lambda done, total, text=None: progress.append(done / total),
        )

        self.assertEqual(steps, 3)
        labels = [label.label for label in read_htk(self.labs / "a.lab")]
        self.assertEqual(labels, ["ah", "SP"])
        self.assertFalse(self.textgrids.exists())
        self.assertTrue(any("Breathing detection skipped" in line for line in lines))
        self.assertTrue(any("Checked 1 files" in line for line in lines))
        self.assertEqual(progress[-1], 1.0)

    def test_missing_folder_is_created(self) -> None:
        new_parent = Path(self._dir.name) / "new_dataset"
        with self.assertRaises(ValueError):
            pipeline.run(new_parent, pipeline.Options(transcribe=False, align=False), lambda _: None)
        self.assertTrue(new_parent.is_dir())

    def test_transcribe_needs_a_wavs_folder(self) -> None:
        with self.assertRaises(ValueError):
            pipeline.run(
                self.parent,
                pipeline.Options(transcribe=True, align=False, convert=False, fix_phones=False, check=False),
                lambda _: None,
            )

    def test_cancel_is_checked_between_steps(self) -> None:
        def cancel() -> None:
            raise CancelledError()

        with self.assertRaises(CancelledError):
            pipeline.run(
                self.parent,
                pipeline.Options(transcribe=False, align=False, fix_phones=False, check=False),
                lambda _: None,
                should_cancel=cancel,
            )
        self.assertFalse((self.labs / "a.lab").exists())


if __name__ == "__main__":
    unittest.main()
