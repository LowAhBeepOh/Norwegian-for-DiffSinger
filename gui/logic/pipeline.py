"""Runs the dataset preparation steps in order, as the Pipeline tab does.

The layout is the one the Auto Label tab already expects::

    dataset/
    ├── wavs/              # .wav files
    ├── transcriptions/    # .txt files (written by the transcribe step)
    └── labs/              # .TextGrid from MFA, then .lab files

Every step can be turned off, so the pipeline also works on a folder where
part of the work is already done.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from . import htk, label_check, mfa, phonemes, transcribe

STEP_ORDER = ("transcribe", "align", "convert", "fix_phones", "check")
STEP_LABELS = {
    "transcribe": "Transcribe audio",
    "align": "Auto-label with MFA",
    "convert": "Convert TextGrid to HTK",
    "fix_phones": "Fix phonemes (and breathing)",
    "check": "Check labels",
}


@dataclass(frozen=True)
class Options:
    """Which steps to run and how."""

    transcribe: bool = True
    align: bool = True
    convert: bool = True
    fix_phones: bool = True
    check: bool = True
    breathing: bool = True
    repo: str = "NbAiLab/nb-whisper-small"
    force_cpu: bool = False


def enabled_steps(options: Options) -> list[str]:
    return [step for step in STEP_ORDER if getattr(options, step)]


def run(
    parent: str | Path,
    options: Options,
    emit: Callable[[str], None],
    *,
    should_cancel: Callable[[], None] | None = None,
    progress: Callable[[float, float, str | None], None] | None = None,
) -> int:
    """Run the selected steps on ``parent``; return how many steps ran."""
    parent = Path(parent)
    parent.mkdir(parents=True, exist_ok=True)
    steps = enabled_steps(options)
    if not steps:
        raise ValueError("Select at least one step to run.")

    wavs = parent / "wavs"
    transcriptions = parent / "transcriptions"
    textgrids = parent / mfa.TEXTGRID_FOLDER
    labs = parent / htk.LABS_FOLDER

    if "transcribe" in steps and not wavs.is_dir():
        raise ValueError(f"There is no 'wavs' folder in {parent}.")
    if "align" in steps:
        if not wavs.is_dir() or not transcriptions.is_dir():
            raise ValueError(
                "Auto-label needs both a 'wavs' and a 'transcriptions' folder "
                f"inside {parent}."
            )
        if not mfa.is_ready():
            raise RuntimeError(
                "Norwegian MFA is not installed. Use 'Install Norwegian MFA' on "
                "the Auto Label tab, or run without the auto-label step."
            )
    if "convert" in steps and "align" not in steps and not textgrids.is_dir():
        raise ValueError(
            f"There is no '{mfa.TEXTGRID_FOLDER}' folder in {parent}. "
            "Run auto-label first, or choose another folder."
        )
    if "convert" not in steps and {"fix_phones", "check"} & set(steps) and not labs.is_dir():
        raise ValueError(f"There is no 'labs' folder in {parent}.")

    total = len(steps)

    def sub(index: int):
        if progress is None:
            return None

        def report(done: float, count: float, text: str | None = None) -> None:
            fraction = 0.0 if count <= 0 else min(done / count, 1.0)
            progress(index + fraction, total, text)

        return report

    for index, step in enumerate(steps):
        if should_cancel is not None:
            should_cancel()
        emit(f"== {STEP_LABELS[step]} ==")
        if progress is not None:
            progress(index, total, STEP_LABELS[step])

        if step == "transcribe":
            transcriptions.mkdir(parents=True, exist_ok=True)
            transcribe.transcribe_folder(
                wavs,
                options.repo,
                emit,
                force_cpu=options.force_cpu,
                output_dir=transcriptions,
                should_cancel=should_cancel,
                progress=sub(index),
            )
        elif step == "align":
            mfa.align_folder(parent, emit, should_cancel=should_cancel)
        elif step == "convert":
            try:
                htk.convert_folder(
                    textgrids,
                    emit,
                    should_cancel=should_cancel,
                    progress=sub(index),
                )
            except ValueError as exc:
                raise ValueError(f"{exc} Run auto-label first, or choose another folder.") from exc
        elif step == "fix_phones":
            phonemes.fix_folder(
                labs,
                phonemes.load_simplified_phonemes(),
                emit,
                breathing=options.breathing,
                should_cancel=should_cancel,
                progress=sub(index),
            )
        elif step == "check":
            label_check.check_folder(
                labs,
                emit,
                should_cancel=should_cancel,
                progress=sub(index),
            )

    if progress is not None:
        progress(total, total, "Pipeline finished")
    emit(f"Pipeline finished ({total} step(s)).")
    return total
