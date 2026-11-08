# plugins/weather/plugin.py

import os
import sys
import json
import traceback
from datetime import datetime
from core import vh


try:
    import requests
except ImportError:
    requests = None


PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(PLUGIN_DIR, "config.json")
ERROR_LOG_FILE = os.path.join(PLUGIN_DIR, "error.log")


UNITS = {
    0: "ноль",
    1: "один",
    2: "два",
    3: "три",
    4: "четыре",
    5: "пять",
    6: "шесть",
    7: "семь",
    8: "восемь",
    9: "девять",
}

TEENS = {
    10: "десять",
    11: "одиннадцать",
    12: "двенадцать",
    13: "тринадцать",
    14: "четырнадцать",
    15: "пятнадцать",
    16: "шестнадцать",
    17: "семнадцать",
    18: "восемнадцать",
    19: "девятнадцать",
}

TENS = {
    20: "двадцать",
    30: "тридцать",
    40: "сорок",
    50: "пятьдесят",
    60: "шестьдесят",
    70: "семьдесят",
    80: "восемьдесят",
    90: "девяносто",
}

HUNDREDS = {
    100: "сто",
    200: "двести",
    300: "триста",
    400: "четыреста",
    500: "пятьсот",
    600: "шестьсот",
    700: "семьсот",
    800: "восемьсот",
    900: "девятьсот",
}


