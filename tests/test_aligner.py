"""Tests for the lyric aligner."""

from __future__ import annotations

import pytest

from mvgen.lyrics.aligner import _extract_lyric_lines, _vocal_segments, align_lyrics


class TestExtractLyricLines:
    def test_strips_headers(self):
        text = "[Verse 1]\nLine one\nLine two\n[Chorus]\nHook line"
        lines = _extract_lyric_lines(text)
        assert lines == ["Line one", "Line two", "Hook line"]

    def test_strips_parenthesised_headers(self):
        text = "(Bridge)\nBridge line"
        lines = _extract_lyric_lines(text)
        assert lines == ["Bridge line"]

    def test_empty_lines_ignored(self):
        text = "Line one\n\nLine two"
        lines = _extract_lyric_lines(text)
        assert lines == ["Line one", "Line two"]

    def test_empty_text(self):
        assert _extract_lyric_lines("") == []


class TestVocalSegments:
    def test_no_silence_returns_full_duration(self, sample_audio_analysis):
        sample_audio_analysis.silence_regions = []
        segs = _vocal_segments(sample_audio_analysis)
        assert segs == [(0.0, sample_audio_analysis.duration)]

    def test_silence_in_middle(self, sample_audio_analysis):
        sample_audio_analysis.silence_regions = [(10.0, 15.0)]
        sample_audio_analysis.duration = 30.0
        segs = _vocal_segments(sample_audio_analysis)
        assert segs == [(0.0, 10.0), (15.0, 30.0)]

    def test_silence_at_start(self, sample_audio_analysis):
        sample_audio_analysis.silence_regions = [(0.0, 5.0)]
        sample_audio_analysis.duration = 30.0
        segs = _vocal_segments(sample_audio_analysis)
        assert segs[0][0] == pytest.approx(5.0)


class TestAlignLyrics:
    def test_returns_correct_count(self, sample_audio_analysis, tmp_path):
        """Number of AlignedLines equals number of non-header lyric lines."""
        lyrics = "[Verse 1]\nLine one\nLine two\n[Chorus]\nHook line\nHook two"
        audio_path = tmp_path / "audio.wav"
        audio_path.write_bytes(b"")

        result = align_lyrics(audio_path, lyrics, audio_analysis=sample_audio_analysis)
        # 4 non-header lines
        assert len(result) == 4

    def test_lines_distributed_evenly(self, sample_audio_analysis, tmp_path):
        """Lines should span the full vocal duration without large gaps."""
        lyrics = "\n".join(f"Line {i}" for i in range(10))
        audio_path = tmp_path / "audio.wav"
        audio_path.write_bytes(b"")

        sample_audio_analysis.silence_regions = []
        result = align_lyrics(audio_path, lyrics, audio_analysis=sample_audio_analysis)

        durations = [line.end - line.start for line in result]
        # All durations should be approximately equal
        assert max(durations) - min(durations) < 0.01

    def test_first_line_starts_at_zero(self, sample_audio_analysis, tmp_path):
        lyrics = "Line one\nLine two\nLine three"
        audio_path = tmp_path / "audio.wav"
        audio_path.write_bytes(b"")
        sample_audio_analysis.silence_regions = []

        result = align_lyrics(audio_path, lyrics, audio_analysis=sample_audio_analysis)
        assert result[0].start == pytest.approx(0.0)

    def test_last_line_ends_at_duration(self, sample_audio_analysis, tmp_path):
        lyrics = "Line one\nLine two"
        audio_path = tmp_path / "audio.wav"
        audio_path.write_bytes(b"")
        sample_audio_analysis.silence_regions = []
        sample_audio_analysis.duration = 10.0

        result = align_lyrics(audio_path, lyrics, audio_analysis=sample_audio_analysis)
        assert result[-1].end == pytest.approx(10.0)

    def test_empty_lyrics_returns_empty(self, sample_audio_analysis, tmp_path):
        audio_path = tmp_path / "audio.wav"
        audio_path.write_bytes(b"")
        result = align_lyrics(audio_path, "", audio_analysis=sample_audio_analysis)
        assert result == []

    def test_line_indices_sequential(self, sample_audio_analysis, tmp_path):
        lyrics = "A\nB\nC\nD"
        audio_path = tmp_path / "audio.wav"
        audio_path.write_bytes(b"")
        sample_audio_analysis.silence_regions = []

        result = align_lyrics(audio_path, lyrics, audio_analysis=sample_audio_analysis)
        assert [line.line_index for line in result] == [0, 1, 2, 3]

    def test_no_overlap_between_lines(self, sample_audio_analysis, tmp_path):
        lyrics = "\n".join(f"Line {i}" for i in range(8))
        audio_path = tmp_path / "audio.wav"
        audio_path.write_bytes(b"")
        sample_audio_analysis.silence_regions = []

        result = align_lyrics(audio_path, lyrics, audio_analysis=sample_audio_analysis)
        for i in range(len(result) - 1):
            assert result[i].end <= result[i + 1].start + 1e-6
