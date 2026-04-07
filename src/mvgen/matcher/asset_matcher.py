"""Asset matcher — match media pool files to scenes.

The initial implementation uses filename-keyword heuristics.  The interface
is designed for future embedding-based matching (e.g. CLIP) without changing
call sites.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from mvgen.models.scene import Scene

logger = logging.getLogger(__name__)

_MEDIA_EXTENSIONS = {
    ".mp4", ".mov", ".avi", ".mkv", ".webm",  # video
    ".jpg", ".jpeg", ".png", ".webp", ".gif",  # images
}

_STOPWORDS = {"the", "a", "an", "and", "or", "of", "in", "on", "at", "to", "for", "is", "it"}


def match_assets(scenes: list[Scene], assets_dir: Path) -> list[Scene]:
    """Match media files in *assets_dir* to each scene.

    For each scene the function:

    1. Scans *assets_dir* recursively for supported media files.
    2. Scores each file against the scene's ``mood`` and ``visual_goal`` using
       keyword overlap between the scene description and the filename stem.
    3. Populates ``asset_candidates`` with the top-scoring files.
    4. Sets ``selected_asset`` to the best candidate (if any).

    Parameters
    ----------
    scenes:
        List of :class:`~mvgen.models.scene.Scene` objects to update.
    assets_dir:
        Root of the media asset pool.

    Returns
    -------
    list[Scene]
        The same list with ``asset_candidates`` and ``selected_asset`` set.
    """
    assets_dir = Path(assets_dir)
    all_assets = _scan_assets(assets_dir)

    if not all_assets:
        logger.warning("No media assets found in %s", assets_dir)
        return scenes

    logger.info("Found %d assets in %s", len(all_assets), assets_dir)

    for scene in scenes:
        candidates = _rank_assets(scene, all_assets)
        scene.asset_candidates = [str(p) for p in candidates]
        scene.selected_asset = str(candidates[0]) if candidates else None
        logger.debug(
            "%s → %s (%d candidates)",
            scene.id,
            scene.selected_asset or "none",
            len(candidates),
        )

    return scenes


# ── Internal helpers ──────────────────────────────────────────────────────────


def _scan_assets(assets_dir: Path) -> list[Path]:
    """Return all supported media files under *assets_dir*."""
    if not assets_dir.exists():
        return []
    return [p for p in assets_dir.rglob("*") if p.suffix.lower() in _MEDIA_EXTENSIONS]


def _rank_assets(scene: Scene, assets: list[Path]) -> list[Path]:
    """Return assets sorted by keyword similarity to the scene description."""
    description_tokens = _tokenise(
        f"{scene.mood} {scene.visual_goal} {scene.section} {' '.join(scene.lyrics)}"
    )

    scored: list[tuple[float, Path]] = []
    for asset in assets:
        asset_tokens = _tokenise(asset.stem)
        overlap = len(description_tokens & asset_tokens)
        scored.append((overlap, asset))

    # Sort by score desc, then by filename for determinism
    scored.sort(key=lambda x: (-x[0], x[1].name))
    # Return top 5 candidates (all if score > 0 among them, else any)
    candidates = [p for score, p in scored if score > 0]
    if not candidates:
        candidates = [p for _, p in scored]
    return candidates[:5]


def _tokenise(text: str) -> set[str]:
    """Lowercase, split on non-word chars, remove stopwords."""
    tokens = re.findall(r"[a-z]+", text.lower())
    return {t for t in tokens if len(t) > 2 and t not in _STOPWORDS}
