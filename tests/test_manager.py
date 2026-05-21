"""Tests for VoiceManager."""

import json
import os
import tempfile

import pytest

from voxkit import VoiceManager

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
            "en/en_US/lessac/medium/en_US-lessac-medium.onnx.json": {
                "size_bytes": 5420,
            },
        },
    },
    "en_GB-alba-medium": {
        "name": "alba",
        "language": {
            "code": "en_GB",
            "family": "en",
            "name_english": "English",
            "country_english": "Great Britain",
        },
        "quality": "medium",
        "num_speakers": 1,
        "files": {
            "en/en_GB/alba/medium/en_GB-alba-medium.onnx": {
                "size_bytes": 50000000,
            },
            "en/en_GB/alba/medium/en_GB-alba-medium.onnx.json": {
                "size_bytes": 4000,
            },
        },
    },
    "pl_PL-darkman-medium": {
        "name": "darkman",
        "language": {
            "code": "pl_PL",
            "family": "pl",
            "name_english": "Polish",
            "country_english": "Poland",
        },
        "quality": "medium",
        "num_speakers": 1,
        "files": {
            "pl/pl_PL/darkman/medium/pl_PL-darkman-medium.onnx": {
                "size_bytes": 63000000,
            },
            "pl/pl_PL/darkman/medium/pl_PL-darkman-medium.onnx.json": {
                "size_bytes": 3000,
            },
        },
    },
}


@pytest.fixture
def data_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def vm(data_dir):
    return VoiceManager(data_dir)


@pytest.fixture
def vm_with_catalog(data_dir):
    manager = VoiceManager(data_dir)
    cache_file = os.path.join(data_dir, "cache", "voices.json")
    with open(cache_file, "w") as f:
        json.dump(SAMPLE_CATALOG, f)
    return manager


class TestInit:
    def test_creates_directories(self, data_dir):
        VoiceManager(data_dir)
        assert os.path.isdir(os.path.join(data_dir, "models"))
        assert os.path.isdir(os.path.join(data_dir, "cache"))

    def test_expands_user_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            home_path = os.path.join(tmpdir, "test")
            vm = VoiceManager(home_path)
            assert "~" not in vm.data_dir

    def test_data_dir_property(self, data_dir):
        vm = VoiceManager(data_dir)
        assert vm.data_dir == data_dir

    def test_voices_dir_property(self, data_dir):
        vm = VoiceManager(data_dir)
        assert vm.voices_dir == os.path.join(data_dir, "models")


class TestVolume:
    def test_default_volume(self, vm):
        assert vm.volume == 100

    def test_set_volume(self, vm):
        vm.set_volume(50)
        assert vm.volume == 50

    def test_set_volume_out_of_range(self, vm):
        with pytest.raises(ValueError):
            vm.set_volume(101)
        with pytest.raises(ValueError):
            vm.set_volume(-1)

    def test_set_volume_zero(self, vm):
        vm.set_volume(0)
        assert vm.volume == 0


class TestListVoices:
    def test_list_all_english(self, vm_with_catalog):
        voices = vm_with_catalog.list_voices("en")
        assert len(voices) == 2
        keys = [v["key"] for v in voices]
        assert "en_US-lessac-medium" in keys
        assert "en_GB-alba-medium" in keys

    def test_list_exact_locale(self, vm_with_catalog):
        voices = vm_with_catalog.list_voices("en_US")
        keys = [v["key"] for v in voices]
        assert "en_US-lessac-medium" in keys
        assert "en_GB-alba-medium" not in keys

    def test_list_polish(self, vm_with_catalog):
        voices = vm_with_catalog.list_voices("pl")
        assert len(voices) == 1
        assert voices[0]["key"] == "pl_PL-darkman-medium"

    def test_list_nonexistent_language(self, vm_with_catalog):
        voices = vm_with_catalog.list_voices("xx")
        assert voices == []

    def test_voice_fields(self, vm_with_catalog):
        voices = vm_with_catalog.list_voices("pl")
        v = voices[0]
        assert v["key"] == "pl_PL-darkman-medium"
        assert v["name"] == "darkman"
        assert v["quality"] == "medium"
        assert v["size_mb"] > 0
        assert v["installed"] is False


