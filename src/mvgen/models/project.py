"""Project manifest model."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from mvgen.models.timeline import Timeline


@dataclass
class Project:
    """Represents a single music-video project on disk.

    A ``Project`` acts as the top-level container that ties together all the
    input files, the computed ``Timeline``, and the output directory.
    """

    name: str
    """Human-readable project name (typically the directory name)."""

    root_dir: Path
    """Absolute path to the project root directory."""

    audio_path: Path
    """Path to the master audio file (``audio.mp3`` or ``audio.wav``)."""

    lyrics_path: Path
    """Path to the plain-text lyrics file (``lyrics.txt``)."""

    cover_path: Optional[Path] = None
    """Path to the cover art image (``cover.jpg`` / ``cover.png``), if present."""

    assets_dir: Path = field(default_factory=Path)
    """Path to the media assets directory."""

    scene_notes_path: Optional[Path] = None
    """Path to the optional ``scene_notes.txt`` file."""

    output_dir: Path = field(default_factory=Path)
    """Path to the output directory where renders are written."""

    timeline: Optional[Timeline] = None
    """The computed ``Timeline`` for this project (populated after pipeline run)."""

    def __post_init__(self) -> None:
        # Ensure output dir and assets dir are Path objects
        if not isinstance(self.assets_dir, Path):
            self.assets_dir = Path(self.assets_dir)
        if not isinstance(self.output_dir, Path):
            self.output_dir = Path(self.output_dir)

    @property
    def timeline_path(self) -> Path:
        """Canonical path for the serialised timeline JSON."""
        return self.output_dir / "timeline.json"
