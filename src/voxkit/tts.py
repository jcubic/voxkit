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
"""TTS synthesis and audio playback."""

import array
import os
import subprocess
import wave


def synthesize(voice, text, output_path):
    """Synthesize text to a WAV file using a loaded Piper voice.

    Args:
        voice: A loaded PiperVoice instance.
        text: Text to synthesize.
        output_path: Path to write the WAV file.

    Returns:
        The output_path.
    """
    with wave.open(output_path, "wb") as wav_file:
        voice.synthesize_wav(text, wav_file)
    return output_path


def synthesize_multi(voice, texts, output_path, pause_ms=700):
    """Synthesize multiple texts into a single WAV with pauses between them.

    Args:
        voice: A loaded PiperVoice instance.
        texts: List of text strings to synthesize.
        output_path: Path to write the combined WAV file.
        pause_ms: Milliseconds of silence between segments (default 700).

    Returns:
        The output_path.
    """
    if not texts:
        raise ValueError("texts must be a non-empty list")

    synthesize(voice, texts[0], output_path)
    if len(texts) == 1:
        return output_path

    tmp_part = output_path + ".part"

    with wave.open(output_path, "rb") as r:
        params = r.getparams()
        all_frames = r.readframes(r.getnframes())

    with wave.open(output_path, "wb") as out:
        out.setparams(params)
        out.writeframes(all_frames)
        for t in texts[1:]:
            _append_silence(out, pause_ms, params.framerate, params.sampwidth, params.nchannels)
            synthesize(voice, t, tmp_part)
            with wave.open(tmp_part, "rb") as part:
                out.writeframes(part.readframes(part.getnframes()))
            os.remove(tmp_part)

    return output_path


def scale_volume(wav_path, volume):
    """Scale WAV sample amplitudes to a volume level (0-100).

    Args:
        wav_path: Path to WAV file (modified in place).
        volume: Volume level 0-100. At 100, no scaling is applied.
    """
    if volume >= 100:
        return
    scale = volume / 100.0
    with wave.open(wav_path, "rb") as r:
        params = r.getparams()
        frames = r.readframes(r.getnframes())
    samples = array.array("h", frames)
    for i in range(len(samples)):
        samples[i] = max(-32768, min(32767, int(samples[i] * scale)))
    with wave.open(wav_path, "wb") as w:
        w.setparams(params)
        w.writeframes(samples.tobytes())


def play_wav(wav_path):
    """Play a WAV file using aplay."""
    subprocess.run(["aplay", wav_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def play_mp3(mp3_path, volume=100):
    """Play an MP3 file using mpg123.

    Args:
        mp3_path: Path to the MP3 file.
        volume: Volume level 0-100.
    """
    cmd = ["mpg123", "-q"]
    if volume < 100:
        cmd += ["-f", str(int(volume * 32768 / 100))]
    cmd.append(mp3_path)
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _append_silence(wav_file, duration_ms, sample_rate, sample_width, channels):
    num_samples = int(sample_rate * duration_ms / 1000)
    silence = b"\x00" * (num_samples * sample_width * channels)
    wav_file.writeframes(silence)
