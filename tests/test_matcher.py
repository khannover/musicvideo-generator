"""Tests for the asset matcher."""

from __future__ import annotations

from pathlib import Path

from mvgen.matcher.asset_matcher import _scan_assets, _tokenise, match_assets
from mvgen.models.scene import Scene


def _make_scene(section: str = "verse_1", mood: str = "dark", visual_goal: str = "ruined city") -> Scene:
    return Scene(id="scene_001", start=0.0, end=5.0, section=section, mood=mood, visual_goal=visual_goal)


class TestScanAssets:
    def test_finds_image_files(self, tmp_path: Path):
        (tmp_path / "photo.jpg").write_bytes(b"")
        (tmp_path / "art.png").write_bytes(b"")
        (tmp_path / "readme.txt").write_text("ignore me", encoding="utf-8")

        result = _scan_assets(tmp_path)
        names = {p.name for p in result}
        assert "photo.jpg" in names
        assert "art.png" in names
        assert "readme.txt" not in names

    def test_finds_video_files(self, tmp_path: Path):
        (tmp_path / "clip.mp4").write_bytes(b"")
        result = _scan_assets(tmp_path)
        assert any(p.name == "clip.mp4" for p in result)

    def test_nonexistent_dir_returns_empty(self):
        assert _scan_assets(Path("/no/such/dir")) == []

    def test_recursive_search(self, tmp_path: Path):
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "nested.jpg").write_bytes(b"")
        result = _scan_assets(tmp_path)
        assert any(p.name == "nested.jpg" for p in result)


class TestTokenise:
    def test_lowercases_and_splits(self):
        assert "city" in _tokenise("ruined_CITY")

    def test_removes_stopwords(self):
        tokens = _tokenise("the ruined city of war")
        assert "the" not in tokens
        assert "of" not in tokens
        assert "city" in tokens

    def test_short_tokens_removed(self):
        tokens = _tokenise("a an on it")
        assert tokens == set()


class TestMatchAssets:
    def test_empty_assets_dir_returns_scenes_unchanged(self, tmp_path: Path):
        scene = _make_scene()
        result = match_assets([scene], tmp_path / "empty")
        assert result[0].selected_asset is None
        assert result[0].asset_candidates == []

    def test_keyword_match_selects_correct_asset(self, tmp_path: Path):
        # Create assets with matching / non-matching filenames
        (tmp_path / "dark_city_ruins.jpg").write_bytes(b"")
        (tmp_path / "happy_flowers.jpg").write_bytes(b"")

        scene = _make_scene(mood="dark", visual_goal="ruined city")
        result = match_assets([scene], tmp_path)

        # Best candidate should relate to "dark city"
        assert result[0].selected_asset is not None
        assert "dark" in result[0].selected_asset or "city" in result[0].selected_asset or "ruins" in result[0].selected_asset

    def test_asset_candidates_populated(self, tmp_path: Path):
        (tmp_path / "asset1.jpg").write_bytes(b"")
        (tmp_path / "asset2.mp4").write_bytes(b"")

        scene = _make_scene()
        result = match_assets([scene], tmp_path)
        assert len(result[0].asset_candidates) > 0

    def test_multiple_scenes(self, tmp_path: Path):
        (tmp_path / "chorus_fire.jpg").write_bytes(b"")
        (tmp_path / "verse_dark.jpg").write_bytes(b"")

        scenes = [
            _make_scene(section="verse_1", mood="dark", visual_goal="dark shadow"),
            _make_scene(section="chorus_1", mood="triumphant", visual_goal="fire chorus"),
        ]
        scenes[1].id = "scene_002"
        result = match_assets(scenes, tmp_path)
        assert len(result) == 2
