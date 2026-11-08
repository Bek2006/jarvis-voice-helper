# plugins/shutdown/plugin.py

import os
from core import vh


POSITIVE_WORDS = {
    "да",
    "ага",
    "конечно",
    "точно",
    "подтверждаю",
    "подтверждать",
    "выключай",
    "выключать",
    "выключить",
    "выключение",
}


def _is_confirmation(text: str) -> bool:
    if not text:
        return False

    words = set(vh.normalize(text).split())

    return not words.isdisjoint(POSITIVE_WORDS)


def shutdown_command():
    vh.say("Точно выключить компьютер?")

    answer = vh.recognize_online()

    if _is_confirmation(answer):
        vh.say("Выключаю компьютер")

        if os.name == "nt":
            os.system("shutdown /s /t 5")
        else:
            os.system("shutdown now || systemctl poweroff")

    else:
        vh.say_random([
            "Отмена",
            "Выключение отменено",
        ])


intents = {
    "shutdown": {
        "examples": [
            "выключи компьютер",
            "выключить компьютер",
            "выключи компьютер пожалуйста",
            "завершить работу компьютера",
            "завершение работы компьютера",
            "компьютер выключить",
        ],
        "responses": [
            "выключаю компьютер",
            "выключение компьютера",
        ],
        "cmd": shutdown_command,
    }
}