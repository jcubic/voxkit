"""Tests for browser module."""

from unittest.mock import MagicMock, patch

from voxkit.browser import (
    _draw,
    _get_default_voice_key,
    _render_list,
    progress_bar,
    run_browser,
)
from voxkit.types import BrowserConfig


def _make_voices():
    return [
        {"key": "en_US-lessac-low", "quality": "low", "size_mb": 30, "installed": False},
        {"key": "en_US-lessac-medium", "quality": "medium", "size_mb": 60, "installed": True},
        {"key": "en_US-ryan-high", "quality": "high", "size_mb": 100, "installed": True},
    ]


class TestGetDefaultVoiceKey:
    def test_config_voice_present(self):
        voices = _make_voices()
        assert _get_default_voice_key(voices, "en_US-ryan-high") == "en_US-ryan-high"

    def test_config_voice_not_in_list(self):
        voices = _make_voices()
        result = _get_default_voice_key(voices, "nonexistent")
        assert result == "en_US-lessac-medium"

    def test_prefers_medium(self):
        voices = _make_voices()
        assert _get_default_voice_key(voices) == "en_US-lessac-medium"

    def test_falls_back_to_first_installed(self):
        voices = [
            {"key": "en_US-lessac-low", "quality": "low", "size_mb": 30, "installed": True},
            {"key": "en_US-ryan-high", "quality": "high", "size_mb": 100, "installed": True},
        ]
        assert _get_default_voice_key(voices) == "en_US-lessac-low"

    def test_none_when_no_installed(self):
        voices = [
            {"key": "en_US-lessac-low", "quality": "low", "size_mb": 30, "installed": False},
        ]
        assert _get_default_voice_key(voices) is None

    def test_no_config_voice(self):
        voices = _make_voices()
        assert _get_default_voice_key(voices, None) == "en_US-lessac-medium"


class TestRenderList:
    def test_basic_render(self):
        voices = _make_voices()
        lines = _render_list(voices, 0, "English", "en")
        assert any("Voices for English (en)" in ln for ln in lines)
        assert any("en_US-lessac-low" in ln for ln in lines)

    def test_cursor_position(self):
        voices = _make_voices()
        lines = _render_list(voices, 1, "English", "en")
        for line in lines:
            if "en_US-lessac-medium" in line:
                assert line.strip().startswith(">")
            elif "en_US-lessac-low" in line:
                assert not line.strip().startswith(">")

    def test_installed_marker(self):
        voices = _make_voices()
        lines = _render_list(voices, 0, "English", "en")
        medium_line = [ln for ln in lines if "lessac-medium" in ln][0]
        assert "[*]" in medium_line

    def test_default_marker(self):
        voices = _make_voices()
        lines = _render_list(voices, 0, "English", "en", default_key="en_US-lessac-medium")
        medium_line = [ln for ln in lines if "lessac-medium" in ln][0]
        assert "[D]" in medium_line

    def test_status_line(self):
        voices = _make_voices()
        lines = _render_list(voices, 0, "English", "en", status="Test status")
        assert any("Test status" in ln for ln in lines)

    def test_no_status_line(self):
        voices = _make_voices()
        lines_with = _render_list(voices, 0, "English", "en", status="hello")
        lines_without = _render_list(voices, 0, "English", "en", status="")
        assert len(lines_with) == len(lines_without) + 1

    def test_hide_size(self):
        voices = _make_voices()
        lines = _render_list(voices, 0, "English", "en", show_size=False)
        for line in lines:
            if "en_US-lessac-low" in line:
                assert "MB" not in line

    def test_show_size(self):
        voices = _make_voices()
        lines = _render_list(voices, 0, "English", "en", show_size=True)
        for line in lines:
            if "en_US-lessac-low" in line:
                assert "MB" in line

    def test_keybinding_hints(self):
        voices = _make_voices()
        lines = _render_list(voices, 0, "English", "en")
        hints_line = [ln for ln in lines if "Navigate" in ln][0]
        assert "Install" in hints_line
        assert "Uninstall" in hints_line
        assert "Quit" in hints_line

    def test_no_markers_padding(self):
        voices = [{"key": "test", "quality": "low", "size_mb": 10, "installed": False}]
        lines = _render_list(voices, 0, "Test", "xx")
        voice_line = [ln for ln in lines if "test" in ln][0]
        assert "[*]" not in voice_line


class TestDraw:
    def test_first_draw(self, capsys):
        _draw(["line1", "line2"], 0)
        captured = capsys.readouterr()
        assert "line1" in captured.out
        assert "line2" in captured.out

    def test_overwrite_previous(self, capsys):
        _draw(["line1"], 3)
        captured = capsys.readouterr()
        assert "\033[3A" in captured.out

    def test_clears_extra_lines(self, capsys):
        _draw(["short"], 5)
        captured = capsys.readouterr()
        assert captured.out.count("\033[2K") >= 5


