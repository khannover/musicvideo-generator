"""End-to-end pipeline integration tests.

All external calls (FFmpeg, librosa) are mocked so the test can run in CI
without heavy dependencies or media files.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from mvgen.models.timeline import Timeline


def _write_lyrics(path: Path) -> None:
    path.write_text(
        """\
[Verse 1]
Line one verse
Line two verse

[Chorus]
Hook line one
Hook line two
""",
        encoding="utf-8",
    )


def _make_audio_analysis(duration: float = 20.0):
    from mvgen.audio.analyzer import AudioAnalysis

    n = 40
    step = duration / n
    return AudioAnalysis(
        duration=duration,
        sample_rate=22050,
        bpm=120.0,
        beat_times=[step * i for i in range(40)],
        energy_times=[step * i for i in range(n)],
        energy_values=[0.1] * n,
        silence_regions=[],
        structural_boundaries=[5.0, 10.0, 15.0],
        onset_times=[step * i for i in range(40)],
    )


_NO_PREVIEW_STAGES = [
    "ingest", "audio_analysis", "lyric_alignment", "structure_detection",
    "scene_planning", "prompt_building", "asset_matching", "lipsync_planning",
]


class TestRunPipeline:
    @patch("mvgen.renderer.preview.render_preview", autospec=True)
    @patch("mvgen.audio.analyzer.analyze_audio")
    def test_pipeline_returns_timeline(self, mock_analyze, mock_render_preview, tmp_path):
        """Full pipeline should produce a Timeline and save timeline.json."""
        mock_analyze.return_value = _make_audio_analysis()
        mock_render_preview.return_value = tmp_path / "output" / "preview.mp4"

        (tmp_path / "audio.wav").write_bytes(b"")
        _write_lyrics(tmp_path / "lyrics.txt")
        (tmp_path / "assets").mkdir()

        from mvgen.pipeline import run_pipeline

        timeline = run_pipeline(tmp_path, config={"resume": False, "pipeline": {"stages": _NO_PREVIEW_STAGES}})

        assert isinstance(timeline, Timeline)
        assert len(timeline.scenes) > 0
        assert timeline.duration == pytest.approx(20.0)

    @patch("mvgen.audio.analyzer.analyze_audio")
    def test_timeline_json_written(self, mock_analyze, tmp_path):
        mock_analyze.return_value = _make_audio_analysis()

        (tmp_path / "audio.wav").write_bytes(b"")
        _write_lyrics(tmp_path / "lyrics.txt")
        (tmp_path / "assets").mkdir()

        from mvgen.pipeline import run_pipeline

        run_pipeline(tmp_path, config={"resume": False, "pipeline": {"stages": _NO_PREVIEW_STAGES}})

        timeline_path = tmp_path / "output" / "timeline.json"
        assert timeline_path.exists()

        # Verify it's valid JSON and parses correctly
        restored = Timeline.from_json(timeline_path.read_text(encoding="utf-8"))
        assert restored.project_name == tmp_path.name

    @patch("mvgen.audio.analyzer.analyze_audio")
    def test_resume_loads_existing_timeline(self, mock_analyze, tmp_path):
        """If timeline.json exists and resume=True, pipeline skips reanalysis."""
        mock_analyze.return_value = _make_audio_analysis()

        (tmp_path / "audio.wav").write_bytes(b"")
        _write_lyrics(tmp_path / "lyrics.txt")
        (tmp_path / "assets").mkdir()

        # First run — creates timeline.json
        from mvgen.pipeline import run_pipeline

        run_pipeline(tmp_path, config={"resume": False, "pipeline": {"stages": _NO_PREVIEW_STAGES}})
        assert mock_analyze.call_count == 1

        # Second run with resume=True — should NOT call analyze_audio again
        run_pipeline(tmp_path, config={"resume": True, "pipeline": {"stages": _NO_PREVIEW_STAGES}})
        assert mock_analyze.call_count == 1  # Still 1, not 2

    @patch("mvgen.audio.analyzer.analyze_audio")
    def test_scenes_have_prompts(self, mock_analyze, tmp_path):
        mock_analyze.return_value = _make_audio_analysis()

        (tmp_path / "audio.wav").write_bytes(b"")
        _write_lyrics(tmp_path / "lyrics.txt")
        (tmp_path / "assets").mkdir()

        from mvgen.pipeline import run_pipeline

        timeline = run_pipeline(tmp_path, config={"resume": False, "pipeline": {"stages": _NO_PREVIEW_STAGES}})

        for scene in timeline.scenes:
            assert scene.generation_prompt, f"Scene {scene.id} has no generation_prompt"

    @patch("mvgen.audio.analyzer.analyze_audio")
    def test_lyrics_aligned_populated(self, mock_analyze, tmp_path):
        mock_analyze.return_value = _make_audio_analysis()

        (tmp_path / "audio.wav").write_bytes(b"")
        _write_lyrics(tmp_path / "lyrics.txt")
        (tmp_path / "assets").mkdir()

        from mvgen.pipeline import run_pipeline

        timeline = run_pipeline(tmp_path, config={"resume": False, "pipeline": {"stages": _NO_PREVIEW_STAGES}})
        assert len(timeline.lyrics_aligned) > 0
