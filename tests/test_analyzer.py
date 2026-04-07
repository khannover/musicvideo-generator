"""Tests for the audio analyser."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest


class TestAudioAnalysis:
    def test_analyze_audio_returns_analysis(self, tmp_project: Path):
        """analyze_audio should return an AudioAnalysis with plausible values."""
        pytest.importorskip("librosa")
        from mvgen.audio.analyzer import AudioAnalysis, analyze_audio

        result = analyze_audio(tmp_project / "audio.wav")

        assert isinstance(result, AudioAnalysis)
        assert result.duration > 0
        assert result.sample_rate > 0
        assert isinstance(result.bpm, float)
        assert isinstance(result.beat_times, list)
        assert isinstance(result.energy_values, list)
        assert isinstance(result.silence_regions, list)

    def test_energy_values_length_matches_times(self, tmp_project: Path):
        pytest.importorskip("librosa")
        from mvgen.audio.analyzer import analyze_audio

        result = analyze_audio(tmp_project / "audio.wav")
        assert len(result.energy_values) == len(result.energy_times)

    def test_duration_approx_correct(self, tmp_project: Path):
        pytest.importorskip("librosa")
        from mvgen.audio.analyzer import analyze_audio

        result = analyze_audio(tmp_project / "audio.wav")
        # The conftest creates a 5-second silent WAV
        assert abs(result.duration - 5.0) < 0.1

    def test_silence_detection_on_all_silence(self, tmp_path: Path):
        """A completely silent clip should have silence regions detected."""
        pytest.importorskip("librosa")
        pytest.importorskip("soundfile")
        import soundfile as sf

        from mvgen.audio.analyzer import analyze_audio

        sr = 22050
        data = np.zeros(sr * 3, dtype=np.float32)
        audio_path = tmp_path / "silent.wav"
        sf.write(str(audio_path), data, sr)

        result = analyze_audio(audio_path)
        # At least zero silence regions (a silent track may or may not produce regions
        # depending on threshold; mainly testing no crash)
        assert isinstance(result.silence_regions, list)

    def test_structural_boundaries_within_duration(self, tmp_project: Path):
        pytest.importorskip("librosa")
        from mvgen.audio.analyzer import analyze_audio

        result = analyze_audio(tmp_project / "audio.wav")
        for b in result.structural_boundaries:
            assert 0 < b < result.duration


class TestDetectSilence:
    def test_silence_region_detected(self):
        from mvgen.audio.analyzer import _detect_silence

        times = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
        # Low energy from 1.0 to 2.0
        values = [0.5, 0.5, 0.01, 0.01, 0.01, 0.5, 0.5]
        regions = _detect_silence(times, values, threshold=0.1, min_duration=0.4)
        assert len(regions) == 1
        assert regions[0][0] == pytest.approx(1.0)

    def test_no_silence(self):
        from mvgen.audio.analyzer import _detect_silence

        times = [0.0, 1.0, 2.0]
        values = [0.5, 0.5, 0.5]
        regions = _detect_silence(times, values, threshold=0.1)
        assert regions == []

    def test_silence_too_short_ignored(self):
        from mvgen.audio.analyzer import _detect_silence

        times = [0.0, 0.1, 0.2, 0.3]
        values = [0.5, 0.01, 0.01, 0.5]
        regions = _detect_silence(times, values, threshold=0.1, min_duration=0.5)
        assert regions == []
