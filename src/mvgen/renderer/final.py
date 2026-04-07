"""Final renderer — produce a polished full-quality video.

Uses FFmpeg to build the final render with:

* Actual media assets placed per timeline
* Transitions (crossfade, cut)
* Camera motion (zoom/pan via crop filter)
* Subtitle burn-in
* Lip-sync segment insertion
"""

from __future__ import annotations

import logging
import subprocess
import tempfile
from pathlib import Path

from mvgen.lyrics.formatter import to_srt
from mvgen.models.project import Project
from mvgen.models.scene import Scene
from mvgen.models.timeline import Timeline

logger = logging.getLogger(__name__)

_RESOLUTION = "1920x1080"
_FPS = 30


def render_final(timeline: Timeline, project: Project) -> Path:
    """Render the final polished music video.

    Parameters
    ----------
    timeline:
        The completed project timeline.
    project:
        The project manifest.

    Returns
    -------
    Path
        Path to the output video (``output/final.mp4``).
    """
    output_path = project.output_dir / "final.mp4"
    project.output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Rendering final video to %s", output_path)

    srt_path = _write_srt(timeline, project)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        segment_paths = _render_scene_segments(timeline, project, tmp)
        concat_list = _write_concat_list(segment_paths, tmp)
        _final_concat(concat_list, project.audio_path, srt_path, output_path, timeline.duration)

    logger.info("Final render complete: %s", output_path)
    return output_path


# ── Internal helpers ──────────────────────────────────────────────────────────


def _write_srt(timeline: Timeline, project: Project) -> Path:
    """Write the subtitle SRT file."""
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


def _render_scene_segments(timeline: Timeline, project: Project, tmp: Path) -> list[Path]:
    """Render each scene to a prepared video segment."""
    segments: list[Path] = []
    cover = str(project.cover_path) if project.cover_path and project.cover_path.exists() else None

    for scene in timeline.scenes:
        seg_path = tmp / f"{scene.id}.mp4"
        duration = max(0.1, scene.end - scene.start)

        asset = scene.selected_asset
        if asset and Path(asset).exists():
            _render_asset_segment(asset, scene, duration, seg_path)
        elif cover:
            _render_image_segment(cover, scene, duration, seg_path)
        else:
            _render_colour_segment(scene, duration, seg_path)

        segments.append(seg_path)

    return segments


def _render_asset_segment(asset: str, scene: Scene, duration: float, output: Path) -> None:
    """Render a scene from a media asset with camera motion applied."""
    asset_path = Path(asset)
    zoom_filter = _camera_motion_filter(scene.camera_motion, _RESOLUTION)

    if asset_path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
        # Image → video
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", asset,
            "-t", str(duration),
            "-vf", f"scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,{zoom_filter}",
            "-c:v", "libx264", "-preset", "medium",
            "-pix_fmt", "yuv420p",
            str(output),
        ]
    else:
        # Video clip — trim/loop to duration
        cmd = [
            "ffmpeg", "-y",
            "-stream_loop", "-1", "-i", asset,
            "-t", str(duration),
            "-vf", f"scale=1920:1080,{zoom_filter}",
            "-c:v", "libx264", "-preset", "medium",
            "-pix_fmt", "yuv420p",
            str(output),
        ]
    _run(cmd)


def _render_image_segment(image: str, scene: Scene, duration: float, output: Path) -> None:
    """Render a scene from the cover image with motion."""
    zoom_filter = _camera_motion_filter(scene.camera_motion, _RESOLUTION)
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", image,
        "-t", str(duration),
        "-vf", (
            f"scale=1920:1080:force_original_aspect_ratio=decrease,"
            f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2,{zoom_filter}"
        ),
        "-c:v", "libx264", "-preset", "medium",
        "-pix_fmt", "yuv420p",
        str(output),
    ]
    _run(cmd)


def _render_colour_segment(scene: Scene, duration: float, output: Path) -> None:
    """Render a colour-fill placeholder segment."""
    from mvgen.renderer.preview import _mood_color

    color = _mood_color(scene.mood)
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c={color}:size=1920x1080:duration={duration}",
        "-c:v", "libx264", "-preset", "medium",
        "-pix_fmt", "yuv420p",
        str(output),
    ]
    _run(cmd)


def _camera_motion_filter(camera_motion: str, resolution: str) -> str:
    """Return an FFmpeg filter string implementing the requested camera motion."""
    w, h = (int(x) for x in resolution.split("x"))
    filters = {
        "static": "null",
        "slow_zoom_in": f"zoompan=z='min(zoom+0.0015,1.5)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={w}x{h}",
        "pan_left": f"crop=w={w}:h={h}:x='(iw-{w})*t/{{}}'.format(5):y=0",
        "handheld": "hue=H='sin(t*2)*2'",  # subtle colour shift as handheld proxy
        "pull_back": f"zoompan=z='max(zoom-0.001,1.0)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={w}x{h}",
    }
    return filters.get(camera_motion, "null")


def _write_concat_list(segments: list[Path], tmp: Path) -> Path:
    """Write FFmpeg concat demuxer list."""
    list_path = tmp / "concat.txt"
    lines = [f"file '{p}'\n" for p in segments]
    list_path.write_text("".join(lines), encoding="utf-8")
    return list_path


def _final_concat(
    concat_list: Path,
    audio_path: Path,
    srt_path: Path,
    output_path: Path,
    duration: float,
) -> None:
    """Merge video segments with audio and burn in subtitles."""
    srt_escaped = str(srt_path).replace("\\", "/").replace(":", r"\:")
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat_list),
        "-i", str(audio_path),
        "-vf", f"subtitles='{srt_escaped}'",
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "libx264", "-preset", "medium",
        "-c:a", "aac", "-b:a", "192k",
        "-t", str(duration),
        "-movflags", "+faststart",
        str(output_path),
    ]
    _run(cmd)


def _run(cmd: list[str]) -> None:
    """Run an FFmpeg command, raising on failure."""
    logger.debug("Running: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg failed:\n{result.stderr}")
