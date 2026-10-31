"""TextGrid -> HTK label conversion and HTK label file I/O.

HTK times are integers in 100 ns units. Gaps between labels are filled with
the silence label ``SP``. Overlaps are clipped to the previous label's end, and
zero-length labels are dropped; both are reported as warnings.
"""

from __future__ import annotations

import shutil
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from .textgrid import read_textgrid

TICKS_PER_SECOND = 10_000_000
SILENCE = "SP"
LABS_FOLDER = "labs"


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
    """Convert the phones tier of a TextGrid into HTK labels."""
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


def convert_folder(
    folder: str | Path,
    emit: Callable[[str], None],
    *,
    should_cancel: Callable[[], None] | None = None,
    progress: Callable[[int, int, str | None], None] | None = None,
) -> int:
    """Convert every .TextGrid in ``folder`` to a .lab file in a ``labs`` sibling of ``folder``.

    Once all the .lab files are written, ``folder`` is deleted along with its contents.
    """
    source = Path(folder)
    files = sorted(p for p in source.iterdir() if p.suffix.lower() == ".textgrid")
    if not files:
        raise ValueError("No .TextGrid files found in that folder.")
    output = source.parent / LABS_FOLDER
    output.mkdir(exist_ok=True)
    for index, textgrid in enumerate(files, 1):
        if should_cancel is not None:
            should_cancel()
        if progress is not None:
            progress(index - 1, len(files), f"Converting {index}/{len(files)}: {textgrid.name}")
        result = textgrid_to_labels(textgrid)
        write_htk(output / textgrid.with_suffix(".lab").name, result.labels)
        emit(f"{textgrid.name}: {len(result.labels)} labels written")
        for warning in result.warnings:
            emit(f"  warning: {warning}")
    shutil.rmtree(source)
    if progress is not None:
        progress(len(files), len(files), "Conversion done")
    return len(files)
