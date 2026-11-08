import os
import sys
from core import vh


LOCK_SCREEN_RESPOMSES = [
    "Блокирую экран",
    "Экран будет заблокирован",
]


def _lock_windows():
    import ctypes
    ctypes.windll.user32.LockWorkStation()


def _lock_linux() -> bool:
    commands = [
        "loginctl lock-session",
        "gnome-screensaver-command -l",
        "xdg-screensaver lock",
        "xscreensaver-command -lock",
        "xset dpms force off",
    ]

    for command in commands:
        result = os.system(command)

        if result == 0:
            return True

    return False


def _lock_mac() -> bool:
    result = os.system("pmset displaysleepnow")
    return result == 0


def lock_screen():
    vh.say_random(LOCK_SCREEN_RESPOMSES)

    if os.name == "nt":
        _lock_windows()

    elif sys.platform.startswith("linux"):
        if not _lock_linux():
            vh.say("Не удалось заблокировать экран")

    elif sys.platform == "darwin":
        if not _lock_mac():
            vh.say("Не удалось заблокировать экран")

    else:
        vh.say("Блокировка экрана не поддерживается")


intents = {
    "lock_screen": {
        "examples": [
            "заблокируй экран",
            "заблокировать экран",
            "блокировка экрана",
            "экран блокировки",
            "заблокируй экран компьютера",
        ],
        "responses": LOCK_SCREEN_RESPOMSES,
        "cmd": lock_screen,
    }
}