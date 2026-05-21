"""Tests for TTS functions."""

import array
import os
import tempfile
import wave

import pytest

from voxkit.tts import scale_volume


@pytest.fixture
def wav_file():
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        path = f.name
    samples = array.array("h", [10000, -10000, 5000, -5000])
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(22050)
        w.writeframes(samples.tobytes())
    yield path
    if os.path.exists(path):
        os.remove(path)


class TestScaleVolume:
    def test_scale_50_percent(self, wav_file):
        scale_volume(wav_file, 50)
        with wave.open(wav_file, "rb") as r:
            frames = r.readframes(r.getnframes())
        samples = array.array("h", frames)
        assert samples[0] == 5000
        assert samples[1] == -5000

    def test_scale_100_no_change(self, wav_file):
        with wave.open(wav_file, "rb") as r:
            original = r.readframes(r.getnframes())
        scale_volume(wav_file, 100)
        with wave.open(wav_file, "rb") as r:
            after = r.readframes(r.getnframes())
        assert original == after

    def test_scale_zero(self, wav_file):
        scale_volume(wav_file, 0)
        with wave.open(wav_file, "rb") as r:
            frames = r.readframes(r.getnframes())
        samples = array.array("h", frames)
        assert all(s == 0 for s in samples)
