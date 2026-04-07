"""Tests for the importer / ingest module."""

from __future__ import annotations

from pathlib import Path

import pytest

from mvgen.importer.ingest import ingest_project
from mvgen.models.project import Project


class TestIngestProject:
    def test_basic_ingest(self, tmp_project: Path):
        project = ingest_project(tmp_project)
        assert isinstance(project, Project)
        assert project.root_dir == tmp_project
        assert project.audio_path.exists()
        assert project.lyrics_path.exists()
        assert project.output_dir.exists()

    def test_project_name_is_directory_name(self, tmp_project: Path):
        project = ingest_project(tmp_project)
        assert project.name == tmp_project.name

    def test_missing_audio_raises(self, tmp_path: Path):
        (tmp_path / "lyrics.txt").write_text("Hello\n", encoding="utf-8")
        (tmp_path / "assets").mkdir()
        with pytest.raises(FileNotFoundError, match="audio"):
            ingest_project(tmp_path)

    def test_missing_lyrics_raises(self, tmp_path: Path):
        (tmp_path / "audio.wav").write_bytes(b"")
        (tmp_path / "assets").mkdir()
        with pytest.raises(ValueError, match="lyrics"):
            ingest_project(tmp_path)

    def test_cover_art_detected(self, tmp_project: Path):
        cover = tmp_project / "cover.jpg"
        cover.write_bytes(b"fake-jpg")
        project = ingest_project(tmp_project)
        assert project.cover_path == cover

    def test_no_cover_art(self, tmp_project: Path):
        project = ingest_project(tmp_project)
        assert project.cover_path is None

    def test_scene_notes_detected(self, tmp_project: Path):
        notes = tmp_project / "scene_notes.txt"
        notes.write_text("chorus: fast cuts\n", encoding="utf-8")
        project = ingest_project(tmp_project)
        assert project.scene_notes_path == notes

    def test_no_scene_notes(self, tmp_project: Path):
        project = ingest_project(tmp_project)
        assert project.scene_notes_path is None

    def test_assets_dir_created_if_missing(self, tmp_path: Path):
        (tmp_path / "audio.wav").write_bytes(b"")
        (tmp_path / "lyrics.txt").write_text("Line\n", encoding="utf-8")
        project = ingest_project(tmp_path)
        assert project.assets_dir.exists()

    def test_output_dir_created(self, tmp_project: Path):
        project = ingest_project(tmp_project)
        assert project.output_dir.is_dir()

    def test_nonexistent_directory_raises(self):
        with pytest.raises(FileNotFoundError):
            ingest_project(Path("/does/not/exist"))

    def test_timeline_path_property(self, tmp_project: Path):
        project = ingest_project(tmp_project)
        assert project.timeline_path == project.output_dir / "timeline.json"
