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
"""VoxKit — Piper TTS voice manager library with interactive TUI."""

from voxkit.manager import VoiceManager
from voxkit.types import BrowserConfig, ProgressCallback, VoiceInfo

__version__ = "0.1.1"

__all__ = [
    "VoiceManager",
    "VoiceInfo",
    "BrowserConfig",
    "ProgressCallback",
    "__version__",
]
