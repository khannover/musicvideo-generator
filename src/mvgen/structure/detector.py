"""Song structure detection — identify verse, chorus, bridge, etc.

The initial implementation uses heuristics:

* Section headers embedded in the lyrics text (``[Verse 1]``, ``[Chorus]``, …)
* Repeated lyric blocks (chorus detection via text similarity)
* Audio structural boundaries from the :class:`~mvgen.audio.analyzer.AudioAnalysis`

The interface is designed so a machine-learning replacement can be swapped in
without changing call sites.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from mvgen.audio.analyzer import AudioAnalysis

logger = logging.getLogger(__name__)

# ── Valid section labels (canonical form) ─────────────────────────────────────
VALID_LABELS = {
    "intro",
    "verse",
    "pre_chorus",
    "chorus",
    "post_chorus",
    "bridge",
    "outro",
    "instrumental",
    "final_chorus",
    "interlude",
}

# ── Header → canonical label mapping ─────────────────────────────────────────
_HEADER_ALIASES: dict[str, str] = {
    "verse": "verse",
    "chorus": "chorus",
    "pre-chorus": "pre_chorus",
    "pre chorus": "pre_chorus",
    "prechorus": "pre_chorus",
    "post-chorus": "post_chorus",
    "post chorus": "post_chorus",
    "bridge": "bridge",
    "intro": "intro",
    "outro": "outro",
    "instrumental": "instrumental",
    "final chorus": "final_chorus",
    "final_chorus": "final_chorus",
    "interlude": "interlude",
    "hook": "chorus",
    "refrain": "chorus",
}


@dataclass
class SongSection:
    """A labelled segment of the song."""

    label: str
    """Canonical section label (e.g. ``"chorus"``, ``"verse"``)."""

    start: float
    """Start time in seconds."""

    end: float
    """End time in seconds."""

    lyrics_lines: list[str] = field(default_factory=list)
    """Lyric lines belonging to this section."""

    @property
    def duration(self) -> float:
        """Section duration in seconds."""
        return self.end - self.start


def detect_structure(
    lyrics_text: str,
    audio_analysis: AudioAnalysis,
) -> list[SongSection]:
    """Detect song sections from lyrics text and audio analysis.

    The function first attempts to parse explicit section headers from the
    lyrics (``[Verse 1]``, ``[Chorus]``, etc.).  If no headers are found it
    falls back to an audio-boundary-based segmentation with naive repeated-
    block chorus detection.

    Parameters
    ----------
    lyrics_text:
        Raw lyric text, optionally containing section headers.
    audio_analysis:
        Pre-computed audio analysis.

    Returns
    -------
    list[SongSection]
        Ordered list of :class:`SongSection` objects spanning the full track.
    """
    raw_sections = _parse_lyric_headers(lyrics_text)

    if raw_sections:
        logger.info("Parsed %d sections from lyric headers", len(raw_sections))
        sections = _assign_times_from_headers(raw_sections, audio_analysis)
    else:
        logger.info("No lyric headers found; using audio boundaries")
        sections = _sections_from_audio_boundaries(lyrics_text, audio_analysis)

    _deduplicate_labels(sections)
    logger.info(
        "Structure: %s",
        ", ".join(f"{s.label}({s.start:.1f}-{s.end:.1f})" for s in sections),
    )
    return sections


# ── Header parsing ────────────────────────────────────────────────────────────


def _parse_lyric_headers(lyrics_text: str) -> list[dict]:
    """Return raw section dicts ``{label, lines}`` from header-tagged lyrics."""
    header_re = re.compile(r"^\[([^\]]+)\]$", re.IGNORECASE)
    sections: list[dict] = []
    current_label: str | None = None
    current_lines: list[str] = []

    for raw_line in lyrics_text.splitlines():
        stripped = raw_line.strip()
        m = header_re.match(stripped)
        if m:
            if current_label is not None:
                sections.append({"label": current_label, "lines": list(current_lines)})
            header_text = m.group(1).strip().lower()
            # Strip trailing numbers for canonical lookup
            base = re.sub(r"\s*\d+$", "", header_text).strip()
            current_label = _HEADER_ALIASES.get(base, _HEADER_ALIASES.get(header_text, base.replace(" ", "_")))
            current_lines = []
        elif stripped and current_label is not None:
            current_lines.append(stripped)

    if current_label is not None:
        sections.append({"label": current_label, "lines": list(current_lines)})

    return sections


def _assign_times_from_headers(
    raw_sections: list[dict],
    audio_analysis: AudioAnalysis,
) -> list[SongSection]:
    """Assign timestamps to header-parsed sections.

    Distributes time proportional to the number of lyric lines in each section,
    using audio structural boundaries as hints when available.
    """
    total_lines = sum(len(s["lines"]) for s in raw_sections)
    if total_lines == 0:
        total_lines = len(raw_sections)

    duration = audio_analysis.duration
    cursor = 0.0
    result: list[SongSection] = []

    for sec in raw_sections:
        n_lines = max(len(sec["lines"]), 1)
        fraction = n_lines / total_lines
        sec_duration = duration * fraction
        end = min(cursor + sec_duration, duration)
        result.append(
            SongSection(
                label=sec["label"],
                start=round(cursor, 3),
                end=round(end, 3),
                lyrics_lines=sec["lines"],
            )
        )
        cursor = end

    return result


# ── Audio-boundary fallback ───────────────────────────────────────────────────


def _sections_from_audio_boundaries(
    lyrics_text: str,
    audio_analysis: AudioAnalysis,
) -> list[SongSection]:
    """Create sections from audio structural boundaries + naive chorus detection."""
    boundaries = sorted(audio_analysis.structural_boundaries)
    # Build time slices
    time_points = [0.0, *boundaries, audio_analysis.duration]
    slices = [(time_points[i], time_points[i + 1]) for i in range(len(time_points) - 1)]

    lyric_lines = [ln for ln in lyrics_text.splitlines() if ln.strip()]
    lines_per_slice = max(1, len(lyric_lines) // len(slices))

    sections: list[SongSection] = []
    for i, (start, end) in enumerate(slices):
        line_start = i * lines_per_slice
        line_end = line_start + lines_per_slice
        chunk = lyric_lines[line_start:line_end]
        label = _guess_label(i, len(slices), chunk, sections)
        sections.append(SongSection(label=label, start=round(start, 3), end=round(end, 3), lyrics_lines=chunk))

    return sections


def _guess_label(idx: int, total: int, lines: list[str], existing: list[SongSection]) -> str:
    """Heuristically assign a section label."""
    if idx == 0:
        return "intro"
    if idx == total - 1:
        return "outro"

    # Check for repeated lines → chorus
    for prev in existing:
        if prev.label in ("chorus", "final_chorus"):
            similarity = _block_similarity(lines, prev.lyrics_lines)
            if similarity > 0.6:
                return "chorus"

    # Simple alternation heuristic
    if idx % 2 == 1:
        return "verse"
    return "chorus"


def _block_similarity(a: list[str], b: list[str]) -> float:
    """Return a similarity score between two lyric blocks."""
    text_a = " ".join(a).lower()
    text_b = " ".join(b).lower()
    return SequenceMatcher(None, text_a, text_b).ratio()


# ── Label deduplication ───────────────────────────────────────────────────────


def _deduplicate_labels(sections: list[SongSection]) -> None:
    """Add numeric suffixes to repeated section labels (in-place)."""
    counts: dict[str, int] = {}
    for sec in sections:
        base = sec.label
        counts[base] = counts.get(base, 0) + 1
        if counts[base] > 1:
            sec.label = f"{base}_{counts[base]}"
        # First occurrence keeps base label (no suffix) unless it appears > once
    # Re-label first occurrences if there are duplicates
    label_total: dict[str, int] = {}
    for sec in sections:
        # strip trailing _N
        base = re.sub(r"_\d+$", "", sec.label)
        label_total[base] = label_total.get(base, 0) + 1

    occurrence: dict[str, int] = {}
    for sec in sections:
        base = re.sub(r"_\d+$", "", sec.label)
        occurrence[base] = occurrence.get(base, 0) + 1
        if label_total[base] > 1:
            sec.label = f"{base}_{occurrence[base]}"
