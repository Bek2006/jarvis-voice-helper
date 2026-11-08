from core import vh


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


intents = {
    "farewell": {
        "examples": [
            "можешь отключаться",
            "мочь отключаться",
            "отключаться",
            "отключись",
            "завершить работа",
        ],
        "responses": FAREWELL_RESPONSES,
        "cmd": farewell
    }
}