class TestGetVoice:
    def test_existing_voice(self, vm_with_catalog):
        v = vm_with_catalog.get_voice("en_US-lessac-medium")
        assert v is not None
        assert v["key"] == "en_US-lessac-medium"
        assert v["quality"] == "medium"

    def test_nonexistent_voice(self, vm_with_catalog):
        assert vm_with_catalog.get_voice("nonexistent") is None


class TestInstallUninstall:
    def test_is_installed_false(self, vm_with_catalog):
        assert vm_with_catalog.is_installed("en_US-lessac-medium") is False

    def test_is_installed_true(self, vm_with_catalog):
        onnx_path = os.path.join(vm_with_catalog.voices_dir, "en_US-lessac-medium.onnx")
        with open(onnx_path, "w") as f:
            f.write("fake")
        assert vm_with_catalog.is_installed("en_US-lessac-medium") is True

    def test_get_path_installed(self, vm_with_catalog):
        onnx_path = os.path.join(vm_with_catalog.voices_dir, "en_US-lessac-medium.onnx")
        with open(onnx_path, "w") as f:
            f.write("fake")
        assert vm_with_catalog.get_path("en_US-lessac-medium") == onnx_path

    def test_get_path_not_installed(self, vm_with_catalog):
        assert vm_with_catalog.get_path("en_US-lessac-medium") is None

    def test_install_unknown_voice(self, vm_with_catalog):
        with pytest.raises(KeyError, match="not found"):
            vm_with_catalog.install("nonexistent")

    def test_uninstall_removes_files(self, vm_with_catalog):
        for ext in (".onnx", ".onnx.json"):
            path = os.path.join(vm_with_catalog.voices_dir, f"en_US-lessac-medium{ext}")
            with open(path, "w") as f:
                f.write("fake")
        assert vm_with_catalog.uninstall("en_US-lessac-medium") is True
        assert not os.path.exists(
            os.path.join(vm_with_catalog.voices_dir, "en_US-lessac-medium.onnx")
        )
        assert not os.path.exists(
            os.path.join(vm_with_catalog.voices_dir, "en_US-lessac-medium.onnx.json")
        )

    def test_uninstall_not_installed(self, vm_with_catalog):
        assert vm_with_catalog.uninstall("en_US-lessac-medium") is False


class TestResolve:
    def test_resolve_with_installed_voice(self, vm_with_catalog):
        onnx_path = os.path.join(vm_with_catalog.voices_dir, "en_US-lessac-medium.onnx")
        with open(onnx_path, "w") as f:
            f.write("fake")
        result = vm_with_catalog.resolve(voice="en_US-lessac-medium")
        assert result == onnx_path

    def test_resolve_by_language(self, vm_with_catalog):
        onnx_path = os.path.join(vm_with_catalog.voices_dir, "en_US-lessac-medium.onnx")
        with open(onnx_path, "w") as f:
            f.write("fake")
        result = vm_with_catalog.resolve(lang="en")
        assert result == onnx_path

    def test_resolve_by_full_locale(self, vm_with_catalog):
        onnx_path = os.path.join(vm_with_catalog.voices_dir, "en_US-lessac-medium.onnx")
        with open(onnx_path, "w") as f:
            f.write("fake")
        result = vm_with_catalog.resolve(lang="en_US")
        assert result == onnx_path

    def test_resolve_prefers_medium(self, vm_with_catalog):
        for name in ("en_US-lessac-low.onnx", "en_US-lessac-medium.onnx"):
            with open(os.path.join(vm_with_catalog.voices_dir, name), "w") as f:
                f.write("fake")
        result = vm_with_catalog.resolve(lang="en")
        assert "medium" in result

    def test_resolve_no_match(self, vm_with_catalog):
        with pytest.raises(FileNotFoundError, match="No installed voice"):
            vm_with_catalog.resolve(lang="xx")


class TestListLanguages:
    def test_list_languages(self, vm_with_catalog):
        langs = vm_with_catalog.list_languages()
        assert "en" in langs
        assert "pl" in langs

    def test_get_language_name(self, vm_with_catalog):
        assert vm_with_catalog.get_language_name("en") == "English"
        assert vm_with_catalog.get_language_name("pl") == "Polish"

    def test_get_language_name_full_locale(self, vm_with_catalog):
        assert vm_with_catalog.get_language_name("en_US") == "English"


class TestDetectLanguage:
    def test_detect_returns_string(self):
        lang = VoiceManager.detect_language()
        assert isinstance(lang, str)
        assert len(lang) >= 2
