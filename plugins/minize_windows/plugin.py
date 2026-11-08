import os
import json
from core import vh


plugin_dir = os.path.dirname(os.path.abspath(__file__))
intents_path = os.path.join(plugin_dir, "intents.json")

with open(intents_path, "r", encoding="utf-8") as file:
    intents = json.load(file)

import keyboard


def minimize_windows():
    vh.say_random(intents["minimize_windows"]["responses"])
    keyboard.send("win+d")


cmds = [minimize_windows]

for intent, cmd in zip(intents, cmds):
    intents[intent]["cmd"] = cmd
