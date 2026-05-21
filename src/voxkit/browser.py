"""Interactive TUI voice browser."""

import sys
import termios
import tty

from voxkit.types import BrowserConfig

CYAN = "\033[36m"
GREEN = "\033[32m"
BOLD = "\033[1m"
RESET = "\033[0m"
CLEAR_LINE = "\033[2K"
HIDE_CURSOR = "\033[?25l"
SHOW_CURSOR = "\033[?25h"


def _getch():
    """Read a single keypress. Returns 'UP', 'DOWN', or a character."""
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == "\x1b":
            ch2 = sys.stdin.read(1)
            if ch2 == "[":
                ch3 = sys.stdin.read(1)
                if ch3 == "A":
                    return "UP"
                if ch3 == "B":
                    return "DOWN"
            return "\x1b"
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def _render_list(voices, cursor, lang_name, lang, status="", default_key=None, show_size=True):
    lines = []
    lines.append(f"Voices for {lang_name} ({lang}):")
    lines.append("")
    for i, v in enumerate(voices):
        arrow = ">" if i == cursor else " "
        marks = ""
        if v["installed"]:
            marks += f" {GREEN}[*]{RESET}"
        if v["key"] == default_key:
            marks += f" {CYAN}[D]{RESET}"
        if not marks:
            marks = "    "
        size = f" {v['size_mb']:>3.0f} MB" if show_size else ""
        line = f"  {arrow} {v['key']:<40} {v['quality']:<8}{size}{marks}"
        lines.append(line)
    lines.append("")

    nav = f"{BOLD}↑/↓{RESET} Navigate"
    enter = f"{BOLD}Enter{RESET} Test"
    inst = f"{BOLD}i{RESET} Install"
    uninst = f"{BOLD}u{RESET} Uninstall"
    quit_hint = f"{BOLD}q{RESET} Quit"
    lines.append(f"  {nav}  {enter}  {inst}  {uninst}  {quit_hint}")
    if status:
        lines.append(f"  {status}")
    return lines


def _draw(lines, prev_line_count):
    if prev_line_count > 0:
        sys.stdout.write(f"\033[{prev_line_count}A")
    for line in lines:
        sys.stdout.write(f"\r{CLEAR_LINE}{line}\n")
    if prev_line_count > len(lines):
        for _ in range(prev_line_count - len(lines)):
            sys.stdout.write(f"\r{CLEAR_LINE}\n")
        sys.stdout.write(f"\033[{prev_line_count - len(lines)}A")
    sys.stdout.flush()


def progress_bar(filename, block_num, block_size, total_size):
    """Render a download progress bar on the current line.

    Compatible with VoiceManager.install() progress_cb signature.
    """
    if total_size <= 0:
        return
    downloaded = block_num * block_size
    pct = min(100, downloaded * 100 // total_size)
    bar_width = 30
    filled = bar_width * pct // 100
    bar = "█" * filled + "░" * (bar_width - filled)
    sys.stdout.write("\033[s")
    sys.stdout.write(f"\r{CLEAR_LINE}  Downloading {filename}... [{bar}] {pct}%")
    sys.stdout.flush()
    if pct >= 100:
        sys.stdout.write(f"\r{CLEAR_LINE}")
        sys.stdout.write("\033[u")
        sys.stdout.flush()


def _get_default_voice_key(voices, config_voice=None):
    if config_voice:
        for v in voices:
            if v["key"] == config_voice:
                return config_voice
    installed = [v for v in voices if v["installed"]]
    if not installed:
        return None
    for v in installed:
        if "-medium" in v["key"]:
            return v["key"]
    return installed[0]["key"]


def run_browser(manager, config=None):
    """Launch the interactive voice browser TUI.

    Args:
        manager: A VoiceManager instance.
        config: Optional BrowserConfig for customization.
    """
    if config is None:
        config = BrowserConfig()

    voices = manager.list_voices(config.lang)
    if not voices:
        print(f"No voices found for language '{config.lang}'.")
        return

    lang_name = manager.get_language_name(config.lang)
    default_key = _get_default_voice_key(voices, config.default_voice)
    cursor = 0
    prev_lines = 0
    status = ""

    kb = config.keybindings
    install_key = kb.get("install", "i")
    uninstall_key = kb.get("uninstall", "u")
    test_keys = kb.get("test", "\r")
    if isinstance(test_keys, str):
        test_keys = (test_keys,)
    quit_keys = kb.get("quit", ("q", "\x03", "\x1b"))
    if isinstance(quit_keys, str):
        quit_keys = (quit_keys,)

    sys.stdout.write(HIDE_CURSOR)
    sys.stdout.flush()

    try:
        while True:
            lines = _render_list(
                voices, cursor, lang_name, config.lang, status, default_key, config.show_size
            )
            _draw(lines, prev_lines)
            prev_lines = len(lines)
            status = ""

            key = _getch()
            if key == "UP" and cursor > 0:
                cursor -= 1
            elif key == "DOWN" and cursor < len(voices) - 1:
                cursor += 1
            elif key in quit_keys:
                break
            elif key == install_key:
                v = voices[cursor]
                if v["installed"]:
                    status = f"'{v['key']}' is already installed."
                else:
                    msg = f"Installing {v['key']}..."
                    lines = _render_list(
                        voices, cursor, lang_name, config.lang, msg, default_key, config.show_size
                    )
                    _draw(lines, prev_lines)
                    prev_lines = len(lines)
                    manager.install(v["key"], progress_cb=progress_bar)
                    v["installed"] = True
                    default_key = _get_default_voice_key(voices, config.default_voice)
                    status = f"Installed '{v['key']}'."
                    if config.on_install:
                        config.on_install(v)
            elif key == uninstall_key:
                v = voices[cursor]
                if not v["installed"]:
                    status = f"'{v['key']}' is not installed."
                else:
                    manager.uninstall(v["key"])
                    v["installed"] = False
                    default_key = _get_default_voice_key(voices, config.default_voice)
                    status = f"Uninstalled '{v['key']}'."
                    if config.on_uninstall:
                        config.on_uninstall(v)
            elif key in test_keys or key == "\n":
                v = voices[cursor]
                if not v["installed"]:
                    msg = f"Installing {v['key']}..."
                    lines = _render_list(
                        voices, cursor, lang_name, config.lang, msg, default_key, config.show_size
                    )
                    _draw(lines, prev_lines)
                    prev_lines = len(lines)
                    manager.install(v["key"], progress_cb=progress_bar)
                    v["installed"] = True
                    default_key = _get_default_voice_key(voices, config.default_voice)
                status = f"Testing '{v['key']}'..."
                lines = _render_list(
                    voices, cursor, lang_name, config.lang, status, default_key, config.show_size
                )
                _draw(lines, prev_lines)
                prev_lines = len(lines)
                sys.stdout.write(SHOW_CURSOR)
                sys.stdout.flush()
                if config.test_fn:
                    config.test_fn(v["key"])
                else:
                    manager.speak(v["key"], v["key"])
                sys.stdout.write(HIDE_CURSOR)
                sys.stdout.flush()
                status = f"Tested '{v['key']}'."
    finally:
        sys.stdout.write(SHOW_CURSOR)
        sys.stdout.write("\n")
        sys.stdout.flush()
