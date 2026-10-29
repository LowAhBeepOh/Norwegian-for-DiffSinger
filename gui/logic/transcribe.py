"""Model installation and batch transcription with Whisper / NB-Whisper.

Models are stored under ``TOOLS_DIR/models``. Transcription uses the
Hugging Face ``transformers`` pipeline, so ``transformers`` and ``torch``
must be installed (see gui/requirements.txt).
"""

from __future__ import annotations

from collections.abc import Callable
from math import gcd
from pathlib import Path
from typing import Any

from ..paths import TOOLS_DIR

TARGET_SAMPLE_RATE = 16_000
CHUNK_SECONDS = 30

FAMILIES: dict[str, dict[str, str]] = {
    "Whisper": {
        "tiny": "openai/whisper-tiny",
        "base": "openai/whisper-base",
        "small": "openai/whisper-small",
        "medium": "openai/whisper-medium",
        "large-v3": "openai/whisper-large-v3",
    },
    "NB-Whisper": {
        "tiny": "NbAiLab/nb-whisper-tiny",
        "base": "NbAiLab/nb-whisper-base",
        "small": "NbAiLab/nb-whisper-small",
        "medium": "NbAiLab/nb-whisper-medium",
        "large": "NbAiLab/nb-whisper-large",
    },
}


# The model repos also ship ONNX, CTranslate2, GGML, Flax and TensorFlow copies
# of the weights, plus model cards and training leftovers. Only the files the
# transformers pipeline reads are downloaded; NB-Whisper Small drops from about
# 7.4 GB to under 1 GB that way.
DOWNLOAD_PATTERNS = (
    "config.json",
    "generation_config.json",
    "preprocessor_config.json",
    "normalizer.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "vocab.json",
    "merges.txt",
    "special_tokens_map.json",
    "added_tokens.json",
    "model.safetensors",
    "model-*.safetensors",
    "*.safetensors.index.json",
)


def repo_id(family: str, size: str) -> str:
    return FAMILIES[family][size]


def model_dir(repo: str) -> Path:
    return TOOLS_DIR / "models" / repo.replace("/", "__")


def is_installed(repo: str) -> bool:
    return (model_dir(repo) / "config.json").is_file()


def install_model(repo: str, emit: Callable[[str], None]) -> Path:
    """Download the files the transformers pipeline needs from the Hub."""
    from huggingface_hub import snapshot_download

    target = model_dir(repo)
    if is_installed(repo):
        emit(f"{repo} is already installed at {target}.")
        return target
    emit(f"Downloading {repo} (this can be several GB)...")
    snapshot_download(
        repo_id=repo, local_dir=str(target), allow_patterns=list(DOWNLOAD_PATTERNS)
    )
    emit(f"Installed {repo} at {target}.")
    return target


def _load_pipeline(model_path: Path, force_cpu: bool = False) -> Any:
    from transformers import pipeline

    device = -1
    if not force_cpu:
        import torch

        if torch.cuda.is_available():
            device = 0
    return pipeline("automatic-speech-recognition", model=str(model_path), device=device)


def _load_audio(path: Path) -> Any:
    import numpy as np
    import soundfile as sf
    from scipy.signal import resample_poly

    data, rate = sf.read(str(path), dtype="float32")
    if data.ndim > 1:
        data = data.mean(axis=1)
    if rate != TARGET_SAMPLE_RATE:
        divisor = gcd(TARGET_SAMPLE_RATE, rate)
        data = resample_poly(data, TARGET_SAMPLE_RATE // divisor, rate // divisor)
    return np.asarray(data, dtype=np.float32)


def transcribe_folder(
    folder: str | Path,
    repo: str,
    emit: Callable[[str], None],
    force_cpu: bool = False,
    pipeline_factory: Callable[..., Any] = _load_pipeline,
) -> int:
    """Transcribe every .wav in ``folder`` into a same-named .txt file."""
    folder = Path(folder)
    if not is_installed(repo):
        raise RuntimeError("The model is not installed yet. Click 'Install model' first.")
    wavs = sorted(p for p in folder.iterdir() if p.suffix.lower() == ".wav")
    if not wavs:
        raise ValueError("No .wav files found in that folder.")

    asr = pipeline_factory(model_dir(repo), force_cpu=force_cpu)
    for index, wav in enumerate(wavs, 1):
        emit(f"[{index}/{len(wavs)}] {wav.name}")
        audio = _load_audio(wav)
        output = asr(
            {"raw": audio, "sampling_rate": TARGET_SAMPLE_RATE},
            chunk_length_s=CHUNK_SECONDS,
            generate_kwargs={"language": "norwegian", "task": "transcribe"},
        )
        text = str(output["text"]).strip()
        wav.with_suffix(".txt").write_text(text + "\n", encoding="utf-8")
    emit(f"Done. Wrote {len(wavs)} transcription(s).")
    return len(wavs)
