from core import vh

import keyboard


def minimize_windows():
    vh.say_random(intents["minimize_windows"]["responses"])
    keyboard.send("win+d")


intents = {
    "minimize_windows": {
        "examples": [
            "сверни все окна",
            "свернуть все окно",
            "свернуть окна",
            "сверни окна"
        ],
        "responses": [
            "хорошо",
            "хорошо, сэр",
            "сворачиваю все окна",
            "сворачиваю все окна, сэр",
            "сворачиваю окна"
            "сворачиваю окна, сэр"],
        "cmd": minimize_windows
    }
}
