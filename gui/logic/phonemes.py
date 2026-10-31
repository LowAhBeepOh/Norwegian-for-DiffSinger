"""Maps standard NoFAbet labels to the simplified NoFAbet set in phonemes.txt.

The standard set attaches stress digits to phones (e.g. ``AH2``, ``AX0``).
The simplified set uses the same names in lowercase without digits
(e.g. ``ah``, ``ax``). Labels that cannot be mapped are left untouched and
reported so the user can review them.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Callable
from pathlib import Path

from ..paths import PHONEMES_FILE
from . import sp_to_ap
from .htk import HtkLabel, read_htk, write_htk

SPECIAL_LABELS = frozenset({"SP", "AP"})
_STRESS_DIGITS = re.compile(r"\d+$")


def load_simplified_phonemes(path: str | Path = PHONEMES_FILE) -> frozenset[str]:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return frozenset(line.split("\t")[0].strip() for line in lines if line.strip())


def simplify(label: str, phonemes: frozenset[str]) -> str | None:
    """Return the simplified form of ``label``, or None if it cannot be mapped."""
    if label in SPECIAL_LABELS:
        return label
    base = _STRESS_DIGITS.sub("", label).lower()
    return base if base in phonemes else None


def fix_labels_folder(
    folder: str | Path,
    phonemes: frozenset[str],
    emit: Callable[[str], None],
    should_cancel: Callable[[], None] | None = None,
    progress: Callable[[int, int, str | None], None] | None = None,
) -> Counter[str]:
    """Rewrite every .lab file in ``folder`` to simplified NoFAbet.

    Returns a count of labels that could not be mapped, keyed by label.
    """
    lab_files = sorted(p for p in Path(folder).iterdir() if p.suffix.lower() == ".lab")
    if not lab_files:
        raise ValueError("No .lab files found in that folder.")

    unknown: Counter[str] = Counter()
    files_changed = 0
    for index, lab_file in enumerate(lab_files, 1):
        if should_cancel is not None:
            should_cancel()
        if progress is not None:
            progress(index - 1, len(lab_files), f"Simplifying phones: {index}/{len(lab_files)}")
        changed = False
        fixed = []
        for lab in read_htk(lab_file):
            new_label = simplify(lab.label, phonemes)
            if new_label is None:
                unknown[lab.label] += 1
                fixed.append(lab)
                continue
            if new_label != lab.label:
                changed = True
            fixed.append(HtkLabel(lab.start, lab.end, new_label))
        if changed:
            write_htk(lab_file, fixed)
            files_changed += 1

    if progress is not None:
        progress(len(lab_files), len(lab_files), "Phones simplified")
    emit(f"Checked {len(lab_files)} files; updated {files_changed}.")
    if unknown:
        emit("Phones that could not be mapped (left unchanged, please review):")
        for label, count in unknown.most_common():
            emit(f"  {label}: {count}")
    else:
        emit("All phones mapped to the simplified set.")
    return unknown


def fix_folder(
    folder: str | Path,
    phonemes: frozenset[str],
    emit: Callable[[str], None],
    *,
    breathing: bool = True,
    wav_dir: str | Path | None = None,
    should_cancel: Callable[[], None] | None = None,
    progress: Callable[[float, float, str | None], None] | None = None,
) -> Counter[str]:
    """Simplify phones, then turn SP into AP where a breath is audible.

    The order matters: breathing detection works on the simplified labels, so
    it runs after the stress digits are gone. ``breathing=False`` skips it.
    """
    def scaled(start: float, end: float):
        if progress is None:
            return None

        def report(done: float, total: float, text: str | None = None) -> None:
            fraction = 0.0 if total <= 0 else min(done / total, 1.0)
            progress(start + (end - start) * fraction, 1.0, text)

        return report

    unknown = fix_labels_folder(
        folder, phonemes, emit, should_cancel=should_cancel, progress=scaled(0.0, 0.6)
    )

    if not breathing:
        emit("Breathing detection skipped.")
        return unknown

    resolved_wav_dir = Path(wav_dir) if wav_dir is not None else sp_to_ap.find_wav_dir(folder)
    if resolved_wav_dir is None:
        emit(
            "Breathing detection skipped: no .wav files found next to the labs "
            "or in a 'wavs' folder."
        )
        return unknown

    sp_to_ap.apply(
        folder,
        resolved_wav_dir,
        emit,
        should_cancel=should_cancel,
        progress=scaled(0.6, 1.0),
    )
    return unknown
