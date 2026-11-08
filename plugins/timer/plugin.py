import os
import json
# plugins/timer/plugin.py

import re
import threading
from core import vh


plugin_dir = os.path.dirname(os.path.abspath(__file__))
intents_path = os.path.join(plugin_dir, "intents.json")

with open(intents_path, "r", encoding="utf-8") as file:
    intents = json.load(file)


WORD_NUMBERS = {
    "ноль": 0,
    "один": 1,
    "одна": 1,
    "одно": 1,
    "одну": 1,
    "два": 2,
    "две": 2,
    "три": 3,
    "четыре": 4,
    "пять": 5,
    "шесть": 6,
    "семь": 7,
    "восемь": 8,
    "девять": 9,
    "десять": 10,
    "одиннадцать": 11,
    "двенадцать": 12,
    "тринадцать": 13,
    "четырнадцать": 14,
    "пятнадцать": 15,
    "шестнадцать": 16,
    "семнадцать": 17,
    "восемнадцать": 18,
    "девятнадцать": 19,
    "двадцать": 20,
    "тридцать": 30,
    "сорок": 40,
    "пятьдесят": 50,
    "шестьдесят": 60,
    "семьдесят": 70,
    "восемьдесят": 80,
    "девяносто": 90,
    "пара": 2,
    "пару": 2,
}


ACTIVE_TIMERS = []


def _parse_minutes(text: str):
    if not text:
        return None

    match = re.search(r"\d+", text)

    if match:
        try:
            return int(match.group())
        except ValueError:
            return None

    words = vh.normalize_char(text).split()

    total = 0
    found = False

    for word in words:
        if word in WORD_NUMBERS:
            total += WORD_NUMBERS[word]
            found = True

    if found and total > 0:
        return total

    return None


def _timer_done():
    vh.say_random([
        "Время вышло",
        "Таймер завершён",
        "Время таймера истекло",
    ])


def timer_command():
    text = vh.query.get("text", "") or vh.query.get("norm_text", "")

    minutes = _parse_minutes(text)

    if not minutes:
        vh.say_random([
            "На сколько минут установить таймер?",
            "Скажите длительность таймера в минутах",
        ])

        answer = vh.recognize_online()
        minutes = _parse_minutes(answer)

    if not minutes or minutes <= 0:
        vh.say_random([
            "Не понял длительность таймера",
            "Таймер не установлен",
        ])
        return

    seconds = minutes * 60

    timer = threading.Timer(seconds, _timer_done)
    timer.daemon = True
    timer.start()

    ACTIVE_TIMERS.append(timer)

    vh.say_random([
        "Таймер запущен",
        "Хорошо, таймер установлен",
        "Таймер включён",
    ])


cmds = [timer_command]

for intent, cmd in zip(intents, cmds):
    intents[intent]["cmd"] = cmd
