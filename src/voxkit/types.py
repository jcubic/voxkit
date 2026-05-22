# Copyright (C) 2026 Jakub T. Jankiewicz <https://jakub.jankiewicz.org/>
#
# This file is part of VoxKit.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
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
