"""Montreal Forced Aligner (MFA) setup and alignment with the NoFA Norwegian model.

MFA runs in its own conda environment (MFA depends on Kaldi, which is not
available through pip). NoFA is distributed by Språkbanken at the National
Library of Norway under CC0.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from collections.abc import Callable
from pathlib import Path

from ..paths import TOOLS_DIR
from .process import download_file, run_streamed

MFA_ENV_NAME = "nofa-mfa"
NOFA_URL = "https://www.nb.no/sbfil/verktoy/nofa/NoFA-1_0.tar.gz"
NOFA_DIR = TOOLS_DIR / "nofa"
ACOUSTIC_MODEL = NOFA_DIR / "NoFA_acoustic.zip"
DICTIONARY = NOFA_DIR / "NoFA-lex.dict"
TEXTGRID_FOLDER = "textgrids"


MINICONDA_URL = "https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe"
CONDA_TIMEOUT_SECONDS = 30
ENV_CACHE_SECONDS = 30.0
_env_cache: dict[str, tuple[float, frozenset[str]]] = {}


def _conda_candidates() -> list[Path]:
    """Places Miniconda, Miniforge or Anaconda may be installed without being on PATH."""
    home = Path.home()
    roots = [
        home / "miniconda3",
        home / "miniforge3",
        home / "anaconda3",
        Path(os.environ.get("LOCALAPPDATA", "")) / "miniconda3",
        Path(os.environ.get("LOCALAPPDATA", "")) / "miniforge3",
        Path(os.environ.get("PROGRAMDATA", "")) / "miniconda3",
        Path(os.environ.get("PROGRAMDATA", "")) / "miniforge3",
        Path(os.environ.get("PROGRAMDATA", "")) / "anaconda3",
    ]
    exe = "conda.exe" if os.name == "nt" else "conda"
    candidates = [root / "condabin" / exe for root in roots] + [root / "Scripts" / exe for root in roots]
    conda_exe = os.environ.get("CONDA_EXE")
    if conda_exe:
        candidates.insert(0, Path(conda_exe))
    return candidates


def find_conda() -> str | None:
    found = shutil.which("conda")
    if found:
        return found
    for candidate in _conda_candidates():
        if candidate.is_file():
            return str(candidate)
    return None


def install_miniconda(emit: Callable[[str], None], should_cancel=None) -> None:
    """Download the Miniconda installer and install it for the current user only."""
    if find_conda() is not None:
        emit("conda is already installed.")
        return
    installer = TOOLS_DIR / "Miniconda3-latest-Windows-x86_64.exe"
    target = Path.home() / "miniconda3"
    TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    try:
        emit(f"Downloading Miniconda from {MINICONDA_URL}")
        download_file(MINICONDA_URL, installer, emit, should_cancel=should_cancel)
        emit(f"Installing Miniconda into {target} (this can take a few minutes)...")
        run_streamed(
            [installer, "/InstallationType=JustMe", "/RegisterPython=0", "/S", f"/D={target}"],
            emit,
            should_cancel=should_cancel,
        )
    finally:
        installer.unlink(missing_ok=True)
    clear_env_cache()
    if find_conda() is None:
        raise RuntimeError("Miniconda installed, but conda was still not found.")
    emit("Miniconda installed.")


def _conda_env_names(conda: str, refresh: bool = False) -> frozenset[str]:
    now = time.monotonic()
    cached = _env_cache.get(conda)
    if cached is not None and not refresh and now - cached[0] < ENV_CACHE_SECONDS:
        return cached[1]
    result = subprocess.run(
        [conda, "env", "list", "--json"],
        capture_output=True,
        text=True,
        check=True,
        timeout=CONDA_TIMEOUT_SECONDS,
    )
    paths = json.loads(result.stdout).get("envs", [])
    names = frozenset(Path(p).name for p in paths)
    _env_cache[conda] = (now, names)
    return names


def clear_env_cache() -> None:
    """Forget cached conda environments, e.g. after installing one."""
    _env_cache.clear()


def is_mfa_installed(refresh: bool = False) -> bool:
    conda = find_conda()
    if conda is None:
        return False
    try:
        return MFA_ENV_NAME in _conda_env_names(conda, refresh=refresh)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError):
        return False


def is_nofa_installed() -> bool:
    return ACOUSTIC_MODEL.is_file() and DICTIONARY.is_file()


def is_ready() -> bool:
    return is_mfa_installed() and is_nofa_installed()


def _require_conda() -> str:
    conda = find_conda()
    if conda is None:
        raise RuntimeError(
            "conda was not found. Install Miniforge or Miniconda, reopen this app, and try again."
        )
    return conda


def install_mfa(emit: Callable[[str], None], should_cancel=None) -> None:
    conda = _require_conda()
    if MFA_ENV_NAME in _conda_env_names(conda, refresh=True):
        emit(f"Conda environment '{MFA_ENV_NAME}' already exists.")
        return
    emit("Creating conda environment with Montreal Forced Aligner (this can take a while)...")
    run_streamed(
        [conda, "create", "-y", "-n", MFA_ENV_NAME, "-c", "conda-forge", "montreal-forced-aligner"],
        emit,
        should_cancel=should_cancel,
    )
    clear_env_cache()
    emit("MFA installed.")


def _safe_extract(archive: tarfile.TarFile, destination: Path) -> None:
    root = destination.resolve()
    for member in archive.getmembers():
        target = (destination / member.name).resolve()
        if root not in target.parents and target != root:
            raise RuntimeError(f"unsafe path in archive: {member.name}")
    archive.extractall(destination)


def install_nofa(emit: Callable[[str], None], should_cancel=None) -> None:
    if is_nofa_installed():
        emit("NoFA model and lexicon are already installed.")
        return
    NOFA_DIR.mkdir(parents=True, exist_ok=True)
    archive_path = TOOLS_DIR / "NoFA-1_0.tar.gz"
    extract_dir = TOOLS_DIR / "nofa_extract"
    shutil.rmtree(extract_dir, ignore_errors=True)
    try:
        emit(f"Downloading NoFA (about 25 MB) from {NOFA_URL}")
        download_file(NOFA_URL, archive_path, emit, should_cancel=should_cancel)
        if should_cancel is not None:
            should_cancel()
        emit("Extracting NoFA...")
        extract_dir.mkdir(parents=True)
        with tarfile.open(archive_path, "r:gz") as archive:
            _safe_extract(archive, extract_dir)

        zips = sorted(extract_dir.rglob("*.zip"))
        dicts = sorted(extract_dir.rglob("NoFA-lex.dict"))
        if not zips or not dicts:
            raise RuntimeError("NoFA archive does not contain the expected model and lexicon.")
        shutil.copyfile(zips[0], ACOUSTIC_MODEL)
        shutil.copyfile(dicts[0], DICTIONARY)
        emit("NoFA installed.")
    finally:
        archive_path.unlink(missing_ok=True)
        shutil.rmtree(extract_dir, ignore_errors=True)


def align_folder(parent: str | Path, emit: Callable[[str], None], should_cancel=None) -> int:
    """Align ``parent/wavs`` and ``parent/transcriptions``; TextGrids go to ``parent/textgrids``."""
    parent = Path(parent)
    wavs_dir = parent / "wavs"
    text_dir = parent / "transcriptions"
    if not wavs_dir.is_dir() or not text_dir.is_dir():
        raise ValueError("The folder must contain 'wavs' and 'transcriptions' subfolders.")
    if not is_ready():
        raise RuntimeError("Norwegian MFA is not installed. Click 'Install Norwegian MFA' first.")

    pairs = []
    for wav in sorted(wavs_dir.iterdir()):
        if wav.suffix.lower() != ".wav":
            continue
        text = text_dir / f"{wav.stem}.txt"
        if text.is_file():
            pairs.append((wav, text))
        else:
            emit(f"Skipping {wav.name}: no matching .txt in 'transcriptions'.")
    if not pairs:
        raise ValueError("No wav/txt pairs with matching names were found.")

    conda = _require_conda()
    runs_dir = TOOLS_DIR / "mfa_runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    run_dir = Path(tempfile.mkdtemp(prefix="align_", dir=runs_dir))
    corpus_stage = run_dir / "corpus"
    corpus_stage.mkdir()
    work_dir = run_dir / "work"
    work_dir.mkdir()
    output = parent / TEXTGRID_FOLDER
    output.mkdir(exist_ok=True)
    try:
        for wav, text in pairs:
            shutil.copyfile(wav, corpus_stage / wav.name)
            shutil.copyfile(text, corpus_stage / text.name)
        emit(f"Aligning {len(pairs)} file(s)...")
        if sys.stdout is not None:
            emit(
                "MFA's output is printed in the terminal window this app was started "
                "from, not in this log."
            )
        kwargs = {"passthrough": True}
        if should_cancel is not None:
            kwargs["should_cancel"] = should_cancel
        run_streamed(
            [
                conda, "run", "-n", MFA_ENV_NAME, "--no-capture-output",
                "mfa", "align", corpus_stage, DICTIONARY, ACOUSTIC_MODEL, output,
                "--clean", "--temporary_directory", work_dir,
            ],
            emit,
            **kwargs,
        )
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)
    emit(f"Done. TextGrids are in {output}.")
    return len(pairs)
