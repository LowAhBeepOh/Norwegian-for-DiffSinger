"""Turn silence labels (SP) into breath labels (AP) where a breath is audible.

MFA marks every pause as ``SP`` (silence), but a pause often contains an
audible breath, and DiffSinger uses ``AP`` for those. This module scans each
``SP`` segment in a ``.lab`` file, measures the matching audio, and rewrites
``SP`` to ``AP`` when enough noise-like, unvoiced energy is inside it.

Run it through the Fix Phonemes tab (after the phones have been simplified),
as part of the Pipeline tab, or from the command line:

    python -m gui.logic.sp_to_ap --labs labs --wavs wavs

Lab format: HTK style ``start end phone``, times in 100 ns units.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .process import CancelCheck

UNIT = 1e7

DEFAULT_MIN_DB = -52.0
DEFAULT_MIN_FLAT = 0.12
DEFAULT_MAX_PERIOD = 0.5
DEFAULT_MIN_BREATH = 0.06
DEFAULT_MIN_SIL = 0.03


@dataclass(frozen=True)
class BreathOptions:
    min_db: float = DEFAULT_MIN_DB
    min_flat: float = DEFAULT_MIN_FLAT
    max_period: float = DEFAULT_MAX_PERIOD
    min_breath: float = DEFAULT_MIN_BREATH
    min_sil: float = DEFAULT_MIN_SIL
    split: bool = False


# ----------------------------------------------------------------- io
def load_wav(path: str | Path) -> tuple[Any, int]:
    """Read a wav as mono float32; soundfile when available, scipy otherwise."""
    try:
        import soundfile as sf
    except ImportError:
        sf = None
    if sf is not None:
        x, sr = sf.read(str(path), dtype="float32", always_2d=False)
    else:
        import numpy as np
        from scipy.io import wavfile

        sr, x = wavfile.read(str(path))
        if x.dtype.kind == "i":
            x = x.astype(np.float32) / np.iinfo(x.dtype).max
        elif x.dtype.kind == "u":
            x = (x.astype(np.float32) - 128.0) / 128.0
        else:
            x = x.astype(np.float32)
    if x.ndim > 1:
        x = x.mean(axis=1)
    return x, int(sr)


def read_lab(path: str | Path) -> list[list[Any]]:
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) >= 3:
            rows.append([int(parts[0]), int(parts[1]), parts[2]])
    return rows


def write_lab(path: str | Path, rows: Sequence[Sequence[Any]]) -> None:
    text = "\n".join(f"{start} {end} {phone}" for start, end, phone in rows)
    Path(path).write_text(text + "\n", encoding="utf-8")


# ----------------------------------------------------------------- features
def frame_features(x: Any, sr: int, win_ms: float = 25.0, hop_ms: float = 10.0) -> Any:
    """Per frame: time, level (dBFS), spectral flatness, periodicity."""
    import numpy as np

    n = int(sr * win_ms / 1000)
    hop = int(sr * hop_ms / 1000)
    nfft = 1 << int(np.ceil(np.log2(n * 2)))
    window = np.hanning(n).astype(np.float32)
    window_power = np.mean(window**2)
    freqs = np.fft.rfftfreq(nfft, 1 / sr)
    band = (freqs > 300) & (freqs < min(10000, sr / 2 * 0.95))
    low_lag, high_lag = int(sr / 400), int(sr / 70)

    if len(x) < n:
        x = np.pad(x, (0, n - len(x)))
    frames = []
    for i in range(0, len(x) - n + 1, hop):
        segment = x[i : i + n] * window
        spectrum = np.abs(np.fft.rfft(segment, nfft)) ** 2 + 1e-14
        level = 10 * np.log10(np.mean(segment**2) / window_power + 1e-14)
        flatness = np.exp(np.mean(np.log(spectrum[band]))) / np.mean(spectrum[band])
        autocorrelation = np.fft.irfft(spectrum)
        autocorrelation = autocorrelation / autocorrelation[0]
        periodicity = autocorrelation[low_lag:high_lag].max()
        frames.append((i / sr + n / sr / 2, level, flatness, periodicity))
    if not frames:
        return np.zeros((0, 4), dtype=np.float32)
    return np.array(frames, dtype=np.float32)


def breath_mask(feat: Any, min_db: float, min_flat: float, max_period: float) -> Any:
    """A frame is breath when audible, noise-like and not voiced."""
    level, flatness, periodicity = feat[:, 1], feat[:, 2], feat[:, 3]
    return (level > min_db) & (flatness > min_flat) & (periodicity < max_period)


def smooth(mask: Any, close: int = 3, open_: int = 2) -> Any:
    """Fill tiny holes (``close``) then drop tiny blips (``open_``), in frames."""
    import numpy as np

    smoothed = mask.copy()

    def runs(values: Any) -> list[tuple[int, int]]:
        diff = np.diff(np.r_[0, values.astype(int), 0])
        return list(zip(np.where(diff == 1)[0], np.where(diff == -1)[0]))

    for start, end in runs(~smoothed):
        if end - start <= close and start > 0 and end < len(smoothed):
            smoothed[start:end] = True
    for start, end in runs(smoothed):
        if end - start <= open_:
            smoothed[start:end] = False
    return smoothed


# ----------------------------------------------------------------- core
def process(
    lab_rows: Sequence[Sequence[Any]], feat: Any, options: BreathOptions
) -> tuple[list[list[Any]], list[tuple[float, float, str, float, str]]]:
    """Return (new rows, report) for one file."""
    import numpy as np

    if len(feat) < 2:
        return [list(row) for row in lab_rows], []
    hop = float(feat[1, 0] - feat[0, 0])
    mask = smooth(
        breath_mask(feat, options.min_db, options.min_flat, options.max_period)
    )
    times = feat[:, 0]

    new_rows: list[list[Any]] = []
    report: list[tuple[float, float, str, float, str]] = []
    for start, end, phone in lab_rows:
        if phone != "SP":
            new_rows.append([start, end, phone])
            continue
        begin, finish = start / UNIT, end / UNIT
        idx = np.where((times >= begin) & (times < finish))[0]
        if len(idx) == 0:
            new_rows.append([start, end, phone])
            report.append((begin, finish, "SP", 0.0, "too short"))
            continue

        inside = mask[idx]
        breath_seconds = float(inside.sum()) * hop
        loudness = float(feat[idx, 1].max())
        if breath_seconds < options.min_breath:
            new_rows.append([start, end, "SP"])
            report.append((begin, finish, "SP", breath_seconds, f"peak {loudness:.0f} dBFS"))
            continue

        if not options.split:
            new_rows.append([start, end, "AP"])
        else:
            # Trim to the first/last breath frame; the rest stays silence.
            first, last = idx[np.where(inside)[0][0]], idx[np.where(inside)[0][-1]]
            breath_start = max(start, int(round((times[first] - hop / 2) * UNIT)))
            breath_end = min(end, int(round((times[last] + hop / 2) * UNIT)))
            if breath_start - start < options.min_sil * UNIT:
                breath_start = start
            if end - breath_end < options.min_sil * UNIT:
                breath_end = end
            if breath_start > start:
                new_rows.append([start, breath_start, "SP"])
            new_rows.append([breath_start, breath_end, "AP"])
            if breath_end < end:
                new_rows.append([breath_end, end, "SP"])
        report.append((begin, finish, "AP", breath_seconds, f"peak {loudness:.0f} dBFS"))
    return new_rows, report


def find_wav_dir(lab_dir: str | Path) -> Path | None:
    """Locate the audio for a folder of .lab files.

    Looks next to the labels first, then for the ``wavs`` folder the Auto Label
    tab expects (a sibling of ``labs`` or inside it).
    """
    folder = Path(lab_dir)
    candidates = [folder, folder.parent / "wavs", folder / "wavs"]
    for candidate in candidates:
        if candidate.is_dir() and any(candidate.glob("*.wav")):
            return candidate
    return None


def apply(
    lab_dir: str | Path,
    wav_dir: str | Path,
    emit: Callable[[str], None],
    *,
    options: BreathOptions | None = None,
    write: bool = True,
    plot: bool = False,
    should_cancel: CancelCheck | None = None,
    progress: Callable[[int, int, str | None], None] | None = None,
) -> tuple[int, int]:
    """Rewrite SP -> AP in every .lab file in ``lab_dir``, in place.

    Returns ``(converted, kept)``: how many SP labels became AP, and how many
    stayed SP. Files without a matching wav are reported and left alone.
    """
    options = options or BreathOptions()
    folder = Path(lab_dir)
    wavs = Path(wav_dir)
    labs = sorted(folder.glob("*.lab"))
    if not labs:
        raise ValueError("No .lab files found in that folder.")

    converted = kept = missing = 0
    for index, lab in enumerate(labs, 1):
        if should_cancel is not None:
            should_cancel()
        if progress is not None:
            progress(index - 1, len(labs), f"Detecting breaths: {index}/{len(labs)}")
        wav = wavs / f"{lab.stem}.wav"
        rows = read_lab(lab)
        if not any(phone == "SP" for _, _, phone in rows):
            continue
        if not wav.is_file():
            missing += 1
            continue

        audio, sample_rate = load_wav(wav)
        features = frame_features(audio, sample_rate)
        new_rows, report = process(rows, features, options)
        for begin, finish, result, seconds, note in report:
            converted += result == "AP"
            kept += result == "SP"
            if result == "AP":
                emit(
                    f"{lab.stem}  {begin:6.2f}-{finish:6.2f}s  SP -> AP  "
                    f"(breath {seconds * 1000:4.0f} ms, {note})"
                )
        if write and new_rows != rows:
            write_lab(lab, new_rows)
        if plot:
            mask = smooth(
                breath_mask(features, options.min_db, options.min_flat, options.max_period)
            )
            plot_debug(audio, sample_rate, features, mask, new_rows, folder / f"{lab.stem}_debug.png")

    if progress is not None:
        progress(len(labs), len(labs), "Breath detection done")
    emit(f"SP -> AP: {converted} label(s) became AP, {kept} kept as SP.")
    if missing:
        emit(
            f"{missing} file(s) with SP labels had no matching .wav in {wavs} and were left unchanged."
        )
    return converted, kept


def plot_debug(x: Any, sr: int, feat: Any, mask: Any, rows: Any, out_png: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    from scipy.signal import stft

    frequencies, times, spectrum = stft(x, sr, nperseg=1024, noverlap=896)
    fig, axes = plt.subplots(2, 1, figsize=(14, 6), sharex=True)
    axes[0].pcolormesh(
        times,
        frequencies / 1000,
        20 * np.log10(np.abs(spectrum) + 1e-9),
        vmin=-110,
        vmax=-30,
        shading="auto",
    )
    axes[0].set_ylim(0, 12)
    for start, end, phone in rows:
        colour = "red" if phone == "SP" else "lime" if phone == "AP" else "white"
        axes[0].axvline(start / UNIT, color=colour, lw=0.6)
        if phone in ("SP", "AP"):
            axes[0].text(start / UNIT, 11, phone, color=colour, fontsize=8)
    axes[1].plot(feat[:, 0], feat[:, 1], label="dBFS")
    axes[1].fill_between(feat[:, 0], -100, 0, where=mask, color="lime", alpha=0.25, label="breath frames")
    axes[1].set_ylim(-100, 0)
    axes[1].legend(loc="upper right")
    plt.tight_layout()
    plt.savefig(out_png, dpi=80)
    plt.close(fig)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Turn SP labels into AP where a breath is audible.")
    parser.add_argument("--labs", default="labs", help="folder with .lab files")
    parser.add_argument("--wavs", default=None, help="folder with .wav files (default: auto-detect)")
    parser.add_argument("--out", default=None, help="write new .lab files here instead of in place")
    parser.add_argument("--min-db", type=float, default=DEFAULT_MIN_DB, help="frame level must be above this dBFS")
    parser.add_argument("--min-flat", type=float, default=DEFAULT_MIN_FLAT, help="min spectral flatness (noisiness)")
    parser.add_argument("--max-period", type=float, default=DEFAULT_MAX_PERIOD, help="max periodicity (voiced = high)")
    parser.add_argument("--min-breath", type=float, default=DEFAULT_MIN_BREATH, help="seconds of breath needed inside an SP")
    parser.add_argument("--split", action="store_true", help="only the breath part becomes AP")
    parser.add_argument("--min-sil", type=float, default=DEFAULT_MIN_SIL, help="with --split, shortest leftover SP kept (s)")
    parser.add_argument("--dry-run", action="store_true", help="report only, write nothing")
    parser.add_argument("--plot", action="store_true", help="save debug pngs next to the output labs")
    args = parser.parse_args(argv)

    lab_dir = Path(args.labs)
    wav_dir = Path(args.wavs) if args.wavs else find_wav_dir(lab_dir)
    if wav_dir is None:
        print("No .wav files found; use --wavs to point at them.", file=sys.stderr)
        return 1

    options = BreathOptions(
        min_db=args.min_db,
        min_flat=args.min_flat,
        max_period=args.max_period,
        min_breath=args.min_breath,
        min_sil=args.min_sil,
        split=args.split,
    )
    if args.out:
        output = Path(args.out)
        output.mkdir(parents=True, exist_ok=True)
    else:
        output = lab_dir
    if not args.dry_run and output != lab_dir:
        for lab in sorted(lab_dir.glob("*.lab")):
            (output / lab.name).write_bytes(lab.read_bytes())

    apply(
        output,
        wav_dir,
        print,
        options=options,
        write=not args.dry_run,
        plot=args.plot,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
