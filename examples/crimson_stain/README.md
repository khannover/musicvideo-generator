# Crimson Stain — Example Project

This directory contains a sample project for the `mvgen` pipeline.

## Required files (not included)

Place the following files here before running:

| File | Description |
|---|---|
| `audio.mp3` | Master audio track (MP3 or WAV) |
| `cover.jpg` | Cover art or mood board image |
| `assets/` | Your media pool: images, video clips, B-roll |

## Quick start

```bash
# Install mvgen
pip install -e /path/to/musicvideo-generator

# Run the full pipeline
mvgen run examples/crimson_stain

# Inspect the resulting timeline
mvgen inspect examples/crimson_stain

# Export lyrics as SRT
mvgen export-lyrics examples/crimson_stain --format srt

# Render preview (requires FFmpeg)
mvgen preview examples/crimson_stain
```

## What's included

- `lyrics.txt` — Full lyrics for "Crimson Stain" with section headers
- `scene_notes.txt` — Human-readable visual intent per section
- `assets/.gitkeep` — Placeholder for your media pool

## Song structure

| Section | Description |
|---|---|
| Verse 1 | Dark establishing shots, ruined cityscape |
| Pre-Chorus | Tension building, character KAI close-up |
| Chorus | Montage of destruction, crimson overlays |
| Verse 2 | Screen collages, data visualisation |
| Pre-Chorus | Tension reprise |
| Chorus | Second montage |
| Bridge | Quieter moment, hopeful tone |
| Final Chorus | Full intensity, KAI to camera |
