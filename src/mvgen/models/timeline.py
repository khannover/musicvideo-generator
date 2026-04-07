"""Timeline data model — the canonical project state."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Optional

from mvgen.models.scene import Scene


@dataclass
class Timeline:
    """The canonical project state for a music video.

    A ``Timeline`` holds all the information needed to render (or re-render)
    a music video without re-running the full pipeline.  It can be serialised
    to / deserialised from JSON so that it can be saved, edited, and reloaded
    independently of the pipeline stages that produced it.
    """

    project_name: str
    """Human-readable project name."""

    audio_path: str
    """Absolute or project-relative path to the master audio file."""

    duration: float
    """Total duration of the audio in seconds."""

    bpm: Optional[float] = None
    """Estimated tempo in beats-per-minute (``None`` if unknown)."""

    scenes: list[Scene] = field(default_factory=list)
    """Ordered list of scenes."""

    lyrics_aligned: list[dict] = field(default_factory=list)
    """Word-level alignment data: ``[{word, start, end, line_index}, ...]``."""

    metadata: dict = field(default_factory=dict)
    """Freeform metadata (e.g. sample-rate, key, mood tags)."""

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """Serialise to a plain dictionary."""
        return {
            "project_name": self.project_name,
            "audio_path": self.audio_path,
            "duration": self.duration,
            "bpm": self.bpm,
            "scenes": [s.to_dict() for s in self.scenes],
            "lyrics_aligned": self.lyrics_aligned,
            "metadata": self.metadata,
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialise to a JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: dict) -> "Timeline":
        """Deserialise from a plain dictionary."""
        return cls(
            project_name=data["project_name"],
            audio_path=data["audio_path"],
            duration=data["duration"],
            bpm=data.get("bpm"),
            scenes=[Scene.from_dict(s) for s in data.get("scenes", [])],
            lyrics_aligned=data.get("lyrics_aligned", []),
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "Timeline":
        """Deserialise from a JSON string."""
        return cls.from_dict(json.loads(json_str))
