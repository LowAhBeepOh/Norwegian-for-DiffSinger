"""Unit tests for the GUI's logic modules (no GUI window is opened)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from gui.logic.htk import TICKS_PER_SECOND, HtkLabel, read_htk, textgrid_to_labels, write_htk
from gui.logic.label_check import check_labels
from gui.logic.phonemes import simplify
from gui.logic.textgrid import read_textgrid

TEXTGRID = '''File type = "ooTextFile"
Object class = "TextGrid"

xmin = 0
xmax = 1
tiers? <exists>
size = 1
item []:
    item [1]:
        class = "IntervalTier"
        name = "phones"
        xmin = 0
        xmax = 1
        intervals: size = 3
        intervals [1]:
            xmin = 0
            xmax = 0.4
            text = "AH2"
        intervals [2]:
            xmin = 0.4
            xmax = 0.7
            text = "S""X"
        intervals [3]:
            xmin = 0.7
            xmax = 1
            text = ""
'''


class TextGridToHtkTests(unittest.TestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.path = Path(self._dir.name) / "sample.TextGrid"
        self.path.write_text(TEXTGRID, encoding="utf-8")

    def tearDown(self) -> None:
        self._dir.cleanup()

    def test_reads_tier_and_unescapes_quotes(self) -> None:
        tiers = read_textgrid(self.path)
        self.assertEqual(tiers[0].name, "phones")
        self.assertEqual([i.text for i in tiers[0].intervals], ["AH2", 'S"X', ""])

    def test_converts_to_htk_with_silence_for_empty_text(self) -> None:
        result = textgrid_to_labels(self.path, "phones")
        labels = [(lab.start, lab.end, lab.label) for lab in result.labels]
        self.assertEqual(
            labels,
            [
                (0, 4_000_000, "AH2"),
                (4_000_000, 7_000_000, 'S"X'),
                (7_000_000, 10_000_000, "SP"),
            ],
        )
        self.assertEqual(result.warnings, [])

    def test_missing_tier_raises(self) -> None:
        with self.assertRaises(ValueError):
            textgrid_to_labels(self.path, "words")

    def test_htk_round_trip(self) -> None:
        out = Path(self._dir.name) / "out.lab"
        labels = [HtkLabel(0, 5 * TICKS_PER_SECOND // 10, "ah")]
        write_htk(out, labels)
        self.assertEqual(read_htk(out), labels)


class PhonemeTests(unittest.TestCase):
    phonemes = frozenset({"ah", "s", "sp"})

    def test_strips_stress_digits(self) -> None:
        self.assertEqual(simplify("AH2", self.phonemes), "ah")

    def test_keeps_special_labels(self) -> None:
        self.assertEqual(simplify("SP", self.phonemes), "SP")

    def test_unknown_phone_returns_none(self) -> None:
        self.assertIsNone(simplify("ZZ1", self.phonemes))


class LabelCheckTests(unittest.TestCase):
    def test_flags_short_overlapping_and_zero_length(self) -> None:
        ms = TICKS_PER_SECOND // 1000
        labels = [
            HtkLabel(0, 100 * ms, "a"),
            HtkLabel(100 * ms, 105 * ms, "b"),
            HtkLabel(105 * ms, 115 * ms, "c"),
            HtkLabel(110 * ms, 150 * ms, "d"),
            HtkLabel(150 * ms, 150 * ms, "e"),
        ]
        issues = check_labels(labels, "x.lab")
        reasons = [(i.label, i.severity) for i in issues]
        self.assertEqual(
            reasons, [("b", "major"), ("c", "minor"), ("d", "major"), ("e", "major")]
        )

    def test_minor_when_between_thresholds(self) -> None:
        ms = TICKS_PER_SECOND // 1000
        labels = [HtkLabel(0, 15 * ms, "a")]
        issues = check_labels(labels, "x.lab")
        self.assertEqual([(i.label, i.severity) for i in issues], [("a", "minor")])


if __name__ == "__main__":
    unittest.main()
