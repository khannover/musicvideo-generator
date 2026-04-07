"""CLI entry point for mvgen."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import click

# Configure logging before importing any mvgen module
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stderr,
)


@click.group()
@click.version_option()
def cli() -> None:
    """mvgen — local-first AI music-video assembly pipeline.

    \b
    Typical usage:
        mvgen run ./my_project
        mvgen inspect ./my_project
        mvgen preview ./my_project
        mvgen render ./my_project
        mvgen export-lyrics ./my_project --format srt
    """


@cli.command()
@click.argument("project_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--no-preview", is_flag=True, default=False, help="Skip preview render.")
@click.option("--no-resume", is_flag=True, default=False, help="Re-run all stages even if timeline.json exists.")
def run(project_dir: Path, no_preview: bool, no_resume: bool) -> None:
    """Run the full pipeline for PROJECT_DIR."""
    from mvgen.pipeline import run_pipeline

    config: dict = {"resume": not no_resume}
    if no_preview:
        config.setdefault("pipeline", {})["stages"] = [
            "ingest",
            "audio_analysis",
            "lyric_alignment",
            "structure_detection",
            "scene_planning",
            "prompt_building",
            "asset_matching",
            "lipsync_planning",
        ]
    timeline = run_pipeline(project_dir, config=config)
    click.echo(f"Pipeline complete. {len(timeline.scenes)} scenes, {timeline.duration:.1f}s.")


@cli.command()
@click.argument("project_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
def preview(project_dir: Path) -> None:
    """Render a rough-cut preview from an existing timeline."""
    from mvgen.importer.ingest import ingest_project
    from mvgen.models.timeline import Timeline
    from mvgen.renderer.preview import render_preview

    project = ingest_project(project_dir)
    if not project.timeline_path.exists():
        click.echo("No timeline.json found. Run `mvgen run` first.", err=True)
        sys.exit(1)

    timeline = Timeline.from_json(project.timeline_path.read_text(encoding="utf-8"))
    out = render_preview(timeline, project)
    click.echo(f"Preview rendered: {out}")


@cli.command()
@click.argument("project_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
def render(project_dir: Path) -> None:
    """Render the final video from an existing timeline."""
    from mvgen.importer.ingest import ingest_project
    from mvgen.models.timeline import Timeline
    from mvgen.renderer.final import render_final

    project = ingest_project(project_dir)
    if not project.timeline_path.exists():
        click.echo("No timeline.json found. Run `mvgen run` first.", err=True)
        sys.exit(1)

    timeline = Timeline.from_json(project.timeline_path.read_text(encoding="utf-8"))
    out = render_final(timeline, project)
    click.echo(f"Final render complete: {out}")


@cli.command()
@click.argument("project_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
def inspect(project_dir: Path) -> None:
    """Print a summary of the project timeline to stdout."""
    from mvgen.importer.ingest import ingest_project
    from mvgen.models.timeline import Timeline

    project = ingest_project(project_dir)
    if not project.timeline_path.exists():
        click.echo("No timeline.json found. Run `mvgen run` first.", err=True)
        sys.exit(1)

    timeline = Timeline.from_json(project.timeline_path.read_text(encoding="utf-8"))
    click.echo(f"Project:  {timeline.project_name}")
    click.echo(f"Audio:    {timeline.audio_path}")
    click.echo(f"Duration: {timeline.duration:.1f}s")
    click.echo(f"BPM:      {timeline.bpm}")
    click.echo(f"Scenes:   {len(timeline.scenes)}")
    click.echo("")
    click.echo(f"{'#':<5} {'Section':<20} {'Start':>7} {'End':>7} {'Mood':<15} {'Lip-sync'}")
    click.echo("-" * 70)
    for s in timeline.scenes:
        click.echo(
            f"{s.id:<5} {s.section:<20} {s.start:>7.2f} {s.end:>7.2f} "
            f"{s.mood:<15} {'yes' if s.lip_sync else 'no'}"
        )


@cli.command("export-lyrics")
@click.argument("project_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["srt", "lrc", "json"]),
    default="srt",
    show_default=True,
    help="Output format.",
)
@click.option("--output", "-o", type=click.Path(path_type=Path), default=None, help="Output file path.")
def export_lyrics(project_dir: Path, fmt: str, output: Path | None) -> None:
    """Export aligned lyrics from an existing timeline."""
    from mvgen.importer.ingest import ingest_project
    from mvgen.lyrics.aligner import AlignedLine
    from mvgen.lyrics.formatter import to_json, to_lrc, to_srt
    from mvgen.models.timeline import Timeline

    project = ingest_project(project_dir)
    if not project.timeline_path.exists():
        click.echo("No timeline.json found. Run `mvgen run` first.", err=True)
        sys.exit(1)

    timeline = Timeline.from_json(project.timeline_path.read_text(encoding="utf-8"))
    lines = [
        AlignedLine(
            text=entry.get("text", entry.get("word", "")),
            start=entry["start"],
            end=entry["end"],
            line_index=entry.get("line_index", 0),
        )
        for entry in timeline.lyrics_aligned
    ]

    formatters = {"srt": to_srt, "lrc": to_lrc, "json": to_json}
    content = formatters[fmt](lines)

    if output:
        Path(output).write_text(content, encoding="utf-8")
        click.echo(f"Lyrics exported to {output}")
    else:
        click.echo(content)
