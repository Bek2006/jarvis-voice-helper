import os
import json
import webbrowser
import subprocess
import logging
from core import vh

try:
    from num2words import num2words
    def number_to_words(num):
        return num2words(num, lang='ru')
except ImportError:
    def number_to_words(num):
        return str(num)

plugin_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(plugin_dir, "config.json")
log_path = os.path.join(plugin_dir, "error.log")

logging.basicConfig(
    filename=log_path,
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

default_config = {
    "websites": {
        "ютуб": "https://www.youtube.com",
        "гугл": "https://www.google.com",
        "яндекс": "https://www.yandex.ru"
    },
    "programs": {
        "блокнот": "notepad.exe",
        "калькулятор": "CalculatorApp.exe",
        "проводник": "explorer.exe",
        "командный строка": "cmd.exe"
    },
    "processes": {
        "блокнот": "notepad.exe",
        "калькулятор": "CalculatorApp.exe",
        "проводник": "explorer.exe",
        "командный строка": "cmd.exe"
    }
}


def load_config():
    if not os.path.exists(config_path):
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(default_config, f, ensure_ascii=False, indent=4)
        return default_config
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)

config = load_config()

OPEN_KEYWORDS = ["открой", "открыть", "запусти", "запустить", "открывай", "запускай"]
CLOSE_KEYWORDS = ["закрой", "закрыть", "закрывай", "завершить", "заверши"]
ALL_KEYWORDS = OPEN_KEYWORDS + CLOSE_KEYWORDS


def clean_text(text):
    for word in ALL_KEYWORDS:
        text = text.replace(word, "")
    extra = ["сайт", "программу", "программа", "приложение",
             "пожалуйста", "сэр"]
    for word in extra:
        text = text.replace(word, "")
    return text.strip()


def detect_action(text):
    text_lower = text.lower()
    for kw in OPEN_KEYWORDS:
        if kw in text_lower:
            return "open"
    for kw in CLOSE_KEYWORDS:
        if kw in text_lower:
            return "close"
    return None


def ask_action():
    vh.say("Что сделать: открыть или закрыть, сэр?")
    vh.recognize_online()
    text = vh.query.get("norm_text", "")
    return detect_action(text)


def ask_target(action):
    if action == "close":
        vh.say("Что именно закрыть, сэр?")
    else:
        vh.say("Что именно открыть, сэр?")
    vh.recognize_online()
    return vh.query.get("norm_text", "")


def get_target(action):
    text = vh.query.get("norm_text", "")
    target = clean_text(text)

    is_valid = (target in config.get("websites", {}) or
                target in config.get("programs", {}) or
                target in config.get("processes", {}))

    if not target or not is_valid:
        text = ask_target(action)
        target = clean_text(text)
    return target


def do_open(target):
    if target in config.get("websites", {}):
        url = config["websites"][target]
        webbrowser.open(url)
        vh.say_random([
            f"открываю {target}",
            f"открываю {target}, сэр"
        ])
    elif target in config.get("programs", {}):
        prog = config["programs"][target]
        subprocess.Popen(["start", prog], shell=True)
        vh.say_random([
            f"запускаю {target}",
            f"запускаю {target}, сэр"
        ])
    else:
        vh.say(f"Не знаю, как открыть {target}, сэр.")


def do_close(target):
    proc_name = config.get("processes", {}).get(target)
    if not proc_name and target in config.get("programs", {}):
        proc_name = config["programs"][target]

    if not proc_name:
        vh.say(f"Не знаю, как закрыть {target}, сэр.")
        return

    subprocess.run(["taskkill", "/IM", proc_name, "/F"],
                   check=True, capture_output=True)

    vh.say_random([
        f"закрываю {target}",
        f"закрываю {target}, сэр"
    ])


def touch_app():
    try:
        text = vh.query.get("norm_text", "")
        action = detect_action(text)

        if action is None:
            action = ask_action()

        if action is None:
            vh.say("Я не понял, что нужно сделать, сэр.")
            return

        target = get_target(action)
        if not target:
            vh.say("Я не расслышал название, сэр.")
            return

        if action == "open":
            do_open(target)
        else:
            do_close(target)

    except Exception as e:
        print(f"Error in touch_app: {e}")
        logging.error(f"touch_app error: {e}")
        vh.say("Произошла ошибка, сэр.")


intents = {
    "touch_app": {
        "examples": [
            "открой ютуб",
            "закрыть ютуб",
            "запусти блокнот",
            "открой сайт гугл",
            "открыть калькулятор",
            "закрыть калькулятор",
            "закрой программу калькулятор",
            "закрой блокнот",
            "открыть командная строка",
            "открыть командную строку",
            "закрой командную строку",
            "закрыть командная строка",
            "открой проводник",
            "открыть проводник",
            "закрыть проводник",
            "открыть telegram",
            "закрыть telegram"
        ],
        "responses": [
            "открываю",
            "запускаю",
            "закрываю"
        ],
        "cmd": touch_app
    }
}
