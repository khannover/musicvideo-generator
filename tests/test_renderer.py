"""Tests for the renderer modules (preview and final).

External subprocess calls to FFmpeg are mocked so the tests can run without
FFmpeg installed.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from mvgen.models.project import Project
from mvgen.models.scene import Scene
from mvgen.models.timeline import Timeline


def _make_timeline(tmp_path: Path) -> Timeline:
    scenes = [
        Scene(
            id="scene_001",
            start=0.0,
            end=5.0,
            section="verse_1",
            mood="dark",
            lyrics=["Line one"],
        ),
        Scene(
            id="scene_002",
            start=5.0,
            end=10.0,
            section="chorus_1",
            mood="triumphant",
            lip_sync=True,
        ),
    ]
    return Timeline(
        project_name="test",
        audio_path=str(tmp_path / "audio.wav"),
        duration=10.0,
        bpm=120.0,
        scenes=scenes,
        lyrics_aligned=[
            {"text": "Line one", "start": 0.5, "end": 1.5, "line_index": 0}
        ],
    )


def _make_project(tmp_path: Path) -> Project:
    (tmp_path / "audio.wav").write_bytes(b"")
    (tmp_path / "lyrics.txt").write_text("Line one\n", encoding="utf-8")
    (tmp_path / "assets").mkdir(exist_ok=True)
    output_dir = tmp_path / "output"
    output_dir.mkdir(exist_ok=True)
    return Project(
        name="test",
        root_dir=tmp_path,
        audio_path=tmp_path / "audio.wav",
        lyrics_path=tmp_path / "lyrics.txt",
        assets_dir=tmp_path / "assets",
        output_dir=output_dir,
    )


class TestPreviewRenderer:
    @patch("mvgen.renderer.preview._run")
    def test_render_preview_calls_ffmpeg(self, mock_run, tmp_path):
        """render_preview should make FFmpeg calls without raising."""
        timeline = _make_timeline(tmp_path)
        project = _make_project(tmp_path)
        mock_run.return_value = None

        from mvgen.renderer.preview import render_preview

        result = render_preview(timeline, project)
        assert mock_run.called
        assert result == project.output_dir / "preview.mp4"

    @patch("mvgen.renderer.preview._run")
    def test_srt_file_written(self, mock_run, tmp_path):
        """render_preview should write a subtitles.srt file."""
        mock_run.return_value = None
        timeline = _make_timeline(tmp_path)
        project = _make_project(tmp_path)

        from mvgen.renderer.preview import render_preview

        render_preview(timeline, project)
        srt_path = project.output_dir / "subtitles.srt"
        assert srt_path.exists()


class TestFinalRenderer:
    @patch("mvgen.renderer.final._run")
    def test_render_final_calls_ffmpeg(self, mock_run, tmp_path):
        mock_run.return_value = None
        timeline = _make_timeline(tmp_path)
        project = _make_project(tmp_path)

        from mvgen.renderer.final import render_final

        result = render_final(timeline, project)
        assert mock_run.called
        assert result == project.output_dir / "final.mp4"

    @patch("mvgen.renderer.final._run")
    def test_srt_file_written(self, mock_run, tmp_path):
        mock_run.return_value = None
        timeline = _make_timeline(tmp_path)
        project = _make_project(tmp_path)

        from mvgen.renderer.final import render_final

        render_final(timeline, project)
        assert (project.output_dir / "subtitles.srt").exists()


class TestMoodColor:
    def test_known_moods_return_hex(self):
        from mvgen.renderer.preview import _mood_color

        assert _mood_color("dark").startswith("0x")
        assert _mood_color("urgent").startswith("0x")

    def test_unknown_mood_returns_default(self):
        from mvgen.renderer.preview import _mood_color

        result = _mood_color("nonexistent_mood")
        assert result.startswith("0x")
