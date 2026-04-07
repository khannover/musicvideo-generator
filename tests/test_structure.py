"""Tests for the structure detector."""

from __future__ import annotations

import pytest

from mvgen.structure.detector import (
    SongSection,
    _block_similarity,
    _parse_lyric_headers,
    detect_structure,
)


class TestParseHeaders:
    def test_verse_chorus_parsed(self):
        text = "[Verse 1]\nLine A\nLine B\n[Chorus]\nHook line"
        sections = _parse_lyric_headers(text)
        assert len(sections) == 2
        labels = [s["label"] for s in sections]
        assert "verse" in labels
        assert "chorus" in labels

    def test_pre_chorus_normalised(self):
        text = "[Pre-Chorus]\nBuilding up"
        sections = _parse_lyric_headers(text)
        assert sections[0]["label"] == "pre_chorus"

    def test_lines_assigned_to_correct_section(self):
        text = "[Verse 1]\nLine A\nLine B\n[Chorus]\nHook"
        sections = _parse_lyric_headers(text)
        verse = next(s for s in sections if s["label"] == "verse")
        assert verse["lines"] == ["Line A", "Line B"]

    def test_no_headers_returns_empty(self):
        text = "Just a line\nAnother line"
        assert _parse_lyric_headers(text) == []


class TestBlockSimilarity:
    def test_identical_blocks_score_one(self):
        a = ["Line one", "Line two"]
        assert _block_similarity(a, a) == pytest.approx(1.0)

    def test_completely_different_blocks_low_score(self):
        a = ["crimson stain across land"]
        b = ["data flows like rivers red"]
        assert _block_similarity(a, b) < 0.5

    def test_repeated_chorus_high_similarity(self):
        chorus = ["Crimson stain across the land", "Written by an unseen hand"]
        score = _block_similarity(chorus, chorus)
        assert score == pytest.approx(1.0)


class TestDetectStructure:
    def test_returns_song_sections(self, sample_audio_analysis, sample_lyrics_text):
        sections = detect_structure(sample_lyrics_text, sample_audio_analysis)
        assert len(sections) > 0
        assert all(isinstance(s, SongSection) for s in sections)

    def test_labels_are_non_empty(self, sample_audio_analysis, sample_lyrics_text):
        sections = detect_structure(sample_lyrics_text, sample_audio_analysis)
        for s in sections:
            assert s.label

    def test_sections_span_full_duration(self, sample_audio_analysis, sample_lyrics_text):
        sections = detect_structure(sample_lyrics_text, sample_audio_analysis)
        assert sections[0].start == pytest.approx(0.0, abs=0.01)
        assert abs(sections[-1].end - sample_audio_analysis.duration) < 1.0

    def test_chorus_label_present(self, sample_audio_analysis, sample_lyrics_text):
        sections = detect_structure(sample_lyrics_text, sample_audio_analysis)
        labels = [s.label for s in sections]
        assert any("chorus" in label for label in labels)

    def test_verse_label_present(self, sample_audio_analysis, sample_lyrics_text):
        sections = detect_structure(sample_lyrics_text, sample_audio_analysis)
        labels = [s.label for s in sections]
        assert any("verse" in label for label in labels)

    def test_no_overlapping_sections(self, sample_audio_analysis, sample_lyrics_text):
        sections = detect_structure(sample_lyrics_text, sample_audio_analysis)
        for i in range(len(sections) - 1):
            assert sections[i].end <= sections[i + 1].start + 1e-6

    def test_section_duration_positive(self, sample_audio_analysis, sample_lyrics_text):
        sections = detect_structure(sample_lyrics_text, sample_audio_analysis)
        for s in sections:
            assert s.duration > 0
