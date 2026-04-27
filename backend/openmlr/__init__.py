"""OpenMLR — AI-powered ML Research Agent."""

from pathlib import Path

_version_file = Path(__file__).resolve().parent.parent.parent / "VERSION"
try:
    __version__ = _version_file.read_text().strip()
except FileNotFoundError:
    __version__ = "0.0.0"
