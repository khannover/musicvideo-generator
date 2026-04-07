"""Audio analysis — extract waveform, BPM, energy, and structural boundaries."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class AudioAnalysis:
    """Results of an audio analysis pass.

    All time values are in **seconds** unless otherwise noted.
    """

    duration: float
    """Total duration of the audio track in seconds."""

    sample_rate: int
    """Sample rate in Hz."""

    bpm: Optional[float] = None
    """Estimated tempo in beats per minute."""

    beat_times: list[float] = field(default_factory=list)
    """Times (seconds) of detected beat onsets."""

    energy_times: list[float] = field(default_factory=list)
    """Time axis for the *energy_values* array."""

    energy_values: list[float] = field(default_factory=list)
    """RMS energy envelope (one value per frame)."""

    silence_regions: list[tuple[float, float]] = field(default_factory=list)
    """List of ``(start, end)`` pairs for detected silence/low-energy regions."""

    structural_boundaries: list[float] = field(default_factory=list)
    """Estimated structural change-points (seconds) from self-similarity analysis."""

    onset_times: list[float] = field(default_factory=list)
    """Onset strength peaks (seconds)."""


def analyze_audio(audio_path: Path) -> AudioAnalysis:
    """Analyse an audio file and return an :class:`AudioAnalysis` result.

    Uses :mod:`librosa` to extract:

    * Duration and sample rate
    * Estimated BPM / beat positions
    * RMS energy envelope
    * Silence / low-energy regions
    * Onset strength peaks
    * Rough structural boundaries via chroma self-similarity

    Parameters
    ----------
    audio_path:
        Path to the audio file (MP3, WAV, FLAC, …).

    Returns
    -------
    AudioAnalysis
        A populated :class:`AudioAnalysis` dataclass.
    """
    try:
        import librosa  # type: ignore[import]
    except ImportError as exc:
        raise ImportError("librosa is required for audio analysis. Install it with: pip install librosa") from exc

    audio_path = Path(audio_path)
    logger.info("Analysing audio: %s", audio_path)

    y, sr = librosa.load(str(audio_path), sr=None, mono=True)
    duration = float(librosa.get_duration(y=y, sr=sr))
    logger.info("Duration: %.2f s, sample rate: %d Hz", duration, sr)

    # ── BPM / beats ──────────────────────────────────────────────────────────
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    bpm = float(np.atleast_1d(tempo)[0])
    beat_times = librosa.frames_to_time(beat_frames, sr=sr).tolist()
    logger.info("Estimated BPM: %.1f, beats detected: %d", bpm, len(beat_times))

    # ── Energy (RMS) ─────────────────────────────────────────────────────────
    hop_length = 512
    rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]
    energy_times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop_length).tolist()
    energy_values = rms.tolist()

    # ── Silence detection ────────────────────────────────────────────────────
    silence_threshold = float(np.percentile(rms, 10))
    silence_regions = _detect_silence(energy_times, energy_values, silence_threshold)
    logger.info("Silence regions detected: %d", len(silence_regions))

    # ── Onset strength ───────────────────────────────────────────────────────
    onset_frames = librosa.onset.onset_detect(y=y, sr=sr, hop_length=hop_length)
    onset_times = librosa.frames_to_time(onset_frames, sr=sr, hop_length=hop_length).tolist()

    # ── Structural boundaries (chroma self-similarity) ───────────────────────
    structural_boundaries = _detect_structural_boundaries(y, sr, duration)
    logger.info("Structural boundaries: %s", structural_boundaries)

    return AudioAnalysis(
        duration=duration,
        sample_rate=int(sr),
        bpm=bpm,
        beat_times=beat_times,
        energy_times=energy_times,
        energy_values=energy_values,
        silence_regions=silence_regions,
        structural_boundaries=structural_boundaries,
        onset_times=onset_times,
    )


# ── Internal helpers ──────────────────────────────────────────────────────────


def _detect_silence(
    times: list[float],
    values: list[float],
    threshold: float,
    min_duration: float = 0.5,
) -> list[tuple[float, float]]:
    """Return silence regions where RMS energy stays below *threshold*."""
    regions: list[tuple[float, float]] = []
    in_silence = False
    start = 0.0

    for t, v in zip(times, values):
        if v < threshold and not in_silence:
            in_silence = True
            start = t
        elif v >= threshold and in_silence:
            in_silence = False
            if t - start >= min_duration:
                regions.append((start, t))

    # Handle silence at the very end
    if in_silence and times[-1] - start >= min_duration:
        regions.append((start, times[-1]))

    return regions


def _detect_structural_boundaries(
    y: "np.ndarray",
    sr: int,
    duration: float,
    n_segments: int = 6,
) -> list[float]:
    """Estimate structural boundaries using chroma self-similarity."""
    try:
        import librosa  # type: ignore[import]
        from scipy.ndimage import gaussian_filter1d  # type: ignore[import]

        hop_length = 2048
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=hop_length)

        # Self-similarity matrix (cosine)
        sim = np.dot(chroma.T, chroma)
        norms = np.linalg.norm(chroma, axis=0)
        norms[norms == 0] = 1e-6
        sim /= np.outer(norms, norms)

        # Novelty curve — diagonal checkerboard kernel
        n = sim.shape[0]
        kernel_size = max(4, n // 20)
        novelty = _checkerboard_novelty(sim, kernel_size)
        novelty = gaussian_filter1d(novelty, sigma=2)

        # Pick top peaks
        from scipy.signal import find_peaks  # type: ignore[import]

        min_dist = max(1, n // (n_segments + 1))
        peaks, _ = find_peaks(novelty, distance=min_dist)

        frame_times = librosa.frames_to_time(peaks, sr=sr, hop_length=hop_length)
        # Keep only boundaries within the actual duration
        boundaries = [float(t) for t in frame_times if 0 < t < duration]
        return sorted(boundaries)[:n_segments]

    except Exception:
        # Fall back to evenly-spaced boundaries
        step = duration / (n_segments + 1)
        return [round(step * i, 2) for i in range(1, n_segments + 1)]


def _checkerboard_novelty(sim: "np.ndarray", k: int) -> "np.ndarray":
    """Compute a novelty curve via a checkerboard kernel applied to *sim*."""
    n = sim.shape[0]
    novelty = np.zeros(n)
    kernel = np.block(
        [
            [np.ones((k, k)), -np.ones((k, k))],
            [-np.ones((k, k)), np.ones((k, k))],
        ]
    )
    for i in range(k, n - k):
        block = sim[i - k : i + k, i - k : i + k]
        if block.shape == kernel.shape:
            novelty[i] = float(np.sum(block * kernel))
    return novelty
