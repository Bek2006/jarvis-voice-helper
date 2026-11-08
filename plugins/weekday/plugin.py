import os
import json
# plugins/weekday/plugin.py

import datetime
from core import vh


plugin_dir = os.path.dirname(os.path.abspath(__file__))
intents_path = os.path.join(plugin_dir, "intents.json")

with open(intents_path, "r", encoding="utf-8") as file:
    intents = json.load(file)


WEEKDAYS = [
    "понедельник",
    "вторник",
    "среда",
    "четверг",
    "пятница",
    "суббота",
    "воскресенье",
]


def weekday_command():
    today = datetime.date.today()
    weekday_word = WEEKDAYS[today.weekday()]

    phrases = [
        f"сегодня {weekday_word}",
        weekday_word,
        f"сегодняшний день недели {weekday_word}",
    ]

    vh.say_random(phrases)


cmds = [weekday_command]

for intent, cmd in zip(intents, cmds):
    intents[intent]["cmd"] = cmd
