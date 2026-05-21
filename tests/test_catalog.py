"""Tests for VoiceCatalog."""

import json
import os
import tempfile
import time

import pytest

from voxkit.catalog import VoiceCatalog

SAMPLE_CATALOG = {
    "en_US-lessac-medium": {
        "name": "lessac",
        "language": {
            "code": "en_US",
            "family": "en",
            "name_english": "English",
            "country_english": "United States",
        },
        "quality": "medium",
        "num_speakers": 1,
        "files": {
            "en/en_US/lessac/medium/en_US-lessac-medium.onnx": {
                "size_bytes": 63201505,
            },
        },
    },
}


@pytest.fixture
def dirs():
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_dir = os.path.join(tmpdir, "cache")
        voices_dir = os.path.join(tmpdir, "voices")
        os.makedirs(cache_dir)
        os.makedirs(voices_dir)
        yield cache_dir, voices_dir


@pytest.fixture
def catalog_with_cache(dirs):
    cache_dir, voices_dir = dirs
    cache_file = os.path.join(cache_dir, "voices.json")
    with open(cache_file, "w") as f:
        json.dump(SAMPLE_CATALOG, f)
    return VoiceCatalog(cache_dir, voices_dir)


class TestCaching:
    def test_loads_from_cache(self, catalog_with_cache):
        data = catalog_with_cache.get()
        assert "en_US-lessac-medium" in data

    def test_invalidate_clears_memory_cache(self, catalog_with_cache):
        catalog_with_cache.get()
        catalog_with_cache.invalidate()
        data = catalog_with_cache.get()
        assert "en_US-lessac-medium" in data

    def test_expired_cache_fetches(self, dirs):
        cache_dir, voices_dir = dirs
        cache_file = os.path.join(cache_dir, "voices.json")
        with open(cache_file, "w") as f:
            json.dump(SAMPLE_CATALOG, f)
        old_time = time.time() - 90000
        os.utime(cache_file, (old_time, old_time))
        catalog = VoiceCatalog(cache_dir, voices_dir, cache_ttl=86400)
        data = catalog.get()
        assert "en_US-lessac-medium" in data


class TestListLanguages:
    def test_lists_languages(self, catalog_with_cache):
        langs = catalog_with_cache.list_languages()
        assert "en" in langs

    def test_language_name(self, catalog_with_cache):
        assert catalog_with_cache.get_language_name("en") == "English"

    def test_unknown_language_name(self, catalog_with_cache):
        assert catalog_with_cache.get_language_name("xx") == "xx"


class TestListVoices:
    def test_installed_detection(self, dirs):
        cache_dir, voices_dir = dirs
        cache_file = os.path.join(cache_dir, "voices.json")
        with open(cache_file, "w") as f:
            json.dump(SAMPLE_CATALOG, f)
        with open(os.path.join(voices_dir, "en_US-lessac-medium.onnx"), "w") as f:
            f.write("fake")
        catalog = VoiceCatalog(cache_dir, voices_dir)
        voices = catalog.list_voices("en")
        assert voices[0]["installed"] is True
