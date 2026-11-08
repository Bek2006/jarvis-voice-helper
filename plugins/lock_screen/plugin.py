import json
import os
import sys
from core import vh


plugin_dir = os.path.dirname(os.path.abspath(__file__))
intents_path = os.path.join(plugin_dir, "intents.json")

with open(intents_path, "r", encoding="utf-8") as file:
    intents = json.load(file)


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


cmds = [lock_screen]

for intent, cmd in zip(intents, cmds):
    intents[intent]["cmd"] = cmd
