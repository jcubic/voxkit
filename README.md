# VoxKit

[![PyPI version](https://img.shields.io/pypi/v/voxkit.svg)](https://pypi.org/project/voxkit/)
[![License: GPL v3+](https://img.shields.io/badge/License-GPLv3+-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

A Python library for managing [Piper](https://github.com/rhasspy/piper) TTS voice models. Browse, install, and use offline AI voices with a clean API and an interactive terminal UI.

## Features

- **Voice catalog** — list, search, and filter Piper voices by language or locale
- **Install/uninstall** — download voice models to any directory you choose
- **TTS synthesis** — synthesize text to WAV files with volume control
- **Interactive TUI** — terminal-based voice browser with install, uninstall, and test
- **Configurable** — custom data directories, catalog URLs, cache TTL, and TUI keybindings
- **Offline** — all synthesis runs locally, no internet needed after voice download

## Requirements

- Python 3.10+
- Linux (uses `aplay` for WAV playback, `mpg123` for MP3)
- [Piper TTS](https://github.com/rhasspy/piper) (installed automatically as dependency)

## Installation

```bash
pip install voxkit
```

## Quick Start

```python
from voxkit import VoiceManager

# Initialize with your app's storage directory
vm = VoiceManager(data_dir="~/.myapp/voices")

# List available English voices
voices = vm.list_voices("en")
for v in voices:
    print(f"{v['key']}  {v['quality']}  {v['size_mb']:.0f} MB  {'[installed]' if v['installed'] else ''}")

# Install a voice
vm.install("en_US-lessac-medium")

# Synthesize and play text
vm.speak("en_US-lessac-medium", "Hello, world!")
```

## API Reference

### VoiceManager

```python
VoiceManager(
    data_dir,             # Directory for models and cache
    catalog_url=None,     # Override Piper catalog URL
    base_url=None,        # Override download base URL
    cache_ttl=86400,      # Catalog cache TTL in seconds (default: 24h)
)
```

#### Catalog

```python
vm.list_languages()                # -> ['en', 'pl', 'de', ...]
vm.get_language_name("en")         # -> 'English'
vm.list_voices("en")               # all English variants
vm.list_voices("en_US")            # US English only
vm.get_voice("en_US-lessac-medium") # single voice info or None
```

The `lang` parameter accepts both 2-letter codes (`"en"`) to match all regional variants
and full locale strings (`"en_US"`) for exact matching.

#### Install & Manage

```python
vm.install("en_US-lessac-medium", progress_cb=None)
vm.uninstall("en_US-lessac-medium")  # -> True if removed
vm.is_installed("en_US-lessac-medium") # -> bool
vm.get_path("en_US-lessac-medium")   # -> Path or None
```

The `progress_cb` receives `(filename, block_num, block_size, total_size)` during download.

#### Resolve

```python
# Find best installed voice for a language
path = vm.resolve(lang="en")

# Use a specific voice (auto-downloads if missing)
path = vm.resolve(voice="en_US-lessac-medium")

# Prefer exact locale, fall back to any match
path = vm.resolve(lang="en_US")
```

#### TTS Synthesis

```python
# Synthesize to WAV file
wav_path = vm.synthesize("en_US-lessac-medium", "Hello!")
wav_path = vm.synthesize("en_US-lessac-medium", "Hello!", output_path="out.wav")

# Multiple texts with pauses
wav_path = vm.synthesize_multi("en_US-lessac-medium", ["Hello.", "World."], pause_ms=700)

# Synthesize and play immediately
vm.speak("en_US-lessac-medium", "Hello, world!")

# Volume control
vm.set_volume(75)
```

#### Voice Loading

```python
# Load a PiperVoice instance for direct use
voice = vm.load_voice("en_US-lessac-medium")
```

#### Language Detection

```python
# Detect language from system locale
lang = VoiceManager.detect_language()  # -> 'en_US' or 'pl_PL' etc.
```

### Interactive TUI

```python
# Basic usage — browse English voices
vm.browse(lang="en")

# With configuration
from voxkit import BrowserConfig

config = BrowserConfig(
    lang="pl",
    default_voice="pl_PL-darkman-medium",
    show_size=True,
    test_fn=lambda key: vm.speak(key, "Dzień dobry"),
    on_install=lambda v: print(f"Installed {v['key']}"),
)
vm.browse(config=config)
```

The TUI supports:
- **Arrow keys** — navigate the voice list
- **Enter** — test the selected voice (auto-installs if needed)
- **i** — install the selected voice
- **u** — uninstall the selected voice
- **q** / Esc / Ctrl-C — quit

Keybindings are configurable via `BrowserConfig.keybindings`.

### Built-in Progress Bar

VoxKit includes a ready-made terminal progress bar for downloads:

```python
from voxkit.browser import progress_bar

vm.install("en_US-lessac-medium", progress_cb=progress_bar)
```

### Data Types

```python
from voxkit import VoiceInfo, BrowserConfig, ProgressCallback
```

#### VoiceInfo

Returned by `list_voices()` and `get_voice()` as a dict with keys:
`key`, `name`, `language`, `quality`, `region`, `speakers`, `size_mb`, `installed`.

#### BrowserConfig

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `lang` | `str` | `"en"` | Language to browse |
| `default_voice` | `str \| None` | `None` | Mark as default in the list |
| `show_size` | `bool` | `True` | Show download size column |
| `test_fn` | `Callable \| None` | `None` | Custom test function `(voice_key) -> None` |
| `on_install` | `Callable \| None` | `None` | Hook called after install `(voice_info) -> None` |
| `on_uninstall` | `Callable \| None` | `None` | Hook called after uninstall `(voice_info) -> None` |
| `keybindings` | `dict` | see below | Custom key mappings |

Default keybindings:
```python
{
    "install": "i",
    "uninstall": "u",
    "test": "\r",
    "quit": ("q", "\x03", "\x1b"),
}
```

## Storage Layout

```
<data_dir>/
├── models/          # Downloaded .onnx voice models
│   ├── <voice>.onnx
│   └── <voice>.onnx.json
└── cache/
    └── voices.json  # Cached Piper catalog (auto-refreshed)
```

## License

Copyright (c) 2026 [Jakub T. Jankiewicz](https://jakub.jankiewicz.org/)

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

See [LICENSE](https://github.com/jcubic/voxkit/blob/master/LICENSE) for the full text.
