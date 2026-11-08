import json
# plugins/shutdown/plugin.py

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


cmds = [shutdown_command]

for intent, cmd in zip(intents, cmds):
    intents[intent]["cmd"] = cmd
