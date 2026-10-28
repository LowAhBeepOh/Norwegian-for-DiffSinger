"""TextGrid -> HTK label conversion and HTK label file I/O.

HTK times are integers in 100 ns units. Gaps between labels are filled with
the silence label ``SP``. Overlaps are clipped to the previous label's end, and
zero-length labels are dropped; both are reported as warnings.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from .textgrid import read_textgrid

TICKS_PER_SECOND = 10_000_000
SILENCE = "SP"


@dataclass(frozen=True)
class HtkLabel:
    start: int
    end: int
    label: str


@dataclass
class ConversionResult:
    labels: list[HtkLabel] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def textgrid_to_labels(path: str | Path, tier_name: str = "phones") -> ConversionResult:
    """Convert one interval tier of a TextGrid into HTK labels."""
    wanted = tier_name.strip().lower()
    matches = [t for t in read_textgrid(path) if t.name.strip().lower() == wanted]
    if not matches:
        raise ValueError(f"no interval tier named {tier_name!r} in {Path(path).name}")

    result = ConversionResult()
    cursor = 0
    for interval in matches[0].intervals:
        start = round(interval.xmin * TICKS_PER_SECOND)
        end = round(interval.xmax * TICKS_PER_SECOND)
        label = interval.text.strip() or SILENCE
        if end <= start:
            result.warnings.append(
                f"zero-length label {label!r} at {interval.xmin:.3f}s dropped"
            )
            continue
        if start < cursor:
            result.warnings.append(
                f"label {label!r} at {interval.xmin:.3f}s overlaps the previous label; clipped"
            )
            start = cursor
            if start >= end:
                result.warnings.append(
                    f"label {label!r} at {interval.xmin:.3f}s lies entirely inside the previous label; dropped"
                )
                continue
        if start > cursor:
            result.labels.append(HtkLabel(cursor, start, SILENCE))
        result.labels.append(HtkLabel(start, end, label))
        cursor = end
    return result


def write_htk(path: str | Path, labels: list[HtkLabel]) -> None:
    text = "".join(f"{lab.start} {lab.end} {lab.label}\n" for lab in labels)
    Path(path).write_text(text, encoding="utf-8")


def read_htk(path: str | Path) -> list[HtkLabel]:
    labels: list[HtkLabel] = []
    for number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        parts = line.split()
        if not parts:
            continue
        if len(parts) != 3:
            raise ValueError(f"{Path(path).name}:{number}: expected 'start end label'")
        labels.append(HtkLabel(int(parts[0]), int(parts[1]), parts[2]))
    return labels


def convert_folder(folder: str | Path, tier_name: str, emit: Callable[[str], None]) -> int:
    """Convert every .TextGrid in ``folder`` to a .lab file next to it."""
    files = sorted(p for p in Path(folder).iterdir() if p.suffix.lower() == ".textgrid")
    if not files:
        raise ValueError("No .TextGrid files found in that folder.")
    for textgrid in files:
        result = textgrid_to_labels(textgrid, tier_name)
        write_htk(textgrid.with_suffix(".lab"), result.labels)
        emit(f"{textgrid.name}: {len(result.labels)} labels written")
        for warning in result.warnings:
            emit(f"  warning: {warning}")
    return len(files)
