"""Scene data model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Scene:
    """Represents a single scene in the music video timeline.

    A scene corresponds to a segment of the song (e.g. a verse, chorus, bridge)
    and carries all the information needed to plan and render that segment.
    """

    id: str
    """Unique scene identifier, e.g. ``"scene_001"``."""

    start: float
    """Start time in seconds."""

    end: float
    """End time in seconds."""

    section: str
    """Song section label: ``"verse_1"``, ``"chorus_1"``, ``"bridge"``,
    ``"intro"``, ``"outro"``, ``"instrumental"``, etc."""

    lyrics: list[str] = field(default_factory=list)
    """Lyric lines contained in this scene."""

    mood: str = "neutral"
    """Emotional tag, e.g. ``"dark"``, ``"urgent"``, ``"melancholy"``,
    ``"triumphant"``."""

    visual_goal: str = ""
    """High-level visual description for this scene."""

    asset_candidates: list[str] = field(default_factory=list)
    """Paths to candidate media files identified by the asset matcher."""

    selected_asset: Optional[str] = None
    """Chosen asset path after matching."""

    camera_motion: str = "static"
    """Camera motion hint: ``"static"``, ``"slow_zoom_in"``, ``"pan_left"``,
    ``"handheld"``, ``"pull_back"``."""

    transition_in: str = "cut"
    """Transition entering this scene: ``"cut"``, ``"crossfade"``,
    ``"fade_from_black"``, ``"wipe"``."""

    transition_out: str = "cut"
    """Transition exiting this scene: ``"cut"``, ``"crossfade"``,
    ``"fade_to_black"``."""

    lip_sync: bool = False
    """Whether this scene requires lip-sync."""

    lip_sync_ref: Optional[str] = None
    """Path to reference face clip when ``lip_sync`` is ``True``."""

    subtitle_mode: str = "lower_third"
    """Subtitle rendering mode: ``"overlay"``, ``"lower_third"``, ``"none"``,
    ``"karaoke"``."""

    generation_prompt: Optional[str] = None
    """Text prompt for AI image/video generation when no suitable asset exists."""

    @property
    def duration(self) -> float:
        """Scene duration in seconds."""
        return self.end - self.start

    def to_dict(self) -> dict:
        """Serialise to a plain dictionary."""
        return {
            "id": self.id,
            "start": self.start,
            "end": self.end,
            "section": self.section,
            "lyrics": self.lyrics,
            "mood": self.mood,
            "visual_goal": self.visual_goal,
            "asset_candidates": self.asset_candidates,
            "selected_asset": self.selected_asset,
            "camera_motion": self.camera_motion,
            "transition_in": self.transition_in,
            "transition_out": self.transition_out,
            "lip_sync": self.lip_sync,
            "lip_sync_ref": self.lip_sync_ref,
            "subtitle_mode": self.subtitle_mode,
            "generation_prompt": self.generation_prompt,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Scene":
        """Deserialise from a plain dictionary."""
        return cls(
            id=data["id"],
            start=data["start"],
            end=data["end"],
            section=data["section"],
            lyrics=data.get("lyrics", []),
            mood=data.get("mood", "neutral"),
            visual_goal=data.get("visual_goal", ""),
            asset_candidates=data.get("asset_candidates", []),
            selected_asset=data.get("selected_asset"),
            camera_motion=data.get("camera_motion", "static"),
            transition_in=data.get("transition_in", "cut"),
            transition_out=data.get("transition_out", "cut"),
            lip_sync=data.get("lip_sync", False),
            lip_sync_ref=data.get("lip_sync_ref"),
            subtitle_mode=data.get("subtitle_mode", "lower_third"),
            generation_prompt=data.get("generation_prompt"),
        )
