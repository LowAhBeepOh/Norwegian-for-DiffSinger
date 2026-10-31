"""Tests for the SP -> AP breathing detection."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
import soundfile as sf

from gui.logic import sp_to_ap
from gui.logic.htk import TICKS_PER_SECOND, HtkLabel, read_htk, write_htk

SR = 16_000


class BreathDetectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        root = Path(self._dir.name)
        self.labs = root / "labs"
        self.wavs = root / "wavs"
        self.labs.mkdir()
        self.wavs.mkdir()

    def tearDown(self) -> None:
        self._dir.cleanup()

    def _write_case(self, name: str, audio: np.ndarray) -> None:
        sf.write(str(self.wavs / f"{name}.wav"), audio, SR)
        write_htk(
            self.labs / f"{name}.lab",
            [HtkLabel(0, int(1.0 * TICKS_PER_SECOND), "SP")],
        )

    def test_noise_in_pause_becomes_ap(self) -> None:
        rng = np.random.default_rng(1234)
        self._write_case("breath", rng.normal(0, 0.05, SR).astype(np.float32))
        lines: list[str] = []

        converted, kept = sp_to_ap.apply(self.labs, self.wavs, lines.append)

        self.assertEqual((converted, kept), (1, 0))
        self.assertEqual([lab.label for lab in read_htk(self.labs / "breath.lab")], ["AP"])
        self.assertTrue(any("SP -> AP" in line for line in lines))

    def test_true_silence_stays_sp(self) -> None:
        self._write_case("silence", np.zeros(SR, dtype=np.float32))

        converted, kept = sp_to_ap.apply(self.labs, self.wavs, lambda _: None)

        self.assertEqual((converted, kept), (0, 1))
        self.assertEqual([lab.label for lab in read_htk(self.labs / "silence.lab")], ["SP"])

    def test_fix_folder_simplifies_phones_then_detects_breath(self) -> None:
        from gui.logic import phonemes

        rng = np.random.default_rng(7)
        sf.write(str(self.wavs / "mix.wav"), rng.normal(0, 0.05, SR).astype(np.float32), SR)
        write_htk(
            self.labs / "mix.lab",
            [
                HtkLabel(0, int(0.5 * TICKS_PER_SECOND), "AH0"),
                HtkLabel(int(0.5 * TICKS_PER_SECOND), TICKS_PER_SECOND, "SP"),
            ],
        )
        lines: list[str] = []

        phonemes.fix_folder(
            self.labs,
            phonemes.load_simplified_phonemes(),
            lines.append,
            breathing=True,
        )

        self.assertEqual(
            [lab.label for lab in read_htk(self.labs / "mix.lab")], ["ah", "AP"]
        )
        self.assertTrue(any("SP -> AP" in line for line in lines))

    def test_fix_folder_can_skip_breathing(self) -> None:
        from gui.logic import phonemes

        rng = np.random.default_rng(8)
        sf.write(str(self.wavs / "skip.wav"), rng.normal(0, 0.05, SR).astype(np.float32), SR)
        write_htk(
            self.labs / "skip.lab",
            [HtkLabel(0, TICKS_PER_SECOND, "SP")],
        )
        lines: list[str] = []

        phonemes.fix_folder(
            self.labs,
            phonemes.load_simplified_phonemes(),
            lines.append,
            breathing=False,
        )

        self.assertEqual([lab.label for lab in read_htk(self.labs / "skip.lab")], ["SP"])
        self.assertTrue(any("Breathing detection skipped" in line for line in lines))

    def test_lab_without_wav_is_left_alone(self) -> None:
        write_htk(
            self.labs / "orphan.lab",
            [HtkLabel(0, TICKS_PER_SECOND, "SP")],
        )
        lines: list[str] = []

        converted, _ = sp_to_ap.apply(self.labs, self.wavs, lines.append)

        self.assertEqual(converted, 0)
        self.assertTrue(any("no matching .wav" in line for line in lines))
        self.assertEqual([lab.label for lab in read_htk(self.labs / "orphan.lab")], ["SP"])

    def test_find_wav_dir_prefers_labs_then_sibling_wavs(self) -> None:
        self.assertIsNone(sp_to_ap.find_wav_dir(self.labs))
        (self.wavs / "a.wav").write_bytes(b"")
        self.assertEqual(sp_to_ap.find_wav_dir(self.labs), self.wavs)
        sf.write(str(self.labs / "b.wav"), np.zeros(100, dtype=np.float32), SR)
        self.assertEqual(sp_to_ap.find_wav_dir(self.labs), self.labs)


if __name__ == "__main__":
    unittest.main()
