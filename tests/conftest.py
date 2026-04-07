"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest


@pytest.fixture()
def sample_lyrics_text() -> str:
    return """\
[Verse 1]
Shadows fall across the wasted ground
Echoes of a war that made no sound

[Chorus]
Crimson stain across the land
Written by an unseen hand

[Verse 2]
Screens light up with curated despair
Algorithms choose how much we care

[Chorus]
Crimson stain across the land
Written by an unseen hand

[Bridge]
In the wreckage there's a frequency
A signal underneath the noise
"""


@pytest.fixture()
def sample_audio_analysis():
    """Return a minimal AudioAnalysis built from synthetic data."""
    from mvgen.audio.analyzer import AudioAnalysis

    duration = 30.0
    sr = 22050
    n_frames = 100
    times = [i * duration / n_frames for i in range(n_frames)]
    values = [0.1 + 0.05 * np.sin(i * 0.3) for i in range(n_frames)]

    return AudioAnalysis(
        duration=duration,
        sample_rate=sr,
        bpm=120.0,
        beat_times=[0.5 * i for i in range(60)],
        energy_times=times,
        energy_values=values,
        silence_regions=[],
        structural_boundaries=[6.0, 12.0, 18.0, 24.0],
        onset_times=[0.5 * i for i in range(60)],
    )


@pytest.fixture()
def tmp_project(tmp_path: Path) -> Path:
    """Create a minimal project directory with required files."""
    # Audio placeholder (1 second of silence as WAV)
    audio_path = tmp_path / "audio.wav"
    _write_silent_wav(audio_path, duration_s=5.0)

    # Lyrics
    lyrics = """\
[Verse 1]
First line of the verse
Second line of the verse

[Chorus]
Hook line one
Hook line two
"""
    (tmp_path / "lyrics.txt").write_text(lyrics, encoding="utf-8")

    # Assets directory
    (tmp_path / "assets").mkdir()

    return tmp_path


def _write_silent_wav(path: Path, duration_s: float = 1.0, sr: int = 22050) -> None:
    """Write a silent mono WAV file to *path*."""
    try:
        import soundfile as sf

        data = np.zeros(int(sr * duration_s), dtype=np.float32)
        sf.write(str(path), data, sr)
    except ImportError:
        # If soundfile is not available, write a minimal valid WAV header
        n_samples = int(sr * duration_s)
        _write_minimal_wav(path, n_samples, sr)


def _write_minimal_wav(path: Path, n_samples: int, sr: int) -> None:
    """Write a minimal valid PCM WAV file."""
    import struct

    n_channels = 1
    bits = 16
    byte_rate = sr * n_channels * bits // 8
    block_align = n_channels * bits // 8
    data_size = n_samples * block_align
    chunk_size = 36 + data_size

    with open(path, "wb") as f:
        f.write(b"RIFF")
        f.write(struct.pack("<I", chunk_size))
        f.write(b"WAVE")
        f.write(b"fmt ")
        f.write(struct.pack("<I", 16))
        f.write(struct.pack("<H", 1))  # PCM
        f.write(struct.pack("<H", n_channels))
        f.write(struct.pack("<I", sr))
        f.write(struct.pack("<I", byte_rate))
        f.write(struct.pack("<H", block_align))
        f.write(struct.pack("<H", bits))
        f.write(b"data")
        f.write(struct.pack("<I", data_size))
        f.write(b"\x00" * data_size)
