"""Preview renderer — produce a rough-cut preview video.

Uses FFmpeg to build a low-quality draft:

* Colour bars (or cover art) as visual placeholder for each scene
* Subtitle overlay from aligned lyrics
* Scene label text overlay
* Audio from the master track
"""

from __future__ import annotations

import logging
import subprocess
import tempfile
from pathlib import Path

from mvgen.lyrics.formatter import to_srt
from mvgen.models.project import Project
from mvgen.models.timeline import Timeline

logger = logging.getLogger(__name__)


def render_preview(timeline: Timeline, project: Project) -> Path:
    """Create a rough-cut preview video.

    Parameters
    ----------
    timeline:
        The project timeline.
    project:
        The project manifest (provides paths).

    Returns
    -------
    Path
        Path to the rendered preview video (``output/preview.mp4``).
    """
    output_path = project.output_dir / "preview.mp4"
    project.output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Rendering preview to %s", output_path)

    # Write SRT subtitle file
    srt_path = _write_srt(timeline, project)

    # Build per-scene video segments
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        segment_paths = _render_segments(timeline, project, tmp)
        concat_list = _write_concat_list(segment_paths, tmp)
        _concat_and_mux(concat_list, project.audio_path, srt_path, output_path, timeline.duration)

    logger.info("Preview rendered: %s", output_path)
    return output_path


# ── Internal helpers ──────────────────────────────────────────────────────────


def _write_srt(timeline: Timeline, project: Project) -> Path:
    """Write an SRT subtitle file derived from the timeline's aligned lyrics."""
    from mvgen.lyrics.aligner import AlignedLine

    lines = [
        AlignedLine(
            text=entry.get("word", entry.get("text", "")),
            start=entry["start"],
            end=entry["end"],
            line_index=entry.get("line_index", 0),
        )
        for entry in timeline.lyrics_aligned
    ]
    srt_content = to_srt(lines)
    srt_path = project.output_dir / "subtitles.srt"
    srt_path.write_text(srt_content, encoding="utf-8")
    return srt_path


def _render_segments(timeline: Timeline, project: Project, tmp: Path) -> list[Path]:
    """Render each scene as a short placeholder video segment."""
    segments: list[Path] = []
    cover = str(project.cover_path) if project.cover_path and project.cover_path.exists() else None

    for scene in timeline.scenes:
        seg_path = tmp / f"{scene.id}.mp4"
        duration = max(0.1, scene.end - scene.start)

        label_text = f"{scene.section} | {scene.mood}"
        # Escape FFmpeg drawtext special characters
        label_text = label_text.replace(":", r"\:").replace("'", r"\'")

        if cover:
            video_filter = (
                f"[0:v]scale=1920:1080:force_original_aspect_ratio=decrease,"
                f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2,"
                f"drawtext=text='{label_text}':fontcolor=white:fontsize=48:"
                f"x=(w-text_w)/2:y=50:box=1:boxcolor=black@0.5:boxborderw=8[v]"
            )
            cmd = [
                "ffmpeg", "-y",
                "-loop", "1", "-i", cover,
                "-t", str(duration),
                "-filter_complex", video_filter,
                "-map", "[v]",
                "-c:v", "libx264", "-preset", "ultrafast",
                "-pix_fmt", "yuv420p",
                str(seg_path),
            ]
        else:
            # Colour bars placeholder
            color = _mood_color(scene.mood)
            video_filter = (
                f"color=c={color}:size=1920x1080:duration={duration},"
                f"drawtext=text='{label_text}':fontcolor=white:fontsize=48:"
                f"x=(w-text_w)/2:y=50:box=1:boxcolor=black@0.5:boxborderw=8"
            )
            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", video_filter,
                "-c:v", "libx264", "-preset", "ultrafast",
                "-pix_fmt", "yuv420p",
                str(seg_path),
            ]

        _run(cmd)
        segments.append(seg_path)

    return segments


def _write_concat_list(segments: list[Path], tmp: Path) -> Path:
    """Write an FFmpeg concat demuxer list file."""
    list_path = tmp / "concat.txt"
    lines = [f"file '{p}'\n" for p in segments]
    list_path.write_text("".join(lines), encoding="utf-8")
    return list_path


def _concat_and_mux(
    concat_list: Path,
    audio_path: Path,
    srt_path: Path,
    output_path: Path,
    duration: float,
) -> None:
    """Concatenate video segments, add audio, and burn in subtitles."""
    srt_escaped = str(srt_path).replace("\\", "/").replace(":", r"\:")
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat_list),
        "-i", str(audio_path),
        "-vf", f"subtitles='{srt_escaped}'",
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "libx264", "-preset", "ultrafast",
        "-c:a", "aac",
        "-t", str(duration),
        str(output_path),
    ]
    _run(cmd)


def _mood_color(mood: str) -> str:
    """Return an FFmpeg colour name for a mood."""
    return {
        "dark": "0x1a1a2e",
        "urgent": "0x7b0000",
        "melancholy": "0x1a3a5c",
        "triumphant": "0xb8860b",
        "neutral": "0x2d2d2d",
    }.get(mood, "0x2d2d2d")


def _run(cmd: list[str]) -> None:
    """Run an FFmpeg command, raising on failure."""
    logger.debug("Running: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg failed:\n{result.stderr}")
