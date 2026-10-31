"""Checks HTK label files for likely auto-labelling errors."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .htk import TICKS_PER_SECOND, HtkLabel, read_htk

DEFAULT_MINOR_MS = 22.0
DEFAULT_MAJOR_MS = 10.0


@dataclass(frozen=True)
class Issue:
    file: str
    index: int
    time: float
    label: str
    severity: str
    message: str


def check_labels(
    labels: list[HtkLabel],
    file_name: str,
    minor_ms: float = DEFAULT_MINOR_MS,
    major_ms: float = DEFAULT_MAJOR_MS,
) -> list[Issue]:
    issues: list[Issue] = []
    previous_end: int | None = None
    for index, lab in enumerate(labels):
        time = lab.start / TICKS_PER_SECOND
        duration_ms = (lab.end - lab.start) / TICKS_PER_SECOND * 1000
        problem: tuple[str, str] | None = None
        if lab.end <= lab.start:
            problem = ("major", "zero or negative length")
        elif previous_end is not None and lab.start < previous_end:
            problem = ("major", "overlaps the previous label")
        elif duration_ms < major_ms:
            problem = ("major", f"very short ({duration_ms:.1f} ms, under {major_ms:g} ms)")
        elif duration_ms < minor_ms:
            problem = ("minor", f"short ({duration_ms:.1f} ms, under {minor_ms:g} ms)")
        if problem is not None:
            severity, message = problem
            issues.append(Issue(file_name, index, time, lab.label, severity, message))
        previous_end = lab.end
    return issues


def check_folder(
    folder: str | Path,
    emit: Callable[[str], None],
    minor_ms: float = DEFAULT_MINOR_MS,
    major_ms: float = DEFAULT_MAJOR_MS,
    *,
    should_cancel: Callable[[], None] | None = None,
    progress: Callable[[int, int, str | None], None] | None = None,
) -> list[Issue]:
    lab_files = sorted(p for p in Path(folder).iterdir() if p.suffix.lower() == ".lab")
    if not lab_files:
        raise ValueError("No .lab files found in that folder.")

    all_issues: list[Issue] = []
    for index, lab_file in enumerate(lab_files, 1):
        if should_cancel is not None:
            should_cancel()
        if progress is not None:
            progress(index - 1, len(lab_files), f"Checking {index}/{len(lab_files)}")
        issues = check_labels(read_htk(lab_file), lab_file.name, minor_ms, major_ms)
        for issue in issues:
            emit(
                f"[{issue.severity.upper()}] {issue.file} #{issue.index + 1} "
                f"at {issue.time:.3f}s ({issue.label}): {issue.message}"
            )
        all_issues.extend(issues)

    if progress is not None:
        progress(len(lab_files), len(lab_files), "Labels checked")
    majors = sum(1 for i in all_issues if i.severity == "major")
    emit(
        f"Checked {len(lab_files)} files: {majors} major, "
        f"{len(all_issues) - majors} minor issue(s)."
    )
    return all_issues
