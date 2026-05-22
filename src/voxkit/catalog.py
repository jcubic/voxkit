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
"""Voice catalog fetching and caching."""

import json
import os
import time
import urllib.request

DEFAULT_VOICES_JSON_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main/voices.json"
DEFAULT_VOICES_BASE_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main"


class VoiceCatalog:
    """Fetches, caches, and queries the Piper voices catalog."""

    def __init__(self, cache_dir, voices_dir, catalog_url=None, base_url=None, cache_ttl=86400):
        self._cache_dir = cache_dir
        self._voices_dir = voices_dir
        self._catalog_url = catalog_url or DEFAULT_VOICES_JSON_URL
        self._base_url = base_url or DEFAULT_VOICES_BASE_URL
        self._cache_ttl = cache_ttl
        self._catalog = None

    @property
    def base_url(self):
        return self._base_url

    def get(self):
        """Return the full catalog dict, fetching/caching as needed."""
        if self._catalog is not None:
            return self._catalog

        cache_file = os.path.join(self._cache_dir, "voices.json")

        if os.path.exists(cache_file):
            age = time.time() - os.path.getmtime(cache_file)
            if age < self._cache_ttl:
                with open(cache_file, "r", encoding="utf-8") as f:
                    self._catalog = json.load(f)
                return self._catalog

        try:
            req = urllib.request.Request(self._catalog_url)
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f)
            self._catalog = data
            return data
        except Exception:
            if os.path.exists(cache_file):
                with open(cache_file, "r", encoding="utf-8") as f:
                    self._catalog = json.load(f)
                return self._catalog
            raise

    def invalidate(self):
        """Clear the in-memory catalog cache."""
        self._catalog = None

    def list_languages(self):
        """Return a sorted list of available language codes (e.g. 'en', 'pl')."""
        catalog = self.get()
        langs = set()
        for info in catalog.values():
            family = info.get("language", {}).get("family", "")
            if family:
                langs.add(family)
        return sorted(langs)

    def get_language_name(self, lang):
        """Return the English name for a 2-letter language code."""
        lang_short = lang.split("_")[0] if "_" in lang else lang
        catalog = self.get()
        for info in catalog.values():
            if info.get("language", {}).get("family", "") == lang_short:
                return info.get("language", {}).get("name_english", lang)
        return lang

    def list_voices(self, lang):
        """List available voices for a language.

        Args:
            lang: Language code — either 2-letter ('en') to match all
                  regional variants, or full locale ('en_US') for exact match.

        Returns:
            Sorted list of VoiceInfo dicts.
        """
        catalog = self.get()
        exact = "_" in lang
        lang_short = lang.split("_")[0] if exact else lang

        matches = []
        for key, info in catalog.items():
            family = info.get("language", {}).get("family", "")
            if family != lang_short:
                continue
            if exact:
                code = info.get("language", {}).get("code", "")
                if code != lang and not key.startswith(lang):
                    continue

            size_bytes = sum(
                f.get("size_bytes", 0)
                for f in info.get("files", {}).values()
                if f.get("size_bytes")
            )
            matches.append(
                {
                    "key": key,
                    "name": info.get("name", ""),
                    "language": f"{family}_{info.get('language', {}).get('code', '')}",
                    "quality": info.get("quality", ""),
                    "region": info.get("language", {}).get("country_english", ""),
                    "speakers": info.get("num_speakers", 1),
                    "size_mb": size_bytes / (1024 * 1024),
                    "installed": self._is_installed(key),
                }
            )

        matches.sort(key=lambda v: v["key"])
        return matches

    def _is_installed(self, voice_key):
        return os.path.exists(os.path.join(self._voices_dir, f"{voice_key}.onnx"))
