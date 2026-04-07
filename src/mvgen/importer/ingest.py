"""Project ingestion — load audio, lyrics, cover art, and assets."""

from __future__ import annotations

import logging
from pathlib import Path

from mvgen.models.project import Project

logger = logging.getLogger(__name__)

_AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".ogg", ".m4a"}
_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def ingest_project(project_dir: Path) -> Project:
    """Ingest a project directory and return a populated :class:`~mvgen.models.project.Project`.

    The function validates that the required files are present, discovers
    optional artefacts (cover art, scene notes, assets folder), normalises all
    paths, and creates the output directory.

    Parameters
    ----------
    project_dir:
        Path to the project root (e.g. ``examples/crimson_stain``).

    Returns
    -------
    Project
        A fully-populated :class:`~mvgen.models.project.Project` object ready
        for the next pipeline stage.

    Raises
    ------
    FileNotFoundError
        If ``project_dir`` does not exist or if no audio file is found.
    ValueError
        If a required file (``lyrics.txt``) is missing.
    """
    project_dir = project_dir.resolve()

    if not project_dir.exists():
        raise FileNotFoundError(f"Project directory not found: {project_dir}")

    logger.info("Ingesting project from %s", project_dir)

    # ── Required: audio ───────────────────────────────────────────────────────
    audio_path = _find_audio(project_dir)
    logger.info("Audio file: %s", audio_path)

    # ── Required: lyrics ──────────────────────────────────────────────────────
    lyrics_path = project_dir / "lyrics.txt"
    if not lyrics_path.exists():
        raise ValueError(f"lyrics.txt not found in {project_dir}")
    logger.info("Lyrics file: %s", lyrics_path)

    # ── Optional: cover art ───────────────────────────────────────────────────
    cover_path = _find_cover(project_dir)
    if cover_path:
        logger.info("Cover art: %s", cover_path)

    # ── Optional: assets directory ────────────────────────────────────────────
    assets_dir = project_dir / "assets"
    if not assets_dir.exists():
        assets_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Created assets directory: %s", assets_dir)
    else:
        logger.info("Assets directory: %s", assets_dir)

    # ── Optional: scene notes ─────────────────────────────────────────────────
    scene_notes_path = project_dir / "scene_notes.txt"
    if not scene_notes_path.exists():
        scene_notes_path = None
    else:
        logger.info("Scene notes: %s", scene_notes_path)

    # ── Output directory ──────────────────────────────────────────────────────
    output_dir = project_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Output directory: %s", output_dir)

    return Project(
        name=project_dir.name,
        root_dir=project_dir,
        audio_path=audio_path,
        lyrics_path=lyrics_path,
        cover_path=cover_path,
        assets_dir=assets_dir,
        scene_notes_path=scene_notes_path,
        output_dir=output_dir,
    )


# ── Helpers ───────────────────────────────────────────────────────────────────


def _find_audio(project_dir: Path) -> Path:
    """Return the first audio file found in *project_dir*."""
    # Prefer audio.mp3 / audio.wav by convention
    for name in ("audio.mp3", "audio.wav"):
        candidate = project_dir / name
        if candidate.exists():
            return candidate

    # Fall back to any audio file in the directory
    for ext in _AUDIO_EXTENSIONS:
        matches = list(project_dir.glob(f"*{ext}"))
        if matches:
            return matches[0]

    raise FileNotFoundError(f"No audio file found in {project_dir}")


def _find_cover(project_dir: Path) -> Path | None:
    """Return the cover art path, or ``None`` if not present."""
    for name in ("cover.jpg", "cover.jpeg", "cover.png"):
        candidate = project_dir / name
        if candidate.exists():
            return candidate

    # Fall back to any image at the project root
    for ext in _IMAGE_EXTENSIONS:
        matches = list(project_dir.glob(f"*{ext}"))
        if matches:
            return matches[0]

    return None