class TestProgressBar:
    def test_in_progress(self, capsys):
        progress_bar("model.onnx", 5, 1024, 10240)
        captured = capsys.readouterr()
        assert "model.onnx" in captured.out
        assert "50%" in captured.out
        assert "█" in captured.out

    def test_complete(self, capsys):
        progress_bar("model.onnx", 10, 1024, 10240)
        captured = capsys.readouterr()
        assert "100%" in captured.out

    def test_zero_total_size(self, capsys):
        progress_bar("model.onnx", 5, 1024, 0)
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_negative_total_size(self, capsys):
        progress_bar("model.onnx", 5, 1024, -1)
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_overflow_clamped(self, capsys):
        progress_bar("model.onnx", 20, 1024, 10240)
        captured = capsys.readouterr()
        assert "100%" in captured.out


class TestRunBrowser:
    def test_no_voices_prints_message(self, capsys):
        manager = MagicMock()
        manager.list_voices.return_value = []
        config = BrowserConfig(lang="xx")
        run_browser(manager, config)
        captured = capsys.readouterr()
        assert "No voices found" in captured.out

    def test_default_config(self, capsys):
        manager = MagicMock()
        manager.list_voices.return_value = []
        run_browser(manager)
        manager.list_voices.assert_called_once_with("en")

    @patch("voxkit.browser._getch")
    def test_quit_key(self, mock_getch, capsys):
        mock_getch.return_value = "q"
        manager = MagicMock()
        manager.list_voices.return_value = _make_voices()
        manager.get_language_name.return_value = "English"
        config = BrowserConfig(lang="en")
        run_browser(manager, config)

    @patch("voxkit.browser._getch")
    def test_navigate_down_then_quit(self, mock_getch, capsys):
        mock_getch.side_effect = ["DOWN", "DOWN", "q"]
        manager = MagicMock()
        manager.list_voices.return_value = _make_voices()
        manager.get_language_name.return_value = "English"
        run_browser(manager, BrowserConfig(lang="en"))

    @patch("voxkit.browser._getch")
    def test_navigate_up_at_top(self, mock_getch, capsys):
        mock_getch.side_effect = ["UP", "q"]
        manager = MagicMock()
        manager.list_voices.return_value = _make_voices()
        manager.get_language_name.return_value = "English"
        run_browser(manager, BrowserConfig(lang="en"))

    @patch("voxkit.browser._getch")
    def test_navigate_down_at_bottom(self, mock_getch, capsys):
        voices = _make_voices()
        mock_getch.side_effect = ["DOWN", "DOWN", "DOWN", "DOWN", "q"]
        manager = MagicMock()
        manager.list_voices.return_value = voices
        manager.get_language_name.return_value = "English"
        run_browser(manager, BrowserConfig(lang="en"))

    @patch("voxkit.browser._getch")
    def test_install_voice(self, mock_getch, capsys):
        mock_getch.side_effect = ["i", "q"]
        voices = _make_voices()
        manager = MagicMock()
        manager.list_voices.return_value = voices
        manager.get_language_name.return_value = "English"
        run_browser(manager, BrowserConfig(lang="en"))
        manager.install.assert_called_once_with("en_US-lessac-low", progress_cb=progress_bar)
        assert voices[0]["installed"] is True

    @patch("voxkit.browser._getch")
    def test_install_already_installed(self, mock_getch, capsys):
        mock_getch.side_effect = ["DOWN", "i", "q"]
        manager = MagicMock()
        manager.list_voices.return_value = _make_voices()
        manager.get_language_name.return_value = "English"
        run_browser(manager, BrowserConfig(lang="en"))
        manager.install.assert_not_called()

    @patch("voxkit.browser._getch")
    def test_uninstall_voice(self, mock_getch, capsys):
        mock_getch.side_effect = ["DOWN", "u", "q"]
        voices = _make_voices()
        manager = MagicMock()
        manager.list_voices.return_value = voices
        manager.get_language_name.return_value = "English"
        run_browser(manager, BrowserConfig(lang="en"))
        manager.uninstall.assert_called_once_with("en_US-lessac-medium")
        assert voices[1]["installed"] is False

    @patch("voxkit.browser._getch")
    def test_uninstall_not_installed(self, mock_getch, capsys):
        mock_getch.side_effect = ["u", "q"]
        manager = MagicMock()
        manager.list_voices.return_value = _make_voices()
        manager.get_language_name.return_value = "English"
        run_browser(manager, BrowserConfig(lang="en"))
        manager.uninstall.assert_not_called()

    @patch("voxkit.browser._getch")
    def test_test_installed_voice_with_test_fn(self, mock_getch, capsys):
        mock_getch.side_effect = ["\r", "q"]
        manager = MagicMock()
        voices = _make_voices()
        voices[0]["installed"] = True
        manager.list_voices.return_value = voices
        manager.get_language_name.return_value = "English"
        test_fn = MagicMock()
        config = BrowserConfig(lang="en", test_fn=test_fn)
        run_browser(manager, config)
        test_fn.assert_called_once_with("en_US-lessac-low")

    @patch("voxkit.browser._getch")
    def test_test_voice_default_speak(self, mock_getch, capsys):
        mock_getch.side_effect = ["DOWN", "\r", "q"]
        manager = MagicMock()
        manager.list_voices.return_value = _make_voices()
        manager.get_language_name.return_value = "English"
        run_browser(manager, BrowserConfig(lang="en"))
        manager.speak.assert_called_once_with("en_US-lessac-medium", "en_US-lessac-medium")

    @patch("voxkit.browser._getch")
    def test_test_auto_installs_if_missing(self, mock_getch, capsys):
        mock_getch.side_effect = ["\r", "q"]
        voices = _make_voices()
        manager = MagicMock()
        manager.list_voices.return_value = voices
        manager.get_language_name.return_value = "English"
        test_fn = MagicMock()
        run_browser(manager, BrowserConfig(lang="en", test_fn=test_fn))
        manager.install.assert_called_once()
        assert voices[0]["installed"] is True
        test_fn.assert_called_once()

    @patch("voxkit.browser._getch")
    def test_on_install_callback(self, mock_getch):
        mock_getch.side_effect = ["i", "q"]
        manager = MagicMock()
        manager.list_voices.return_value = _make_voices()
        manager.get_language_name.return_value = "English"
        on_install = MagicMock()
        config = BrowserConfig(lang="en", on_install=on_install)
        run_browser(manager, config)
        on_install.assert_called_once()

    @patch("voxkit.browser._getch")
    def test_on_uninstall_callback(self, mock_getch):
        mock_getch.side_effect = ["DOWN", "u", "q"]
        manager = MagicMock()
        manager.list_voices.return_value = _make_voices()
        manager.get_language_name.return_value = "English"
        on_uninstall = MagicMock()
        config = BrowserConfig(lang="en", on_uninstall=on_uninstall)
        run_browser(manager, config)
        on_uninstall.assert_called_once()

    @patch("voxkit.browser._getch")
    def test_esc_quits(self, mock_getch, capsys):
        mock_getch.return_value = "\x1b"
        manager = MagicMock()
        manager.list_voices.return_value = _make_voices()
        manager.get_language_name.return_value = "English"
        run_browser(manager, BrowserConfig(lang="en"))

    @patch("voxkit.browser._getch")
    def test_ctrl_c_quits(self, mock_getch, capsys):
        mock_getch.return_value = "\x03"
        manager = MagicMock()
        manager.list_voices.return_value = _make_voices()
        manager.get_language_name.return_value = "English"
        run_browser(manager, BrowserConfig(lang="en"))

    @patch("voxkit.browser._getch")
    def test_newline_tests_voice(self, mock_getch, capsys):
        mock_getch.side_effect = ["DOWN", "\n", "q"]
        manager = MagicMock()
        manager.list_voices.return_value = _make_voices()
        manager.get_language_name.return_value = "English"
        run_browser(manager, BrowserConfig(lang="en"))
        manager.speak.assert_called_once()

    @patch("voxkit.browser._getch")
    def test_custom_keybindings(self, mock_getch, capsys):
        mock_getch.side_effect = ["x", "q"]
        voices = _make_voices()
        manager = MagicMock()
        manager.list_voices.return_value = voices
        manager.get_language_name.return_value = "English"
        config = BrowserConfig(
            lang="en",
            keybindings={"install": "x", "uninstall": "u", "test": "\r", "quit": "q"},
        )
        run_browser(manager, config)
        manager.install.assert_called_once()

    @patch("voxkit.browser._getch")
    def test_string_quit_key(self, mock_getch, capsys):
        mock_getch.return_value = "q"
        manager = MagicMock()
        manager.list_voices.return_value = _make_voices()
        manager.get_language_name.return_value = "English"
        config = BrowserConfig(
            lang="en",
            keybindings={"install": "i", "uninstall": "u", "test": "\r", "quit": "q"},
        )
        run_browser(manager, config)

    @patch("voxkit.browser._getch")
    def test_string_test_key(self, mock_getch, capsys):
        mock_getch.side_effect = ["DOWN", "t", "q"]
        manager = MagicMock()
        manager.list_voices.return_value = _make_voices()
        manager.get_language_name.return_value = "English"
        config = BrowserConfig(
            lang="en",
            keybindings={"install": "i", "uninstall": "u", "test": "t", "quit": "q"},
        )
        run_browser(manager, config)
        manager.speak.assert_called_once()

    @patch("voxkit.browser._getch")
    def test_unknown_key_ignored(self, mock_getch, capsys):
        mock_getch.side_effect = ["z", "q"]
        manager = MagicMock()
        manager.list_voices.return_value = _make_voices()
        manager.get_language_name.return_value = "English"
        run_browser(manager, BrowserConfig(lang="en"))
        manager.install.assert_not_called()
        manager.uninstall.assert_not_called()
        manager.speak.assert_not_called()
