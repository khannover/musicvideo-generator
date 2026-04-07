"""Prompt builder — generate per-scene AI image/video prompts."""

from __future__ import annotations

import logging

from mvgen.models.scene import Scene

logger = logging.getLogger(__name__)

# ── Mood → visual style modifiers ─────────────────────────────────────────────
_MOOD_STYLES: dict[str, str] = {
    "dark": "cinematic dark tones, dramatic shadows, low-key lighting, gritty texture",
    "urgent": "fast motion blur, high contrast, intense red/orange palette, dynamic angle",
    "melancholy": "desaturated blues and greys, soft focus, slow drift, lonely atmosphere",
    "triumphant": "golden hour light, soaring wide shot, vibrant colours, epic scale",
    "neutral": "balanced exposure, clean composition, versatile framing",
}

# ── Camera motion → prompt modifier ──────────────────────────────────────────
_CAMERA_MODS: dict[str, str] = {
    "static": "static shot, stable frame",
    "slow_zoom_in": "subtle slow zoom in, tightening focus",
    "pan_left": "smooth horizontal pan left",
    "handheld": "slight handheld shake, intimate feel",
    "pull_back": "slow pull-back reveal, expanding view",
}


def build_prompts(scenes: list[Scene]) -> list[Scene]:
    """Populate ``generation_prompt`` for each scene that lacks one.

    For scenes that already have a ``generation_prompt`` set, the existing
    value is preserved.  For the rest, a template-based prompt is constructed
    from the scene's ``mood``, ``visual_goal``, ``lyrics``, and
    ``camera_motion``.

    The function mutates the scenes in-place **and** returns the list so it
    can be used in a pipeline chain.

    Parameters
    ----------
    scenes:
        List of :class:`~mvgen.models.scene.Scene` objects.

    Returns
    -------
    list[Scene]
        The same list, each scene now having a ``generation_prompt``.
    """
    for scene in scenes:
        if scene.generation_prompt:
            continue  # Preserve manually-set prompts
        scene.generation_prompt = _build_prompt(scene)
        logger.debug("Built prompt for %s: %s", scene.id, scene.generation_prompt[:80])

    logger.info("Prompts built for %d scenes", len(scenes))
    return scenes


# ── Internal helpers ──────────────────────────────────────────────────────────


def _build_prompt(scene: Scene) -> str:
    """Construct a generation prompt string for a single scene."""
    parts: list[str] = []

    # Base visual goal
    if scene.visual_goal:
        parts.append(scene.visual_goal)

    # Mood / style
    style = _MOOD_STYLES.get(scene.mood, _MOOD_STYLES["neutral"])
    parts.append(style)

    # Lyric snippet (first two lines max, as contextual flavour)
    if scene.lyrics:
        snippet = "; ".join(scene.lyrics[:2])
        parts.append(f'Inspired by: "{snippet}"')

    # Camera motion
    cam_mod = _CAMERA_MODS.get(scene.camera_motion, "")
    if cam_mod:
        parts.append(cam_mod)

    # Technical suffix
    parts.append("photorealistic, 4K, music video aesthetic")

    return ". ".join(parts) + "."
