"""VoxKit — Piper TTS voice manager library with interactive TUI."""

from voxkit.manager import VoiceManager
from voxkit.types import BrowserConfig, ProgressCallback, VoiceInfo

__version__ = "0.1.0"

__all__ = [
    "VoiceManager",
    "VoiceInfo",
    "BrowserConfig",
    "ProgressCallback",
    "__version__",
]
