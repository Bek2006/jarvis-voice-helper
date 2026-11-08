import json
# plugins/restart/plugin.py

import os
from core import vh


plugin_dir = os.path.dirname(os.path.abspath(__file__))
intents_path = os.path.join(plugin_dir, "intents.json")

with open(intents_path, "r", encoding="utf-8") as file:
    intents = json.load(file)


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


cmds = [restart_command]

for intent, cmd in zip(intents, cmds):
    intents[intent]["cmd"] = cmd
