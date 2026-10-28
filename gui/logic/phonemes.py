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
    folder: str | Path, phonemes: frozenset[str], emit: Callable[[str], None]
) -> Counter[str]:
    """Rewrite every .lab file in ``folder`` to simplified NoFAbet.

    Returns a count of labels that could not be mapped, keyed by label.
    """
    lab_files = sorted(p for p in Path(folder).iterdir() if p.suffix.lower() == ".lab")
    if not lab_files:
        raise ValueError("No .lab files found in that folder.")

    unknown: Counter[str] = Counter()
    files_changed = 0
    for lab_file in lab_files:
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

    emit(f"Checked {len(lab_files)} files; updated {files_changed}.")
    if unknown:
        emit("Phones that could not be mapped (left unchanged, please review):")
        for label, count in unknown.most_common():
            emit(f"  {label}: {count}")
    else:
        emit("All phones mapped to the simplified set.")
    return unknown
