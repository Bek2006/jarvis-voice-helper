import os
import json
from core import vh


plugin_dir = os.path.dirname(os.path.abspath(__file__))
intents_path = os.path.join(plugin_dir, "intents.json")

with open(intents_path, "r", encoding="utf-8") as file:
    intents = json.load(file)


FAREWELL_RESPONSES = [
    "до свидания, сэр!",
    "хорошо",
    "хорошо, сэр",
    "отключаюсь",
    "всего хорошего",
    "отключаюсь, сэр",
]


def farewell():
    vh.say_random(FAREWELL_RESPONSES)
    raise SystemExit(0)


cmds = [farewell]

for intent, cmd in zip(intents, cmds):
    intents[intent]["cmd"] = cmd