def _log_error(message: str, error=None) -> None:
    """
    Печатает ошибку в консоль и записывает её в error.log
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        f"[{timestamp}] {message}"
    ]

    if error is not None:
        lines.append(str(error))

    if sys.exc_info()[0] is not None:
        lines.append(traceback.format_exc())

    text = "\n".join(lines)

    print(text)

    try:
        with open(ERROR_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(text)
            f.write("\n\n")
    except Exception as log_error:
        print("Не удалось записать ошибку в error.log:", log_error)


def _number_to_words(n: int) -> str:
    """
    Переводит целое число в слова.
    Поддерживает отрицательные числа.
    """
    try:
        n = int(n)
    except Exception:
        return "неизвестно"

    if n < 0:
        return "минус " + _number_to_words(abs(n))

    if n in UNITS:
        return UNITS[n]

    if n in TEENS:
        return TEENS[n]

    if n in TENS:
        return TENS[n]

    if n in HUNDREDS:
        return HUNDREDS[n]

    if n > 999:
        # Для погоды обычно не нужно, но чтобы не говорить цифрами
        return "очень много"

    hundreds = (n // 100) * 100
    rest = n % 100

    if rest == 0:
        return HUNDREDS[hundreds]

    return f"{HUNDREDS[hundreds]} {_number_to_words(rest)}"


def _degrees_plural(n: int) -> str:
    """
    Возвращает правильную форму слова 'градус'.
    """
    try:
        n = abs(int(n))
    except Exception:
        return "градусов"

    n = n % 100

    if 10 < n < 20:
        return "градусов"

    last_digit = n % 10

    if last_digit == 1:
        return "градус"

    if 2 <= last_digit <= 4:
        return "градуса"

    return "градусов"


def _temperature_to_words(temp) -> str:
    """
    Превращает температуру в фразу словами.
    Например:
        5  -> "пять градусов"
        -3 -> "минус три градуса"
    """
    try:
        temp = int(round(float(temp)))
    except Exception:
        return "неизвестная температура"

    number_words = _number_to_words(temp)
    degree_word = _degrees_plural(temp)

    return f"{number_words} {degree_word}"


def _int_from_value(value):
    try:
        return int(round(float(value)))
    except Exception:
        return None


def _load_config() -> dict:
    default_config = {
        "api_key": "",
        "default_city": "Москва"
    }

    try:
        if not os.path.exists(CONFIG_FILE):
            _log_error(f"Файл конфигурации не найден: {CONFIG_FILE}")
            return default_config

        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)

        if not isinstance(config, dict):
            _log_error("config.json должен содержать словарь")
            return default_config

        return config

    except Exception as e:
        _log_error("Ошибка загрузки config.json", e)
        return default_config


def _get_weather(city: str, api_key: str):
    """
    Возвращает (данные, ошибка)
    """
    if requests is None:
        return None, "Не установлен модуль requests. Выполни: pip install requests"

    url = "https://api.openweathermap.org/data/2.5/weather"

    params = {
        "q": city,
        "appid": api_key,
        "units": "metric",
        "lang": "ru"
    }

    try:
        response = requests.get(url, params=params, timeout=10)

        if response.status_code != 200:
            return None, f"HTTP {response.status_code}: {response.text}"

        return response.json(), None

    except requests.exceptions.RequestException as e:
        return None, f"Ошибка сети или запроса: {e}"

    except Exception as e:
        return None, f"Неизвестная ошибка при получении погоды: {e}"


def _extract_city_from_text(text: str):
    try:
        if not text:
            return None

        normalized = vh.normalize(text)

        trigger_words = {
            "погода",
            "какая",
            "какой",
            "скажи",
            "сказать",
            "подскажи",
            "подсказать",
            "узнай",
            "узнать",
            "текущая",
            "сегодня",
            "сейчас",
            "в",
            "городе",
            "для",
            "на",
        }

        words = normalized.split()
        city_words = [word for word in words if word not in trigger_words]

        if city_words:
            return " ".join(city_words)

        return None

    except Exception as e:
        _log_error("Ошибка при извлечении города из фразы", e)
        return None


def weather_command():
    try:
        if requests is None:
            _log_error("Не установлен модуль requests")
            vh.say("Не установлена библиотека для запросов погоды")
            return

        config = _load_config()

        api_key = str(config.get("api_key", "")).strip()
        default_city = str(config.get("default_city", "Москва")).strip()

        if not api_key:
            _log_error(f"API ключ не задан в файле: {CONFIG_FILE}")
            vh.say("Не настроен ключ погоды")
            return

        text = vh.query.get("text", "") or vh.query.get("norm_text", "")
        city = _extract_city_from_text(text)

        if not city:
            vh.say_random([
                "Какой город?",
                "Для какого города узнать погоду?",
                "Назовите город",
            ])

            answer = vh.recognize_online()
            city = _extract_city_from_text(answer)

        if not city:
            city = default_city

        if not city:
            city = "Москва"

        weather_data, error = _get_weather(city, api_key)

        if error:
            _log_error(f"Ошибка получения погоды для города: {city}", error)
            vh.say_random([
                "Не удалось получить погоду",
                "Ошибка при запросе погоды",
                "Не могу узнать погоду",
            ])
            return

        try:
            temp = _int_from_value(weather_data["main"]["temp"])
            feels_like = _int_from_value(weather_data["main"]["feels_like"])
            description = weather_data["weather"][0]["description"]
            city_name = weather_data["name"]

            if temp is None:
                _log_error("Не удалось получить температуру из ответа")
                vh.say("Не удалось разобрать температуру")
                return

            temp_words = _temperature_to_words(temp)

            phrases = [
                f"В городе {city_name} сейчас {temp_words}, {description}",
                f"{city_name}, {description}, {temp_words}",
            ]

            if feels_like is not None:
                feels_like_words = _temperature_to_words(feels_like)

                phrases.append(
                    f"Температура {temp_words}, ощущается как {feels_like_words}"
                )

            vh.say_random(phrases)

        except Exception as parse_error:
            _log_error("Ошибка разбора ответа от погодного сервиса", parse_error)
            _log_error("Ответ сервиса", str(weather_data)[:2000])
            vh.say("Не удалось разобрать данные о погоде")

    except Exception as e:
        _log_error("Неизвестная ошибка в weather_command", e)
        vh.say_random([
            "Произошла ошибка при получении погоды",
            "Плагин погоды завершился с ошибкой",
        ])


intents = {
    "weather": {
        "examples": [
            "какая погода",
            "погода сегодня",
            "погода сейчас",
            "какая погода в москве",
            "погода в санкт-петербурге",
            "скажи погоду",
            "узнай погоду",
            "подскажи погоду",
            "текущая погода",
        ],
        "responses": [
            "узнаю погоду",
            "проверяю погоду",
        ],
        "cmd": weather_command,
    }
}