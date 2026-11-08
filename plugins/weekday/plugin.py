# plugins/weekday/plugin.py

import datetime
from core import vh


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


intents = {
    "weekday": {
        "examples": [
            "какой сегодня день недели",
            "какой день недели",
            "какой сегодня день",
            "сегодняшний день недели",
            "назови день недели",
            "скажи день недели",
        ],
        "responses": [
            "сегодня день недели",
            "день недели",
        ],
        "cmd": weekday_command,
    }
}