# musicvideo-generator

**Local-first, Dockerized AI music-video assembly pipeline.**

Ingest a song package (audio, lyrics, cover art, media assets), and produce a
**structured timeline JSON** — the canonical project state — plus aligned
lyrics, per-scene generation prompts, and a rendered video.

> **Core principle:** The timeline JSON is the *product*. The render is just
> one output of that product.

---

## Architecture

```
Audio + Lyrics + Cover + Assets
           │
    ┌──────▼──────┐
    │   Importer  │  Load & validate project files
    └──────┬──────┘
           │
    ┌──────▼──────┐
    │   Analyser  │  BPM, energy, structural boundaries (librosa)
    └──────┬──────┘
           │
    ┌──────▼──────┐
    │   Aligner   │  Map lyric lines → timestamps (proportional / Whisper)
    └──────┬──────┘
           │
    ┌──────▼──────────┐
    │ Structure Detect│  Label verse / chorus / bridge / intro / outro
    └──────┬──────────┘
           │
    ┌──────▼──────┐
    │   Planner   │  Sections → Scenes (mood, camera, transitions)
    └──────┬──────┘
           │
    ┌──────▼──────────┐
    │  Prompt Builder │  Per-scene AI generation prompts
    └──────┬──────────┘
           │
    ┌──────▼──────────┐
    │  Asset Matcher  │  Match media pool to scenes (filename / CLIP)
    └──────┬──────────┘
           │
    ┌──────▼──────────┐
    │ Lip-sync Planner│  Assign face clips to performance segments
    └──────┬──────────┘
           │
    ┌──────▼──────┐
    │  timeline   │  ◀── canonical project state (editable JSON)
    │   .json     │
    └──────┬──────┘
           │
    ┌──────▼──────┐
    │  Renderer   │  Preview (rough cut) + Final (FFmpeg composite)
    └─────────────┘
```

---

## Installation

### pip (local development)

```bash
git clone https://github.com/khannover/musicvideo-generator
cd musicvideo-generator
pip install -e .
```

### Docker

```bash
docker compose build
docker compose run --rm mvgen --help
```

---

## Quick Start

```bash
# 1. Prepare your project directory
mkdir -p projects/my_song/assets
cp song.mp3        projects/my_song/audio.mp3
cp lyrics.txt      projects/my_song/lyrics.txt
cp cover.jpg       projects/my_song/cover.jpg
cp footage/*.mp4   projects/my_song/assets/

# 2. Run the full pipeline
mvgen run projects/my_song

# 3. Inspect the timeline
mvgen inspect projects/my_song

# 4. Render preview (requires FFmpeg)
mvgen preview projects/my_song

# 5. Render final video
mvgen render projects/my_song

# 6. Export lyrics
mvgen export-lyrics projects/my_song --format srt
```

---

## Inputs

| File / Directory | Required | Description |
|---|---|---|
| `audio.mp3` / `audio.wav` | Yes | Master audio track |
| `lyrics.txt` | Yes | Plain-text lyrics (section headers optional) |
| `cover.jpg` / `cover.png` | No | Cover art / mood board |
| `assets/` | No | Media pool: images, video clips, B-roll |
| `scene_notes.txt` | No | Human-readable visual intent per section |

---

## Outputs

| File | Description |
|---|---|
| `output/timeline.json` | **Canonical project state** — scenes, timing, prompts, assignments |
| `output/subtitles.srt` | SubRip subtitle file |
| `output/preview.mp4` | Rough-cut preview video |
| `output/final.mp4` | Full-quality render |

---

## Timeline JSON Format

```json
{
  "project_name": "my_song",
  "audio_path": "/path/to/audio.mp3",
  "duration": 214.3,
  "bpm": 128.0,
  "scenes": [
    {
      "id": "scene_001",
      "start": 0.0,
      "end": 18.5,
      "section": "intro",
      "lyrics": [],
      "mood": "neutral",
      "visual_goal": "Establishing wide shot setting the scene atmosphere",
      "asset_candidates": ["assets/wide_city.jpg"],
      "selected_asset": "assets/wide_city.jpg",
      "camera_motion": "slow_zoom_in",
      "transition_in": "fade_from_black",
      "transition_out": "crossfade",
      "lip_sync": false,
      "lip_sync_ref": null,
      "subtitle_mode": "lower_third",
      "generation_prompt": "Establishing wide shot. cinematic dark tones..."
    }
  ],
  "lyrics_aligned": [
    { "text": "Shadows fall", "start": 18.5, "end": 20.1, "line_index": 0 }
  ],
  "metadata": {}
}
```

---

## Module Overview

| Module | File | Responsibility |
|---|---|---|
| Importer | `importer/ingest.py` | Load & validate project files |
| Audio Analyser | `audio/analyzer.py` | BPM, energy, structural boundaries |
| Lyric Aligner | `lyrics/aligner.py` | Map lines to timestamps |
| Lyric Formatter | `lyrics/formatter.py` | Export to SRT / LRC / JSON |
| Structure Detector | `structure/detector.py` | Label verse / chorus / bridge |
| Scene Planner | `planner/scene_planner.py` | Sections → Scenes |
| Prompt Builder | `planner/prompt_builder.py` | Per-scene AI prompts |
| Asset Matcher | `matcher/asset_matcher.py` | Match media pool to scenes |
| Lip-sync Planner | `lipsync/planner.py` | Assign face clips |
| Preview Renderer | `renderer/preview.py` | Rough-cut FFmpeg render |
| Final Renderer | `renderer/final.py` | Full-quality FFmpeg render |
| FFmpeg Utils | `utils/ffmpeg.py` | Subprocess wrappers |
| File Utils | `utils/files.py` | Path normalisation, I/O |
| Pipeline | `pipeline.py` | Orchestrates all stages |
| CLI | `cli.py` | Click commands |

---

## Configuration (`config/default.yaml`)

```yaml
pipeline:
  stages: [ingest, audio_analysis, lyric_alignment, structure_detection,
           scene_planning, prompt_building, asset_matching, lipsync_planning,
           preview_render]

render:
  resolution: "1920x1080"
  fps: 30
  codec: libx264
  preset: medium

alignment:
  method: "proportional"   # proportional | whisper | gentle

matching:
  method: "filename"        # filename | embedding
```

---

## CLI Reference

```
mvgen run <project_dir>                     Run full pipeline
mvgen preview <project_dir>                 Render preview from existing timeline
mvgen render <project_dir>                  Render final video from existing timeline
mvgen inspect <project_dir>                 Print timeline summary
mvgen export-lyrics <project_dir> [--format srt|lrc|json]
```

---

## Development

```bash
# Install dev dependencies
pip install -r requirements.txt && pip install -e .

# Run tests
pytest tests/ --cov=mvgen

# Lint
ruff check src tests

# Or use Make
make test
make lint
```

---

## Docker

```bash
docker compose build
docker compose run --rm mvgen run /data/my_song
```

Mount your projects under `./projects/` — they appear as `/data/` inside the
container.

---

## Roadmap

- [ ] **Whisper alignment** — word-level forced alignment via `whisper-timestamped`
- [ ] **CLIP matching** — embedding-based scene to asset matching
- [ ] **Local video generation** — integrate with AnimateDiff / CogVideoX
- [ ] **Web UI** — browser-based timeline editor and preview player
- [ ] **Multi-model prompts** — LLM-generated scene prompts (Ollama / LM Studio)
- [ ] **Lip-sync generation** — automatic lip-sync with SadTalker / LatentSync
- [ ] **Batch processing** — process multiple projects in parallel
