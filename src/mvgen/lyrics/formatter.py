"""Lyric formatter — export aligned lyrics to SRT, LRC, and JSON."""

from __future__ import annotations

import json

from mvgen.lyrics.aligner import AlignedLine


def to_srt(aligned: list[AlignedLine]) -> str:
    """Convert aligned lyric lines to SubRip (SRT) subtitle format.

    Parameters
    ----------
    aligned:
        List of :class:`~mvgen.lyrics.aligner.AlignedLine` objects.

    Returns
    -------
    str
        SRT-formatted subtitle string.
    """
    blocks: list[str] = []
    for i, line in enumerate(aligned, start=1):
        start_ts = _seconds_to_srt_timestamp(line.start)
        end_ts = _seconds_to_srt_timestamp(line.end)
        blocks.append(f"{i}\n{start_ts} --> {end_ts}\n{line.text}")
    return "\n\n".join(blocks)


def to_lrc(aligned: list[AlignedLine]) -> str:
    """Convert aligned lyric lines to LRC (lyrics) format.

    Parameters
    ----------
    aligned:
        List of :class:`~mvgen.lyrics.aligner.AlignedLine` objects.

    Returns
    -------
    str
        LRC-formatted string.
    """
    lines: list[str] = []
    for line in aligned:
        ts = _seconds_to_lrc_timestamp(line.start)
        lines.append(f"[{ts}]{line.text}")
    return "\n".join(lines)


def to_json(aligned: list[AlignedLine]) -> str:
    """Serialise aligned lyrics to JSON.

    Parameters
    ----------
    aligned:
        List of :class:`~mvgen.lyrics.aligner.AlignedLine` objects.

    Returns
    -------
    str
        JSON array of alignment records.
    """
    records = []
    for line in aligned:
        record: dict = {
            "line_index": line.line_index,
            "text": line.text,
            "start": line.start,
            "end": line.end,
        }
        if line.words is not None:
            record["words"] = [
                {"text": w.text, "start": w.start, "end": w.end}
                for w in line.words
            ]
        records.append(record)
    return json.dumps(records, indent=2)


# ── Timestamp helpers ─────────────────────────────────────────────────────────


def _seconds_to_srt_timestamp(seconds: float) -> str:
    """Convert *seconds* to ``HH:MM:SS,mmm`` SRT timestamp."""
    total_ms = int(round(seconds * 1000))
    ms = total_ms % 1000
    total_s = total_ms // 1000
    h = total_s // 3600
    m = (total_s % 3600) // 60
    s = total_s % 60
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _seconds_to_lrc_timestamp(seconds: float) -> str:
    """Convert *seconds* to ``mm:ss.xx`` LRC timestamp."""
    total_cs = int(round(seconds * 100))
    cs = total_cs % 100
    total_s = total_cs // 100
    m = total_s // 60
    s = total_s % 60
    return f"{m:02d}:{s:02d}.{cs:02d}"
