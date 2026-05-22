# Copyright (C) 2026 Jakub T. Jankiewicz <https://jakub.jankiewicz.org/>
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
"""VoiceManager — main entry point for voxkit."""

import glob
import locale
import os
import urllib.request

from voxkit.catalog import VoiceCatalog
from voxkit.tts import play_wav, scale_volume, synthesize, synthesize_multi
from voxkit.types import BrowserConfig


class VoiceManager:
    """Manage Piper TTS voice models: catalog, install, synthesize, and browse.

    Args:
        data_dir: Directory for voices and cache (e.g. '~/.myapp/voices').
            Subdirectories 'models/' and 'cache/' are created automatically.
        catalog_url: Override the Piper voices catalog URL.
        base_url: Override the Piper voices download base URL.
        cache_ttl: Catalog cache TTL in seconds (default 86400 = 24h).
    """

    def __init__(self, data_dir, catalog_url=None, base_url=None, cache_ttl=86400):
        self._data_dir = os.path.expanduser(data_dir)
        self._voices_dir = os.path.join(self._data_dir, "models")
        self._cache_dir = os.path.join(self._data_dir, "cache")
        os.makedirs(self._voices_dir, exist_ok=True)
        os.makedirs(self._cache_dir, exist_ok=True)
        self._catalog = VoiceCatalog(
            self._cache_dir, self._voices_dir, catalog_url, base_url, cache_ttl
        )
        self._volume = 100

    @property
    def data_dir(self):
        """The root data directory."""
        return self._data_dir

    @property
    def voices_dir(self):
        """Directory where voice model files are stored."""
        return self._voices_dir

    def set_volume(self, volume):
        """Set the playback volume (0-100)."""
        if not 0 <= volume <= 100:
            raise ValueError(f"volume must be 0-100, got {volume}")
        self._volume = volume

    @property
    def volume(self):
        return self._volume

    def list_languages(self):
        """Return sorted list of available language codes."""
        return self._catalog.list_languages()

    def get_language_name(self, lang):
        """Return the English name for a language code."""
        return self._catalog.get_language_name(lang)

    def list_voices(self, lang):
        """List available voices for a language.

        Args:
            lang: Language code — 'en' for all English variants,
                  'en_US' for US English only.

        Returns:
            List of dicts with keys: key, name, language, quality,
            region, speakers, size_mb, installed.
        """
        return self._catalog.list_voices(lang)

    def get_voice(self, voice_key):
        """Get info for a specific voice, or None if not in catalog."""
        catalog = self._catalog.get()
        info = catalog.get(voice_key)
        if info is None:
            return None
        size_bytes = sum(
            f.get("size_bytes", 0) for f in info.get("files", {}).values() if f.get("size_bytes")
        )
        lang_info = info.get("language", {})
        return {
            "key": voice_key,
            "name": info.get("name", ""),
            "language": f"{lang_info.get('family', '')}_{lang_info.get('code', '')}",
            "quality": info.get("quality", ""),
            "region": lang_info.get("country_english", ""),
            "speakers": info.get("num_speakers", 1),
            "size_mb": size_bytes / (1024 * 1024),
            "installed": self.is_installed(voice_key),
        }

    def is_installed(self, voice_key):
        """Check if a voice model is installed locally."""
        return os.path.exists(os.path.join(self._voices_dir, f"{voice_key}.onnx"))

    def get_path(self, voice_key):
        """Return the path to an installed voice's .onnx file, or None."""
        path = os.path.join(self._voices_dir, f"{voice_key}.onnx")
        return path if os.path.exists(path) else None

    def install(self, voice_key, progress_cb=None):
        """Download and install a voice model.

        Args:
            voice_key: Voice identifier (e.g. 'en_US-lessac-medium').
            progress_cb: Optional callback(filename, block_num, block_size, total_size).

        Raises:
            KeyError: If voice_key is not found in the catalog.
        """
        catalog = self._catalog.get()
        if voice_key not in catalog:
            raise KeyError(f"Voice '{voice_key}' not found in catalog")

        info = catalog[voice_key]
        for file_path, file_info in info.get("files", {}).items():
            filename = os.path.basename(file_path)
            dest = os.path.join(self._voices_dir, filename)
            if os.path.exists(dest):
                continue

            url = f"{self._catalog.base_url}/{file_path}"

            def hook(block_num, block_size, total_size):
                if progress_cb:
                    progress_cb(filename, block_num, block_size, total_size)

            try:
                urllib.request.urlretrieve(url, dest, reporthook=hook)
            except Exception:
                if os.path.exists(dest):
                    os.remove(dest)
                raise

    def uninstall(self, voice_key):
        """Remove a voice model's files.

        Returns:
            True if files were removed, False if voice was not installed.
        """
        removed = False
        for ext in (".onnx", ".onnx.json"):
            path = os.path.join(self._voices_dir, f"{voice_key}{ext}")
            if os.path.exists(path):
                os.remove(path)
                removed = True
        return removed

    def resolve(self, voice=None, lang="en"):
        """Find the best voice to use, downloading if needed.

        Args:
            voice: Specific voice key to use. If provided, downloads it
                   if not installed.
            lang: Language code ('en' or 'en_US'). Used to find a voice
                  when voice is None. Accepts both 2-letter and full locale.

        Returns:
            Path to the .onnx model file.

        Raises:
            FileNotFoundError: If no matching voice is found or installed.
        """
        if voice:
            onnx_path = os.path.join(self._voices_dir, f"{voice}.onnx")
            if not os.path.exists(onnx_path):
                self.install(voice)
            return onnx_path

        lang_short = lang.split("_")[0] if "_" in lang else lang

        if "_" in lang:
            pattern = os.path.join(self._voices_dir, f"{lang}-*.onnx")
            matches = [f for f in glob.glob(pattern) if not f.endswith(".onnx.json")]
            if matches:
                for m in matches:
                    if "-medium." in m:
                        return m
                return matches[0]

        pattern = os.path.join(self._voices_dir, f"{lang_short}_*.onnx")
        matches = [f for f in glob.glob(pattern) if not f.endswith(".onnx.json")]
        if matches:
            for m in matches:
                if "-medium." in m:
                    return m
            return matches[0]

        raise FileNotFoundError(
            f"No installed voice for language '{lang}'. "
            f"Use list_voices('{lang}') to see available voices, then install() one."
        )

    def load_voice(self, voice_key):
        """Load a Piper voice model and return the PiperVoice instance.

        Args:
            voice_key: Voice identifier, or path to .onnx file.

        Returns:
            A loaded PiperVoice instance ready for synthesis.
        """
        from piper import PiperVoice

        if os.path.exists(voice_key) and voice_key.endswith(".onnx"):
            return PiperVoice.load(voice_key)
        onnx_path = os.path.join(self._voices_dir, f"{voice_key}.onnx")
        return PiperVoice.load(onnx_path)

    def synthesize(self, voice_key, text, output_path=None):
        """Synthesize text to a WAV file.

        Args:
            voice_key: Voice identifier or path to .onnx file.
            text: Text to speak.
            output_path: Where to write the WAV. Defaults to a temp file.

        Returns:
            Path to the generated WAV file.
        """
        if output_path is None:
            output_path = os.path.join(self._data_dir, f"_tts_{os.getpid()}.wav")
        voice = self.load_voice(voice_key)
        synthesize(voice, text, output_path)
        if self._volume < 100:
            scale_volume(output_path, self._volume)
        return output_path

    def synthesize_multi(self, voice_key, texts, output_path=None, pause_ms=700):
        """Synthesize multiple texts into one WAV with pauses.

        Args:
            voice_key: Voice identifier or path to .onnx file.
            texts: List of text strings.
            output_path: Where to write the WAV. Defaults to a temp file.
            pause_ms: Silence between segments in milliseconds.

        Returns:
            Path to the generated WAV file.
        """
        if output_path is None:
            output_path = os.path.join(self._data_dir, f"_tts_{os.getpid()}.wav")
        voice = self.load_voice(voice_key)
        synthesize_multi(voice, texts, output_path, pause_ms)
        if self._volume < 100:
            scale_volume(output_path, self._volume)
        return output_path

    def speak(self, voice_key, text):
        """Synthesize text and play it immediately.

        Args:
            voice_key: Voice identifier or path to .onnx file.
            text: Text to speak.
        """
        wav_path = self.synthesize(voice_key, text)
        try:
            play_wav(wav_path)
        finally:
            if os.path.exists(wav_path):
                os.remove(wav_path)

    def browse(self, config=None, **kwargs):
        """Launch the interactive voice browser TUI.

        Args:
            config: A BrowserConfig instance. If None, one is created
                    from kwargs.
            **kwargs: Passed to BrowserConfig() if config is None.
                      Common: lang, default_voice, test_fn.
        """
        from voxkit.browser import run_browser

        if config is None:
            config = BrowserConfig(**kwargs)
        run_browser(self, config)

    @staticmethod
    def detect_language():
        """Detect language from system locale.

        Returns:
            Full locale string (e.g. 'pl_PL', 'en_US') if available,
            otherwise 2-letter code, falling back to 'en'.
        """
        try:
            loc = locale.getlocale()[0]
            if loc and "_" in loc:
                return loc
            if loc and len(loc) >= 2:
                return loc[:2]
        except Exception:
            pass
        return "en"
