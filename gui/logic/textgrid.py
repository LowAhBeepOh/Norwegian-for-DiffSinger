"""Reader for Praat TextGrid files (long and short text formats).

Only interval tiers are returned; point tiers are skipped.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Interval:
    xmin: float
    xmax: float
    text: str


@dataclass(frozen=True)
class IntervalTier:
    name: str
    intervals: tuple[Interval, ...]


_LONG_ITEM_SPLIT = re.compile(r"^\s*item \[\d+\]:\s*$", re.MULTILINE)
_LONG_INTERVAL_SPLIT = re.compile(r"^\s*intervals \[\d+\]:\s*$", re.MULTILINE)
_LONG_ITEM_START = re.compile(r"^\s*item \[", re.MULTILINE)
_LONG_CLASS = re.compile(r'class = "([^"]*)"')
_LONG_NAME = re.compile(r'name = "((?:[^"]|"")*)"')
_LONG_XMIN = re.compile(r"xmin = ([-+0-9.eE]+)")
_LONG_XMAX = re.compile(r"xmax = ([-+0-9.eE]+)")
_LONG_TEXT = re.compile(r'text = "((?:[^"]|"")*)"')
_SHORT_TOKEN = re.compile(r'"((?:[^"]|"")*)"|\S+')


def _unquote(value: str) -> str:
    return value.replace('""', '"')


def read_textgrid(path: str | Path) -> list[IntervalTier]:
    """Return the interval tiers of a TextGrid file, in file order."""
    raw = Path(path).read_text(encoding="utf-8-sig")
    try:
        if _LONG_ITEM_START.search(raw):
            return _parse_long(raw)
        return _parse_short(raw)
    except (IndexError, ValueError, AttributeError) as exc:
        raise ValueError(f"malformed TextGrid file {Path(path).name}: {exc}") from exc


def _parse_long(raw: str) -> list[IntervalTier]:
    tiers: list[IntervalTier] = []
    for block in _LONG_ITEM_SPLIT.split(raw)[1:]:
        header, *interval_blocks = _LONG_INTERVAL_SPLIT.split(block)
        cls = _LONG_CLASS.search(header)
        if cls is None or cls.group(1) != "IntervalTier":
            continue
        name = _LONG_NAME.search(header)
        intervals = []
        for chunk in interval_blocks:
            xmin = _LONG_XMIN.search(chunk)
            xmax = _LONG_XMAX.search(chunk)
            text = _LONG_TEXT.search(chunk)
            if xmin is None or xmax is None or text is None:
                raise ValueError("interval is missing xmin, xmax or text")
            intervals.append(
                Interval(float(xmin.group(1)), float(xmax.group(1)), _unquote(text.group(1)))
            )
        tiers.append(IntervalTier(_unquote(name.group(1)) if name else "", tuple(intervals)))
    return tiers


def _parse_short(raw: str) -> list[IntervalTier]:
    tokens = [
        m.group(1).replace('""', '"') if m.group(1) is not None else m.group(0)
        for m in _SHORT_TOKEN.finditer(raw)
    ]
    if not tokens or tokens[0] != "ooTextFile":
        raise ValueError("not a TextGrid file")
    tier_count = int(tokens[5])
    index = 6
    tiers: list[IntervalTier] = []
    for _ in range(tier_count):
        tier_class, name = tokens[index], tokens[index + 1]
        count = int(tokens[index + 4])
        index += 5
        if tier_class == "IntervalTier":
            intervals = []
            for _ in range(count):
                intervals.append(
                    Interval(float(tokens[index]), float(tokens[index + 1]), tokens[index + 2])
                )
                index += 3
            tiers.append(IntervalTier(name, tuple(intervals)))
        else:
            index += 2 * count
    return tiers
