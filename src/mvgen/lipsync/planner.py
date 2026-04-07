"""Lip-sync planner — identify segments needing lip-sync and assign reference clips."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from mvgen.models.scene import Scene

logger = logging.getLogger(__name__)

# Filename keywords that suggest a face / character clip
_FACE_KEYWORDS = {
    "face", "character", "singer", "performer", "lipsync", "lip_sync",
    "close", "portrait", "head", "vocal", "person",
}

_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}


def plan_lipsync(scenes: list[Scene], assets_dir: Path) -> list[Scene]:
    """Assign lip-sync reference clips to scenes that require them.

    For each scene where ``lip_sync=True``:

    * If ``lip_sync_ref`` is already set, it is preserved.
    * Otherwise the function searches *assets_dir* for video files whose
      filename contains face/character keywords and assigns the best match.
    * If no face clip is found, ``lip_sync=True`` is retained as a flag for
      future generation.

    Parameters
    ----------
    scenes:
        List of :class:`~mvgen.models.scene.Scene` objects.
    assets_dir:
        Root of the media asset pool.

    Returns
    -------
    list[Scene]
        The same list with ``lip_sync_ref`` populated where possible.
    """
    assets_dir = Path(assets_dir)
    face_clips = _find_face_clips(assets_dir)

    if face_clips:
        logger.info("Found %d face/character clips for lip-sync", len(face_clips))
    else:
        logger.info("No face clips found; lip_sync flag retained for generation")

    for scene in scenes:
        if not scene.lip_sync:
            continue
        if scene.lip_sync_ref:
            continue  # Already assigned

        best = _best_clip_for_scene(scene, face_clips)
        if best:
            scene.lip_sync_ref = str(best)
            logger.debug("%s → lip_sync_ref: %s", scene.id, best.name)
        else:
            logger.debug("%s: no lip-sync clip found (flag kept for generation)", scene.id)

    return scenes


# ── Internal helpers ──────────────────────────────────────────────────────────


def _find_face_clips(assets_dir: Path) -> list[Path]:
    """Return video files from *assets_dir* that look like face/character clips."""
    if not assets_dir.exists():
        return []
    clips = []
    for p in assets_dir.rglob("*"):
        if p.suffix.lower() not in _VIDEO_EXTENSIONS:
            continue
        stem_tokens = set(re.findall(r"[a-z]+", p.stem.lower()))
        if stem_tokens & _FACE_KEYWORDS:
            clips.append(p)
    return clips


def _best_clip_for_scene(scene: Scene, face_clips: list[Path]) -> Path | None:
    """Return the face clip most relevant to *scene*, or ``None``."""
    if not face_clips:
        return None

    scene_tokens = set(
        re.findall(r"[a-z]+", f"{scene.section} {scene.mood} {' '.join(scene.lyrics)}".lower())
    )

    scored = []
    for clip in face_clips:
        clip_tokens = set(re.findall(r"[a-z]+", clip.stem.lower()))
        overlap = len(scene_tokens & clip_tokens)
        scored.append((overlap, clip))

    scored.sort(key=lambda x: (-x[0], x[1].name))
    return scored[0][1]
