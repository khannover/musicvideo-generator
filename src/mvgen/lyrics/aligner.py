"""Lyric alignment — map raw lyric lines to audio timestamps.

The initial implementation uses a **proportional fallback** aligner that
distributes lyric lines evenly across the vocal duration (excluding detected
silence regions).  The interface is designed so a real aligner (e.g. one
backed by Whisper forced-alignment) can be swapped in later without changing
call sites.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from mvgen.audio.analyzer import AudioAnalysis

logger = logging.getLogger(__name__)


@dataclass
class AlignedWord:
    """A single word with start/end timestamps."""

    text: str
    start: float
    end: float


@dataclass
class AlignedLine:
    """A lyric line with start/end timestamps and optional word-level alignment."""

    text: str
    start: float
    end: float
    line_index: int
    words: Optional[list[AlignedWord]] = field(default=None)


def align_lyrics(
    audio_path: Path,
    lyrics_text: str,
    audio_analysis: Optional[AudioAnalysis] = None,
) -> list[AlignedLine]:
    """Align raw lyric lines to the audio timeline.

    Currently uses a **proportional fallback** strategy: lyric lines are
    distributed evenly across the *vocal duration* (the audio duration minus
    silence regions).

    Parameters
    ----------
    audio_path:
        Path to the master audio file (used to load audio analysis when
        *audio_analysis* is not provided).
    lyrics_text:
        Raw lyric text.  Section headers like ``[Verse 1]`` are stripped.
    audio_analysis:
        Pre-computed :class:`~mvgen.audio.analyzer.AudioAnalysis`.  When
        ``None``, a fresh analysis is run.

    Returns
    -------
    list[AlignedLine]
        One :class:`AlignedLine` per non-empty, non-header lyric line.
    """
    audio_path = Path(audio_path)

    if audio_analysis is None:
        from mvgen.audio.analyzer import analyze_audio

        audio_analysis = analyze_audio(audio_path)

    lines = _extract_lyric_lines(lyrics_text)
    if not lines:
        logger.warning("No lyric lines found after parsing")
        return []

    # Build the vocal timeline: full duration minus silence regions
    vocal_segments = _vocal_segments(audio_analysis)
    total_vocal_time = sum(end - start for start, end in vocal_segments)

    if total_vocal_time <= 0:
        # Fall back to full duration split evenly
        vocal_segments = [(0.0, audio_analysis.duration)]
        total_vocal_time = audio_analysis.duration

    logger.info(
        "Aligning %d lyric lines across %.2f s of vocal time",
        len(lines),
        total_vocal_time,
    )

    time_per_line = total_vocal_time / len(lines)
    aligned: list[AlignedLine] = []

    # Walk through the vocal timeline, assigning each line a slot
    segment_iter = iter(vocal_segments)
    seg_start, seg_end = next(segment_iter)
    cursor = seg_start

    for idx, line in enumerate(lines):
        line_start = cursor
        line_end = cursor + time_per_line

        # Advance cursor, wrapping into the next vocal segment if needed
        cursor = line_end
        while cursor > seg_end:
            try:
                seg_start, seg_end = next(segment_iter)
                cursor = seg_start + (cursor - seg_end)
            except StopIteration:
                cursor = audio_analysis.duration
                break

        aligned.append(
            AlignedLine(
                text=line,
                start=round(line_start, 3),
                end=round(min(line_end, audio_analysis.duration), 3),
                line_index=idx,
            )
        )

    return aligned


# ── Internal helpers ──────────────────────────────────────────────────────────


def _extract_lyric_lines(lyrics_text: str) -> list[str]:
    """Return non-empty, non-header lines from *lyrics_text*."""
    lines = []
    for raw_line in lyrics_text.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        # Skip section headers like [Verse 1] or (Chorus)
        if stripped.startswith("[") and stripped.endswith("]"):
            continue
        if stripped.startswith("(") and stripped.endswith(")"):
            continue
        lines.append(stripped)
    return lines


def _vocal_segments(analysis: AudioAnalysis) -> list[tuple[float, float]]:
    """Return (start, end) pairs representing non-silent portions of the track."""
    if not analysis.silence_regions:
        return [(0.0, analysis.duration)]

    silence = sorted(analysis.silence_regions)
    segments: list[tuple[float, float]] = []
    cursor = 0.0

    for s_start, s_end in silence:
        if s_start > cursor:
            segments.append((cursor, s_start))
        cursor = s_end

    if cursor < analysis.duration:
        segments.append((cursor, analysis.duration))

    return segments if segments else [(0.0, analysis.duration)]
