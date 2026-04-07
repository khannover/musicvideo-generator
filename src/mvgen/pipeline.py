"""Pipeline orchestrator — run all stages in order."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import yaml

from mvgen.models.timeline import Timeline

logger = logging.getLogger(__name__)

_DEFAULT_CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "default.yaml"


def run_pipeline(project_dir: Path, config: Optional[dict] = None) -> Timeline:
    """Execute the full music-video pipeline.

    Stages (in order):

    1. **Ingest** — load audio, lyrics, cover, assets.
    2. **Audio analysis** — BPM, energy, structural boundaries.
    3. **Lyric alignment** — map lines to timestamps.
    4. **Structure detection** — label verse/chorus/bridge etc.
    5. **Scene planning** — one scene per section.
    6. **Prompt building** — generate AI prompts per scene.
    7. **Asset matching** — pick media files for each scene.
    8. **Lip-sync planning** — assign face clips.
    9. **Save timeline JSON** — write canonical project state.
    10. **Preview render** *(optional)* — rough-cut video.

    If a ``timeline.json`` already exists in the output directory, the
    pipeline offers to load it and skip already-completed stages (controlled
    via ``config["resume"]``).

    Parameters
    ----------
    project_dir:
        Root directory of the project.
    config:
        Optional configuration dictionary.  Merged with the default config.

    Returns
    -------
    Timeline
        The completed :class:`~mvgen.models.timeline.Timeline`.
    """
    cfg = _load_config(config)
    stages = cfg.get("pipeline", {}).get("stages", _default_stages())
    do_preview = "preview_render" in stages

    project_dir = Path(project_dir).resolve()

    # ── Stage 1: Ingest ───────────────────────────────────────────────────────
    logger.info("[1/9] Ingesting project from %s", project_dir)
    from mvgen.importer.ingest import ingest_project

    project = ingest_project(project_dir)

    # ── Resume check ─────────────────────────────────────────────────────────
    timeline_path = project.timeline_path
    if timeline_path.exists() and cfg.get("resume", True):
        logger.info("Existing timeline found at %s — loading for resume", timeline_path)
        timeline = Timeline.from_json(timeline_path.read_text(encoding="utf-8"))
        project.timeline = timeline
    else:
        # ── Stage 2: Audio analysis ───────────────────────────────────────────
        logger.info("[2/9] Analysing audio")
        from mvgen.audio.analyzer import analyze_audio

        audio_analysis = analyze_audio(project.audio_path)

        # ── Stage 3: Lyric alignment ──────────────────────────────────────────
        logger.info("[3/9] Aligning lyrics")
        from mvgen.lyrics.aligner import align_lyrics

        lyrics_text = project.lyrics_path.read_text(encoding="utf-8")
        aligned_lyrics = align_lyrics(project.audio_path, lyrics_text, audio_analysis)

        # ── Stage 4: Structure detection ──────────────────────────────────────
        logger.info("[4/9] Detecting song structure")
        from mvgen.structure.detector import detect_structure

        sections = detect_structure(lyrics_text, audio_analysis)

        # ── Stage 5: Scene planning ───────────────────────────────────────────
        logger.info("[5/9] Planning scenes")
        from mvgen.planner.scene_planner import plan_scenes

        scenes = plan_scenes(sections, aligned_lyrics, audio_analysis)

        # ── Stage 6: Prompt building ──────────────────────────────────────────
        logger.info("[6/9] Building generation prompts")
        from mvgen.planner.prompt_builder import build_prompts

        scenes = build_prompts(scenes)

        # ── Stage 7: Asset matching ───────────────────────────────────────────
        logger.info("[7/9] Matching assets")
        from mvgen.matcher.asset_matcher import match_assets

        scenes = match_assets(scenes, project.assets_dir)

        # ── Stage 8: Lip-sync planning ────────────────────────────────────────
        logger.info("[8/9] Planning lip-sync")
        from mvgen.lipsync.planner import plan_lipsync

        scenes = plan_lipsync(scenes, project.assets_dir)

        # Build lyrics_aligned list from AlignedLine objects
        lyrics_aligned = [
            {
                "text": line.text,
                "start": line.start,
                "end": line.end,
                "line_index": line.line_index,
            }
            for line in aligned_lyrics
        ]

        timeline = Timeline(
            project_name=project.name,
            audio_path=str(project.audio_path),
            duration=audio_analysis.duration,
            bpm=audio_analysis.bpm,
            scenes=scenes,
            lyrics_aligned=lyrics_aligned,
            metadata={
                "sample_rate": audio_analysis.sample_rate,
                "beat_count": len(audio_analysis.beat_times),
                "silence_regions": audio_analysis.silence_regions,
            },
        )

        # ── Stage 9: Save timeline ────────────────────────────────────────────
        logger.info("[9/9] Saving timeline to %s", timeline_path)
        timeline_path.write_text(timeline.to_json(), encoding="utf-8")
        project.timeline = timeline

    # ── Stage 10: Preview render (optional) ───────────────────────────────────
    if do_preview:
        logger.info("[10] Rendering preview")
        from mvgen.renderer.preview import render_preview

        render_preview(timeline, project)

    return timeline


# ── Helpers ───────────────────────────────────────────────────────────────────


def _load_config(override: Optional[dict]) -> dict:
    """Merge default config with *override*."""
    cfg: dict = {}
    if _DEFAULT_CONFIG_PATH.exists():
        with _DEFAULT_CONFIG_PATH.open(encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
    if override:
        _deep_merge(cfg, override)
    return cfg


def _deep_merge(base: dict, override: dict) -> None:
    """Recursively merge *override* into *base* in-place."""
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


def _default_stages() -> list[str]:
    return [
        "ingest",
        "audio_analysis",
        "lyric_alignment",
        "structure_detection",
        "scene_planning",
        "prompt_building",
        "asset_matching",
        "lipsync_planning",
    ]
