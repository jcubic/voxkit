"""Data types for VoxKit."""

from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class VoiceInfo:
    """Metadata for a single Piper voice model."""

    key: str
    name: str
    language: str
    quality: str
    size_mb: float
    speakers: int
    installed: bool


ProgressCallback = Callable[[str, int, int, int], None]
"""progress_cb(filename, block_num, block_size, total_size)"""


@dataclass
class BrowserConfig:
    """Configuration for the interactive voice browser TUI."""

    lang: str = "en"
    default_voice: Optional[str] = None
    show_size: bool = True
    test_fn: Optional[Callable[[str], None]] = None
    on_install: Optional[Callable[[VoiceInfo], None]] = None
    on_uninstall: Optional[Callable[[VoiceInfo], None]] = None
    keybindings: dict = field(
        default_factory=lambda: {
            "install": "i",
            "uninstall": "u",
            "test": "\r",
            "quit": ("q", "\x03", "\x1b"),
        }
    )
