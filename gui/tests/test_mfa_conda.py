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


if __name__ == "__main__":
    unittest.main()
