"""Tests for the scene planner."""

from __future__ import annotations

from mvgen.planner.scene_planner import _base_label, _infer_mood, plan_scenes
from mvgen.structure.detector import SongSection


def _make_sections(labels: list[str], duration: float = 30.0) -> list[SongSection]:
    n = len(labels)
    step = duration / n
    return [
        SongSection(
            label=label,
            start=i * step,
            end=(i + 1) * step,
            lyrics_lines=[f"{label} line {j}" for j in range(2)],
        )
        for i, label in enumerate(labels)
    ]


class TestPlanScenes:
    def test_scene_count_matches_sections(self, sample_audio_analysis):
        sections = _make_sections(["intro", "verse_1", "chorus_1", "verse_2", "chorus_2", "outro"])
        scenes = plan_scenes(sections, [], sample_audio_analysis)
        assert len(scenes) == len(sections)

    def test_scene_ids_unique(self, sample_audio_analysis):
        sections = _make_sections(["verse_1", "chorus_1", "bridge_1"])
        scenes = plan_scenes(sections, [], sample_audio_analysis)
        ids = [s.id for s in scenes]
        assert len(ids) == len(set(ids))

    def test_chorus_has_lip_sync(self, sample_audio_analysis):
        sections = _make_sections(["verse_1", "chorus_1"])
        scenes = plan_scenes(sections, [], sample_audio_analysis)
        chorus_scene = next(s for s in scenes if "chorus" in s.section)
        assert chorus_scene.lip_sync is True

    def test_verse_no_lip_sync_by_default(self, sample_audio_analysis):
        sections = _make_sections(["verse_1"])
        scenes = plan_scenes(sections, [], sample_audio_analysis)
        assert scenes[0].lip_sync is False

    def test_first_scene_fade_from_black(self, sample_audio_analysis):
        sections = _make_sections(["intro", "verse_1"])
        scenes = plan_scenes(sections, [], sample_audio_analysis)
        assert scenes[0].transition_in == "fade_from_black"

    def test_last_scene_fade_to_black(self, sample_audio_analysis):
        sections = _make_sections(["intro", "outro"])
        scenes = plan_scenes(sections, [], sample_audio_analysis)
        assert scenes[-1].transition_out == "fade_to_black"

    def test_moods_assigned(self, sample_audio_analysis):
        sections = _make_sections(["verse_1", "chorus_1", "bridge_1"])
        scenes = plan_scenes(sections, [], sample_audio_analysis)
        for scene in scenes:
            assert scene.mood  # Not empty

    def test_start_end_match_section(self, sample_audio_analysis):
        sections = _make_sections(["verse_1", "chorus_1"])
        scenes = plan_scenes(sections, [], sample_audio_analysis)
        for scene, section in zip(scenes, sections):
            assert scene.start == section.start
            assert scene.end == section.end

    def test_visual_goal_set(self, sample_audio_analysis):
        sections = _make_sections(["verse_1"])
        scenes = plan_scenes(sections, [], sample_audio_analysis)
        assert scenes[0].visual_goal != ""


class TestInferMood:
    def test_dark_keyword_overrides_section_default(self):
        mood = _infer_mood("chorus", ["blood rains down"])
        assert mood == "dark"

    def test_section_default_used_without_keywords(self):
        assert _infer_mood("chorus", ["la la la"]) == "triumphant"
        assert _infer_mood("bridge", ["bridge stuff"]) == "melancholy"

    def test_unknown_section_returns_neutral(self):
        assert _infer_mood("unknown_section", ["lalala"]) == "neutral"


class TestBaseLabel:
    def test_strips_numeric_suffix(self):
        assert _base_label("chorus_2") == "chorus"
        assert _base_label("verse_10") == "verse"

    def test_no_suffix_unchanged(self):
        assert _base_label("bridge") == "bridge"
        assert _base_label("final_chorus") == "final_chorus"
