"""Tests for data models — Scene, Timeline, Project."""

from __future__ import annotations

import json

import pytest

from mvgen.models.scene import Scene
from mvgen.models.timeline import Timeline


class TestScene:
    def test_defaults(self):
        s = Scene(id="scene_001", start=0.0, end=5.0, section="verse_1")
        assert s.mood == "neutral"
        assert s.lip_sync is False
        assert s.selected_asset is None
        assert s.lyrics == []

    def test_duration_property(self):
        s = Scene(id="scene_001", start=2.5, end=7.5, section="chorus")
        assert s.duration == pytest.approx(5.0)

    def test_round_trip(self):
        s = Scene(
            id="scene_002",
            start=10.0,
            end=20.0,
            section="chorus_1",
            lyrics=["Line one", "Line two"],
            mood="dark",
            visual_goal="Burning skyline",
            asset_candidates=["/path/a.jpg", "/path/b.mp4"],
            selected_asset="/path/a.jpg",
            camera_motion="slow_zoom_in",
            transition_in="fade_from_black",
            transition_out="crossfade",
            lip_sync=True,
            lip_sync_ref="/path/face.mp4",
            subtitle_mode="karaoke",
            generation_prompt="A dark burning skyline.",
        )
        d = s.to_dict()
        restored = Scene.from_dict(d)
        assert restored.id == s.id
        assert restored.start == s.start
        assert restored.end == s.end
        assert restored.section == s.section
        assert restored.lyrics == s.lyrics
        assert restored.mood == s.mood
        assert restored.visual_goal == s.visual_goal
        assert restored.asset_candidates == s.asset_candidates
        assert restored.selected_asset == s.selected_asset
        assert restored.camera_motion == s.camera_motion
        assert restored.transition_in == s.transition_in
        assert restored.transition_out == s.transition_out
        assert restored.lip_sync == s.lip_sync
        assert restored.lip_sync_ref == s.lip_sync_ref
        assert restored.subtitle_mode == s.subtitle_mode
        assert restored.generation_prompt == s.generation_prompt

    def test_from_dict_missing_optional_keys(self):
        """from_dict should work with minimal required keys."""
        d = {"id": "scene_001", "start": 0.0, "end": 3.0, "section": "verse"}
        s = Scene.from_dict(d)
        assert s.id == "scene_001"
        assert s.mood == "neutral"
        assert s.lip_sync is False


class TestTimeline:
    def _make_timeline(self) -> Timeline:
        scenes = [
            Scene(id="scene_001", start=0.0, end=5.0, section="verse_1"),
            Scene(id="scene_002", start=5.0, end=10.0, section="chorus_1", lip_sync=True),
        ]
        return Timeline(
            project_name="Test Project",
            audio_path="/tmp/audio.mp3",
            duration=10.0,
            bpm=120.0,
            scenes=scenes,
            lyrics_aligned=[{"text": "Hello", "start": 0.5, "end": 1.5, "line_index": 0}],
            metadata={"key": "C minor"},
        )

    def test_to_json_is_valid_json(self):
        t = self._make_timeline()
        raw = t.to_json()
        parsed = json.loads(raw)
        assert parsed["project_name"] == "Test Project"
        assert len(parsed["scenes"]) == 2

    def test_json_round_trip(self):
        t = self._make_timeline()
        restored = Timeline.from_json(t.to_json())

        assert restored.project_name == t.project_name
        assert restored.audio_path == t.audio_path
        assert restored.duration == t.duration
        assert restored.bpm == t.bpm
        assert len(restored.scenes) == len(t.scenes)
        assert restored.lyrics_aligned == t.lyrics_aligned
        assert restored.metadata == t.metadata

    def test_scene_round_trip_inside_timeline(self):
        t = self._make_timeline()
        restored = Timeline.from_json(t.to_json())
        scene = restored.scenes[1]
        assert scene.lip_sync is True
        assert scene.section == "chorus_1"

    def test_bpm_none(self):
        t = Timeline(project_name="X", audio_path="/a.mp3", duration=5.0)
        raw = t.to_json()
        restored = Timeline.from_json(raw)
        assert restored.bpm is None
