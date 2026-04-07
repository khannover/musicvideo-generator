"""FFmpeg utility wrappers.

All functions call ``subprocess.run`` with proper error handling and raise
``RuntimeError`` on non-zero exit codes.
"""

from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def extract_audio(video_path: Path, output_path: Path) -> Path:
    """Extract the audio stream from *video_path* into *output_path*.

    Parameters
    ----------
    video_path:
        Source video file.
    output_path:
        Destination audio file (format inferred from extension).

    Returns
    -------
    Path
        *output_path* on success.
    """
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vn", "-acodec", "copy",
        str(output_path),
    ]
    _run(cmd)
    return output_path


def concat_clips(clips: list[Path], output_path: Path) -> Path:
    """Concatenate *clips* in order into *output_path*.

    Parameters
    ----------
    clips:
        Ordered list of input clip paths.
    output_path:
        Output file path.

    Returns
    -------
    Path
        *output_path* on success.
    """
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        for clip in clips:
            f.write(f"file '{clip}'\n")
        list_path = f.name

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", list_path,
        "-c", "copy",
        str(output_path),
    ]
    _run(cmd)
    return output_path


def add_subtitle(video_path: Path, srt_path: Path, output_path: Path) -> Path:
    """Burn subtitles from *srt_path* into *video_path*.

    Parameters
    ----------
    video_path:
        Source video.
    srt_path:
        SubRip subtitle file.
    output_path:
        Output video with burned-in subtitles.

    Returns
    -------
    Path
        *output_path* on success.
    """
    srt_escaped = str(srt_path).replace("\\", "/").replace(":", r"\:")
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vf", f"subtitles='{srt_escaped}'",
        "-c:a", "copy",
        str(output_path),
    ]
    _run(cmd)
    return output_path


def apply_zoom(clip_path: Path, zoom_params: dict, output_path: Path) -> Path:
    """Apply a zoom/pan effect to *clip_path*.

    Parameters
    ----------
    clip_path:
        Source video or image clip.
    zoom_params:
        Dictionary with optional keys:

        * ``"zoom_start"`` – initial zoom factor (default ``1.0``)
        * ``"zoom_end"`` – final zoom factor (default ``1.2``)
        * ``"duration"`` – clip duration in seconds
        * ``"resolution"`` – output resolution string, e.g. ``"1920x1080"``
    output_path:
        Output video file.

    Returns
    -------
    Path
        *output_path* on success.
    """
    resolution = zoom_params.get("resolution", "1920x1080")
    w, h = resolution.split("x")
    zoom_start = zoom_params.get("zoom_start", 1.0)
    zoom_end = zoom_params.get("zoom_end", 1.2)
    duration = zoom_params.get("duration", 5.0)
    fps = zoom_params.get("fps", 30)

    # Linear interpolation of zoom via zoompan filter
    zoom_step = (zoom_end - zoom_start) / (duration * fps)
    zoom_expr = f"min({zoom_start}+{zoom_step}*on,{zoom_end})"

    vf = (
        f"zoompan=z='{zoom_expr}':"
        f"x='iw/2-(iw/zoom/2)':"
        f"y='ih/2-(ih/zoom/2)':"
        f"d=1:s={w}x{h}"
    )
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", str(clip_path),
        "-t", str(duration),
        "-vf", vf,
        "-c:v", "libx264", "-preset", "medium",
        "-pix_fmt", "yuv420p",
        str(output_path),
    ]
    _run(cmd)
    return output_path


def crossfade(clip_a: Path, clip_b: Path, duration: float, output_path: Path) -> Path:
    """Create a crossfade transition between *clip_a* and *clip_b*.

    Parameters
    ----------
    clip_a:
        First clip (transition happens at its end).
    clip_b:
        Second clip.
    duration:
        Duration of the crossfade in seconds.
    output_path:
        Output video file.

    Returns
    -------
    Path
        *output_path* on success.
    """
    # Get duration of clip_a to compute offset
    info_a = probe_media(clip_a)
    dur_a = float(info_a.get("duration", 5.0))
    offset = max(0.0, dur_a - duration)

    cmd = [
        "ffmpeg", "-y",
        "-i", str(clip_a),
        "-i", str(clip_b),
        "-filter_complex",
        (
            f"[0:v][1:v]xfade=transition=fade:duration={duration}:offset={offset}[v];"
            f"[0:a][1:a]acrossfade=d={duration}[a]"
        ),
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "medium",
        "-c:a", "aac",
        str(output_path),
    ]
    _run(cmd)
    return output_path


def probe_media(path: Path) -> dict:
    """Return media information for *path* using ``ffprobe``.

    Returns a dictionary with keys such as ``"duration"``, ``"width"``,
    ``"height"``, ``"codec_name"``, etc.

    Parameters
    ----------
    path:
        Media file to probe.

    Returns
    -------
    dict
        Flat dictionary of stream/format metadata.
    """
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed on {path}:\n{result.stderr}")

    data = json.loads(result.stdout)
    info: dict = {}

    # Extract from format
    fmt = data.get("format", {})
    info["duration"] = float(fmt.get("duration", 0))
    info["format_name"] = fmt.get("format_name", "")
    info["size"] = int(fmt.get("size", 0))

    # Extract from first video stream
    for stream in data.get("streams", []):
        if stream.get("codec_type") == "video":
            info["width"] = stream.get("width", 0)
            info["height"] = stream.get("height", 0)
            info["codec_name"] = stream.get("codec_name", "")
            info["fps"] = stream.get("avg_frame_rate", "")
            break

    return info


# ── Internal helpers ──────────────────────────────────────────────────────────


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    """Run *cmd*, raising ``RuntimeError`` on non-zero exit."""
    logger.debug("$ %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed (exit {result.returncode}):\n"
            f"  {' '.join(cmd)}\n"
            f"stderr: {result.stderr}"
        )
    return result
