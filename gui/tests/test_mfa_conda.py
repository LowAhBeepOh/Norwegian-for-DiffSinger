from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from gui.logic import mfa


class FindCondaTests(unittest.TestCase):
    def test_finds_conda_from_conda_exe_when_not_on_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            conda = Path(tmp) / "conda.exe"
            conda.write_bytes(b"")
            with (
                mock.patch.object(mfa.shutil, "which", return_value=None),
                mock.patch.dict(os.environ, {"CONDA_EXE": str(conda)}),
            ):
                self.assertEqual(mfa.find_conda(), str(conda))

    def test_returns_none_when_conda_is_nowhere(self) -> None:
        with (
            mock.patch.object(mfa.shutil, "which", return_value=None),
            mock.patch.object(mfa, "_conda_candidates", return_value=[]),
        ):
            self.assertIsNone(mfa.find_conda())


class AlignIsolationTests(unittest.TestCase):
    def test_each_run_gets_its_own_mfa_working_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            parent = root / "dataset"
            (parent / "wavs").mkdir(parents=True)
            (parent / "transcriptions").mkdir()
            (parent / "wavs" / "a.wav").write_bytes(b"")
            (parent / "transcriptions" / "a.txt").write_text("hei", encoding="utf-8")
            commands: list[list[str]] = []
            passthroughs: list[bool] = []

            def fake_run(command, emit, cwd=None, passthrough=False) -> None:
                args = [str(part) for part in command]
                commands.append(args)
                passthroughs.append(passthrough)
                work_dir = Path(args[args.index("--temporary_directory") + 1])
                # Fresh state per run, so --clean has nothing locked to delete.
                self.assertTrue(work_dir.is_dir())
                self.assertEqual(list(work_dir.iterdir()), [])

            with (
                mock.patch.object(mfa, "TOOLS_DIR", root / "tools"),
                mock.patch.object(mfa, "is_ready", return_value=True),
                mock.patch.object(mfa, "find_conda", return_value="conda"),
                mock.patch.object(mfa, "run_streamed", fake_run),
            ):
                mfa.align_folder(parent, lambda _: None)
                mfa.align_folder(parent, lambda _: None)

            self.assertEqual(len(commands), 2)
            work_dirs = [
                args[args.index("--temporary_directory") + 1] for args in commands
            ]
            self.assertNotEqual(work_dirs[0], work_dirs[1])
            self.assertIn("--clean", commands[0])
            # MFA writes to the terminal the app was started from, not the GUI log.
            self.assertEqual(passthroughs, [True, True])
            # The run's staging and state directories are removed afterwards.
            self.assertEqual(list((root / "tools" / "mfa_runs").iterdir()), [])


if __name__ == "__main__":
    unittest.main()
