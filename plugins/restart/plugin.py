# plugins/restart/plugin.py

import os
from core import vh


POSITIVE_WORDS = {
    "да",
    "ага",
    "конечно",
    "точно",
    "подтверждаю",
    "подтверждать",
    "перезагружай",
    "перезагружать",
    "перезагрузить",
    "перезагрузка",
}


def _is_confirmation(text: str) -> bool:
    if not text:
        return False

    words = set(vh.normalize(text).split())

    return not words.isdisjoint(POSITIVE_WORDS)


def restart_command():
    vh.say("Точно перезагрузить компьютер?")

    answer = vh.recognize_online()

    if _is_confirmation(answer):
        vh.say("Перезагружаю компьютер")

        if os.name == "nt":
            os.system("shutdown /r /t 5")
        else:
            os.system("reboot || systemctl reboot")

    else:
        vh.say_random([
            "Отмена",
            "Перезагрузка отменена",
        ])


intents = {
    "restart": {
        "examples": [
            "перезагрузи компьютер",
            "перезагрузить компьютер",
            "перезагрузи компьютер пожалуйста",
            "перезагрузка компьютера",
            "компьютер перезагрузить",
        ],
        "responses": [
            "перезагружаю компьютер",
            "перезагрузка компьютера",
        ],
        "cmd": restart_command,
    }
}