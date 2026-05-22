"""Tests for TTS functions."""

import array
import os
import tempfile
import wave
from unittest.mock import MagicMock, patch

import pytest

from voxkit.tts import (
    _append_silence,
    play_mp3,
    play_wav,
    scale_volume,
    synthesize,
    synthesize_multi,
)


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


@pytest.fixture
def tmp_path_wav():
    with tempfile.TemporaryDirectory() as d:
        yield os.path.join(d, "out.wav")


def _make_mock_voice():
    voice = MagicMock()

    def fake_synthesize(text, wav_file):
        samples = array.array("h", [1000, 2000, 3000, 4000])
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(22050)
        wav_file.writeframes(samples.tobytes())

    voice.synthesize_wav.side_effect = fake_synthesize
    return voice


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


class TestSynthesize:
    def test_synthesize_creates_wav(self, tmp_path_wav):
        voice = _make_mock_voice()
        result = synthesize(voice, "hello", tmp_path_wav)
        assert result == tmp_path_wav
        assert os.path.exists(tmp_path_wav)
        voice.synthesize_wav.assert_called_once()

    def test_synthesize_wav_readable(self, tmp_path_wav):
        voice = _make_mock_voice()
        synthesize(voice, "hello", tmp_path_wav)
        with wave.open(tmp_path_wav, "rb") as r:
            assert r.getnframes() == 4
            assert r.getnchannels() == 1


class TestSynthesizeMulti:
    def test_single_text(self, tmp_path_wav):
        voice = _make_mock_voice()
        result = synthesize_multi(voice, ["hello"], tmp_path_wav)
        assert result == tmp_path_wav
        assert voice.synthesize_wav.call_count == 1

    def test_multiple_texts(self, tmp_path_wav):
        voice = _make_mock_voice()
        result = synthesize_multi(voice, ["hello", "world"], tmp_path_wav)
        assert result == tmp_path_wav
        assert voice.synthesize_wav.call_count == 2
        with wave.open(tmp_path_wav, "rb") as r:
            assert r.getnframes() > 4

    def test_three_texts_with_pauses(self, tmp_path_wav):
        voice = _make_mock_voice()
        synthesize_multi(voice, ["a", "b", "c"], tmp_path_wav, pause_ms=100)
        assert voice.synthesize_wav.call_count == 3
        with wave.open(tmp_path_wav, "rb") as r:
            total = r.getnframes()
            silence_per_pause = int(22050 * 100 / 1000)
            assert total == 4 * 3 + silence_per_pause * 2

    def test_empty_texts_raises(self, tmp_path_wav):
        voice = _make_mock_voice()
        with pytest.raises(ValueError, match="non-empty"):
            synthesize_multi(voice, [], tmp_path_wav)

    def test_part_file_cleaned_up(self, tmp_path_wav):
        voice = _make_mock_voice()
        synthesize_multi(voice, ["hello", "world"], tmp_path_wav)
        assert not os.path.exists(tmp_path_wav + ".part")


class TestAppendSilence:
    def test_appends_correct_bytes(self):
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            path = f.name
        try:
            with wave.open(path, "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(22050)
                w.writeframes(b"\x00\x00" * 10)
                _append_silence(w, 1000, 22050, 2, 1)
            with wave.open(path, "rb") as r:
                assert r.getnframes() == 10 + 22050
        finally:
            os.remove(path)


class TestPlayWav:
    @patch("voxkit.tts.subprocess.run")
    def test_calls_aplay(self, mock_run):
        play_wav("/tmp/test.wav")
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[0] == "aplay"
        assert args[1] == "/tmp/test.wav"


class TestPlayMp3:
    @patch("voxkit.tts.subprocess.run")
    def test_calls_mpg123_full_volume(self, mock_run):
        play_mp3("/tmp/test.mp3")
        args = mock_run.call_args[0][0]
        assert args == ["mpg123", "-q", "/tmp/test.mp3"]

    @patch("voxkit.tts.subprocess.run")
    def test_calls_mpg123_with_volume(self, mock_run):
        play_mp3("/tmp/test.mp3", volume=50)
        args = mock_run.call_args[0][0]
        assert args[0] == "mpg123"
        assert "-f" in args
        idx = args.index("-f")
        assert int(args[idx + 1]) == int(50 * 32768 / 100)

    @patch("voxkit.tts.subprocess.run")
    def test_volume_100_no_flag(self, mock_run):
        play_mp3("/tmp/test.mp3", volume=100)
        args = mock_run.call_args[0][0]
        assert "-f" not in args
