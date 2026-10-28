"""Montreal Forced Aligner (MFA) setup and alignment with the NoFA Norwegian model.

MFA runs in its own conda environment (MFA depends on Kaldi, which is not
available through pip). NoFA is distributed by Språkbanken at the National
Library of Norway under CC0.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tarfile
import urllib.request
from collections.abc import Callable
from pathlib import Path

from ..paths import TOOLS_DIR
from .process import run_streamed

MFA_ENV_NAME = "nofa-mfa"
NOFA_URL = "https://www.nb.no/sbfil/verktoy/nofa/NoFA-1_0.tar.gz"
NOFA_DIR = TOOLS_DIR / "nofa"
ACOUSTIC_MODEL = NOFA_DIR / "NoFA_acoustic.zip"
DICTIONARY = NOFA_DIR / "NoFA-lex.dict"
CORPUS_STAGE = TOOLS_DIR / "mfa_corpus"
LABELS_FOLDER = "labels"


def find_conda() -> str | None:
    return shutil.which("conda")


def _conda_env_names(conda: str) -> set[str]:
    result = subprocess.run(
        [conda, "env", "list", "--json"], capture_output=True, text=True, check=True
    )
    paths = json.loads(result.stdout).get("envs", [])
    return {Path(p).name for p in paths}


def is_mfa_installed() -> bool:
    conda = find_conda()
    if conda is None:
        return False
    try:
        return MFA_ENV_NAME in _conda_env_names(conda)
    except (OSError, ValueError, RuntimeError):
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


def install_mfa(emit: Callable[[str], None]) -> None:
    conda = _require_conda()
    if MFA_ENV_NAME in _conda_env_names(conda):
        emit(f"Conda environment '{MFA_ENV_NAME}' already exists.")
        return
    emit("Creating conda environment with Montreal Forced Aligner (this can take a while)...")
    run_streamed(
        [conda, "create", "-y", "-n", MFA_ENV_NAME, "-c", "conda-forge", "montreal-forced-aligner"],
        emit,
    )
    emit("MFA installed.")


def _safe_extract(archive: tarfile.TarFile, destination: Path) -> None:
    root = destination.resolve()
    for member in archive.getmembers():
        target = (destination / member.name).resolve()
        if root not in target.parents and target != root:
            raise RuntimeError(f"unsafe path in archive: {member.name}")
    archive.extractall(destination)


def install_nofa(emit: Callable[[str], None]) -> None:
    if is_nofa_installed():
        emit("NoFA model and lexicon are already installed.")
        return
    NOFA_DIR.mkdir(parents=True, exist_ok=True)
    archive_path = TOOLS_DIR / "NoFA-1_0.tar.gz"
    extract_dir = TOOLS_DIR / "nofa_extract"
    shutil.rmtree(extract_dir, ignore_errors=True)
    try:
        emit(f"Downloading NoFA (about 25 MB) from {NOFA_URL}")
        urllib.request.urlretrieve(NOFA_URL, archive_path)
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


def align_folder(parent: str | Path, emit: Callable[[str], None]) -> int:
    """Align ``parent/wavs`` and ``parent/transcriptions``; TextGrids go to ``parent/labels``."""
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
    shutil.rmtree(CORPUS_STAGE, ignore_errors=True)
    CORPUS_STAGE.mkdir(parents=True)
    output = parent / LABELS_FOLDER
    output.mkdir(exist_ok=True)
    try:
        for wav, text in pairs:
            shutil.copyfile(wav, CORPUS_STAGE / wav.name)
            shutil.copyfile(text, CORPUS_STAGE / text.name)
        emit(f"Aligning {len(pairs)} file(s)...")
        run_streamed(
            [
                conda, "run", "-n", MFA_ENV_NAME, "--no-capture-output",
                "mfa", "align", CORPUS_STAGE, DICTIONARY, ACOUSTIC_MODEL, output, "--clean",
            ],
            emit,
        )
    finally:
        shutil.rmtree(CORPUS_STAGE, ignore_errors=True)
    emit(f"Done. TextGrids are in {output}.")
    return len(pairs)
