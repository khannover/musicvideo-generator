"""Scene planner — convert song sections into Scene objects."""

from __future__ import annotations

import logging

from mvgen.audio.analyzer import AudioAnalysis
from mvgen.lyrics.aligner import AlignedLine
from mvgen.models.scene import Scene
from mvgen.structure.detector import SongSection

logger = logging.getLogger(__name__)

# ── Mood mappings ─────────────────────────────────────────────────────────────
_SECTION_MOOD: dict[str, str] = {
    "intro": "neutral",
    "verse": "dark",
    "pre_chorus": "urgent",
    "chorus": "triumphant",
    "post_chorus": "triumphant",
    "bridge": "melancholy",
    "outro": "melancholy",
    "instrumental": "neutral",
    "final_chorus": "triumphant",
    "interlude": "neutral",
}

_KEYWORD_MOOD: dict[str, str] = {
    "fire": "urgent",
    "flame": "urgent",
    "burn": "urgent",
    "blood": "dark",
    "death": "dark",
    "dark": "dark",
    "shadow": "dark",
    "hope": "triumphant",
    "rise": "triumphant",
    "light": "triumphant",
    "love": "melancholy",
    "tears": "melancholy",
    "rain": "melancholy",
    "lost": "melancholy",
    "broken": "dark",
    "war": "dark",
    "pain": "dark",
}

# ── Camera motion defaults per section ───────────────────────────────────────
_SECTION_CAMERA: dict[str, str] = {
    "intro": "slow_zoom_in",
    "verse": "slow_zoom_in",
    "pre_chorus": "handheld",
    "chorus": "pull_back",
    "post_chorus": "pull_back",
    "bridge": "static",
    "outro": "pull_back",
    "instrumental": "pan_left",
    "final_chorus": "pull_back",
    "interlude": "static",
}

# ── Sections that default to lip-sync ────────────────────────────────────────
_LIP_SYNC_SECTIONS = {"chorus", "final_chorus", "pre_chorus"}


def plan_scenes(
    sections: list[SongSection],
    aligned_lyrics: list[AlignedLine],
    audio_analysis: AudioAnalysis,
) -> list[Scene]:
    """Map song sections to :class:`~mvgen.models.scene.Scene` objects.

    Each section produces exactly one scene.  Mood is inferred from the
    section type and lyric keywords.  Camera motion and transition defaults
    are assigned based on section type.

    Parameters
    ----------
    sections:
        Ordered list of :class:`~mvgen.structure.detector.SongSection` objects.
    aligned_lyrics:
        Lyric alignment data (used for per-scene subtitle lines).
    audio_analysis:
        Audio analysis result (used for duration context).

    Returns
    -------
    list[Scene]
        One :class:`~mvgen.models.scene.Scene` per section.
    """
    scenes: list[Scene] = []

    for idx, section in enumerate(sections):
        scene_id = f"scene_{idx + 1:03d}"

        # Extract aligned lyric lines that fall within this section's time range
        scene_lyrics = _lines_for_section(aligned_lyrics, section.start, section.end)
        if not scene_lyrics:
            scene_lyrics = section.lyrics_lines

        # Infer mood
        base_label = _base_label(section.label)
        mood = _infer_mood(base_label, scene_lyrics)

        # Camera motion
        camera_motion = _SECTION_CAMERA.get(base_label, "slow_zoom_in")

        # Transitions
        if idx == 0:
            transition_in = "fade_from_black"
        else:
            transition_in = "crossfade"

        if idx == len(sections) - 1:
            transition_out = "fade_to_black"
        else:
            transition_out = "crossfade"

        # Lip-sync
        lip_sync = base_label in _LIP_SYNC_SECTIONS

        # Visual goal (generic placeholder; will be enriched by the prompt builder)
        visual_goal = _visual_goal(base_label, mood)

        scene = Scene(
            id=scene_id,
            start=section.start,
            end=section.end,
            section=section.label,
            lyrics=scene_lyrics,
            mood=mood,
            visual_goal=visual_goal,
            camera_motion=camera_motion,
            transition_in=transition_in,
            transition_out=transition_out,
            lip_sync=lip_sync,
            subtitle_mode="lower_third",
        )
        scenes.append(scene)
        logger.debug("Planned %s: %s–%s [%s] lip_sync=%s", scene_id, section.start, section.end, mood, lip_sync)

    logger.info("Planned %d scenes", len(scenes))
    return scenes


# ── Helpers ───────────────────────────────────────────────────────────────────


def _base_label(label: str) -> str:
    """Strip numeric suffix from a section label."""
    import re

    return re.sub(r"_\d+$", "", label)


def _lines_for_section(aligned: list[AlignedLine], start: float, end: float) -> list[str]:
    """Return lyric line texts whose start time falls within [start, end)."""
    return [line.text for line in aligned if start <= line.start < end]


def _infer_mood(base_label: str, lyrics: list[str]) -> str:
    """Infer mood from section type and lyric keywords."""
    # Check lyrics for mood keywords first
    combined = " ".join(lyrics).lower()
    for keyword, mood in _KEYWORD_MOOD.items():
        if keyword in combined:
            return mood
    return _SECTION_MOOD.get(base_label, "neutral")


def _visual_goal(base_label: str, mood: str) -> str:
    """Return a generic visual goal string."""
    templates: dict[str, str] = {
        "intro": "Establishing wide shot setting the scene atmosphere",
        "verse": "Narrative imagery reflecting the lyric story",
        "pre_chorus": "Tension-building close-ups and environment",
        "chorus": "High-energy montage or performance focal point",
        "post_chorus": "Momentum carrying shots from chorus",
        "bridge": "Contrast or turning-point imagery",
        "outro": "Resolution or fading imagery",
        "instrumental": "Abstract or environmental B-roll",
        "final_chorus": "Climactic performance or montage",
        "interlude": "Transitional atmospheric imagery",
    }
    return templates.get(base_label, f"{mood.capitalize()} cinematic shot")
