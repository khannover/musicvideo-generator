"""File I/O and path normalisation utilities."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def ensure_dir(path: Path) -> Path:
    """Create *path* and all parents if they do not exist.

    Parameters
    ----------
    path:
        Directory path to create.

    Returns
    -------
    Path
        The (now existing) directory path.
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_text(path: Path, encoding: str = "utf-8") -> str:
    """Read and return the text content of *path*.

    Parameters
    ----------
    path:
        File to read.
    encoding:
        Text encoding (default UTF-8).

    Returns
    -------
    str
        File contents as a string.
    """
    return Path(path).read_text(encoding=encoding)


def write_text(path: Path, content: str, encoding: str = "utf-8") -> Path:
    """Write *content* to *path*, creating parent directories as needed.

    Parameters
    ----------
    path:
        Destination file path.
    content:
        Text to write.
    encoding:
        Text encoding (default UTF-8).

    Returns
    -------
    Path
        The written file path.
    """
    path = Path(path)
    ensure_dir(path.parent)
    path.write_text(content, encoding=encoding)
    return path


def read_json(path: Path) -> Any:
    """Parse and return JSON from *path*.

    Parameters
    ----------
    path:
        JSON file to read.

    Returns
    -------
    Any
        Parsed JSON value.
    """
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: Path, data: Any, indent: int = 2) -> Path:
    """Serialise *data* as JSON and write to *path*.

    Parameters
    ----------
    path:
        Destination file path.
    data:
        JSON-serialisable object.
    indent:
        Indentation level for pretty-printing.

    Returns
    -------
    Path
        The written file path.
    """
    content = json.dumps(data, indent=indent)
    return write_text(path, content)


def normalise_path(path: Path | str, base: Path | None = None) -> Path:
    """Return an absolute, normalised version of *path*.

    If *path* is relative and *base* is given, it is resolved relative to
    *base*; otherwise it is resolved from the current working directory.

    Parameters
    ----------
    path:
        The path to normalise.
    base:
        Optional base directory for relative paths.

    Returns
    -------
    Path
        Absolute, resolved path.
    """
    p = Path(path)
    if not p.is_absolute() and base is not None:
        p = base / p
    return p.resolve()


def find_files(directory: Path, extensions: set[str]) -> list[Path]:
    """Recursively find files under *directory* matching *extensions*.

    Parameters
    ----------
    directory:
        Root directory to search.
    extensions:
        Set of lowercase extensions to match (e.g. ``{".mp4", ".mov"}``).

    Returns
    -------
    list[Path]
        Sorted list of matching file paths.
    """
    directory = Path(directory)
    if not directory.exists():
        return []
    return sorted(p for p in directory.rglob("*") if p.suffix.lower() in extensions)
