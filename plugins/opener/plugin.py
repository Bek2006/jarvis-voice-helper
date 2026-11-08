"""Открытие объектов и распознавание команд без выполнения текста оболочкой."""

import json
import logging
import os
from pathlib import Path
import re
import subprocess
import time
import webbrowser

import keyboard
from thefuzz import fuzz

from core import vh


plugin_dir = Path(__file__).resolve().parent
config_path = plugin_dir / "config.json"
intents_path = plugin_dir / "intents.json"
logger = logging.getLogger(__name__)

ACTION_THRESHOLD = 85
TYPE_THRESHOLD = 90
APP_THRESHOLD = 85
AMBIGUITY_MARGIN = 8
ACTION_ALIASES = {
    "open": ["открой", "открыть", "запусти", "запустить"],
    "close": ["закрой", "закрыть", "заверши", "завершить"],
}
TYPE_ALIASES = {
    "file": ["файл"],
    "folder": ["папка", "папку", "папк"],
    "website": ["сайт"],
    "program": ["программа", "программу", "приложение"],
}
CATEGORIES = {"website": "websites", "program": "programs"}
started_programs = {}


def _load_json(path):
    """Ошибки загрузки доступны разработчику через локальный logger."""
    try:
        with path.open(encoding="utf-8") as file:
            data = json.load(file)
        if not isinstance(data, dict):
            raise ValueError("В корне JSON должен быть объект")
        return data
    except (OSError, ValueError):
        logger.exception("Не удалось загрузить %s", path)
        return {}


def load_config():
    data = _load_json(config_path)
    try:
        for category in CATEGORIES.values():
            for name, item in data.get(category, {}).items():
                field = "url" if category == "websites" else "exe"
                if not isinstance(item, dict):
                    raise ValueError(f"Некорректный объект: {name}")
                if not isinstance(item.get(field), str) or not item[field]:
                    raise ValueError(f"Не задано {field}: {name}")
                aliases = item.get("aliases")
                if not isinstance(aliases, list) or not aliases or not all(
                    isinstance(alias, str) and alias.strip()
                    for alias in aliases
                ):
                    raise ValueError(f"Некорректные aliases: {name}")
                if "process" in item and not isinstance(item["process"], str):
                    raise ValueError(f"Некорректный process: {name}")
        return data
    except (AttributeError, ValueError):
        logger.exception("Некорректная конфигурация %s", config_path)
        return {}


config = load_config()
intents = _load_json(intents_path)
if not all(
    isinstance(item, dict)
    and isinstance(item.get("examples"), list)
    and all(isinstance(example, str) for example in item["examples"])
    and isinstance(item.get("responses"), list)
    and item.get("cmd") == "touch_app"
    for item in intents.values()
):
    logger.error("Некорректная структура намерений в %s", intents_path)
    intents = {}


def _normalize(text):
    return " ".join(text.casefold().split())


def _words(text):
    return re.findall(r"[\w-]+", _normalize(text))


def _word_score(alias, word):
    # Не считаем короткую подстроку внутри длинного слова совпадением.
    if abs(len(alias) - len(word)) > 2:
        return 0
    return fuzz.partial_ratio(alias, word)


def _best_match(scores, threshold):
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    if not ranked or ranked[0][1] < threshold:
        return None
    if len(ranked) > 1 and ranked[0][1] - ranked[1][1] < AMBIGUITY_MARGIN:
        return None
    return ranked[0][0]


def _action_words(text):
    matches = []
    for word in _words(text):
        scores = {
            action: max(_word_score(alias, word) for alias in aliases)
            for action, aliases in ACTION_ALIASES.items()
        }
        action = _best_match(scores, ACTION_THRESHOLD)
        if action:
            matches.append((word, action))
    return matches


def _blocked(text):
    words = set(_words(text))
    return bool(words & {"не", "ни", "нельзя", "отмена", "отмени"}) or len(
        _action_words(text)
    ) > 1


def _detect_type(text, explicit_only=False):
    scores = {
        kind: max(
            (_word_score(alias, word) for alias in aliases
             for word in _words(text)),
            default=0,
        )
        for kind, aliases in TYPE_ALIASES.items()
        if not explicit_only or kind in {"file", "folder"}
    }
    return _best_match(scores, TYPE_THRESHOLD)


def _path_name(text):
    # Удаляем только служебный префикс; регистр, точки и слеши сохраняем.
    words = text.strip().split()
    actions = {word for aliases in ACTION_ALIASES.values() for word in aliases}
    types = {word for aliases in TYPE_ALIASES.values() for word in aliases}
    while words:
        word = words[0].casefold().strip(",")
        if word in {"пожалуйста", "сэр"} or any(
            _word_score(alias, word) >= ACTION_THRESHOLD for alias in actions
        ) or word in types:
            words.pop(0)
        else:
            break
    while words and words[-1].casefold().strip(",") in {"пожалуйста", "сэр"}:
        words.pop()
    return " ".join(words).strip().strip('"«»') or None


def _app_score(alias, text):
    alias_words = _words(alias)
    words = _words(text)
    scores = []
    for start in range(len(words) - len(alias_words) + 1):
        candidate = words[start:start + len(alias_words)]
        if all(
            abs(len(a) - len(b)) <= 2
            for a, b in zip(alias_words, candidate)
        ):
            scores.append(fuzz.partial_ratio(
                " ".join(alias_words), " ".join(candidate),
            ))
    return max(scores, default=0)


def parse_command(text):
    """Возвращает действие, тип и имя; неоднозначные параметры равны None."""
    if _blocked(text):
        return None, None, None
    normalized = _normalize(text)
    matches = _action_words(text)
    action = matches[0][1] if matches else None
    kind = _detect_type(text, explicit_only=True)
    if kind:
        return action, kind, _path_name(text)
    # Два явных типа нельзя подменять совпадением с программой.
    if any(word in {"файл", "папка", "папку"} for word in _words(text)):
        return action, None, None
    scores = {}
    for category, kind in (("websites", "website"), ("programs", "program")):
        for name, item in config.get(category, {}).items():
            scores[kind, name] = max(
                (_app_score(alias, normalized) for alias in item["aliases"]),
                default=0,
            )
    target = _best_match(scores, APP_THRESHOLD)
    return (action, *target) if target else (action, None, None)


def _ask(question):
    vh.say(question)
    vh.query["text"] = ""
    vh.query["norm_text"] = ""
    answer = vh.recognize_online()
    # Ядро возвращает строку, но само query не обновляет.
    if isinstance(answer, str):
        vh.query["text"] = answer
        vh.query["norm_text"] = vh.normalize(answer)
    return vh.query.get("norm_text", "")


def ask_action():
    return parse_command(_ask("Открыть или закрыть, сэр?"))[0]


def ask_type():
    text = _ask("Что это: файл, папка, сайт или программа, сэр?")
    if _blocked(text):
        return None
    return _detect_type(text) or parse_command(text)[1]


def ask_app_name():
    text = _ask("Что именно, сэр?")
    if _blocked(text):
        return None
    # Исходный ответ нужен для сохранения регистра и пунктуации путей.
    raw_text = vh.query.get("text") or text
    return parse_command(raw_text)[2] or _path_name(raw_text)


def open_app(type, app_name):
    """Открывает объект; сообщает результат и возвращает признак успеха."""
    try:
        if type == "website":
            item = config.get("websites", {}).get(app_name)
            if not item:
                raise ValueError("Сайт отсутствует в config.json")
            if not webbrowser.open(item["url"]):
                raise OSError("Браузер не принял запрос на открытие")
        elif type == "program":
            item = config.get("programs", {}).get(app_name)
            if not item:
                raise ValueError("Программа отсутствует в config.json")
            started_programs[app_name] = subprocess.Popen([item["exe"]])
        elif type in {"file", "folder"}:
            if os.name != "nt":
                raise OSError("Поиск через клавишу Win доступен только в Windows")
            keyboard.send("windows")
            time.sleep(0.3)
            keyboard.write(f"{type}: {app_name or ''}")
            vh.say("Поиск подготовлен, сэр.")
            return True
        else:
            raise ValueError("Неизвестный тип объекта")
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        logger.exception("Ошибка открытия %r (%s)", app_name, type)
        vh.say(f"Не удалось открыть: {error}")
        return False
    vh.say(f"Запрос на открытие {app_name} отправлен, сэр.")
    return True


def close_app(type, app_name):
    """Закрывает программу без принудительного завершения."""
    if type in {"website", "file", "folder"}:
        vh.say(
            "Не могу надёжно выбрать и закрыть только эту вкладку "
            "или окно, сэр."
        )
        return False
    item = config.get("programs", {}).get(app_name)
    if type != "program" or not item:
        vh.say("Программа отсутствует в config.json, сэр.")
        return False
    try:
        if os.name == "nt":
            process = item.get("process")
            if not process:
                raise ValueError("Не задано имя процесса в config.json")
            subprocess.run(
                ["taskkill", "/IM", process], check=True, capture_output=True,
            )
        else:
            process = started_programs.get(app_name)
            if process is None or process.poll() is not None:
                vh.say(
                    "Могу закрыть только программу, "
                    "запущенную этим плагином, сэр."
                )
                return False
            process.terminate()
            process.wait(timeout=3)
            del started_programs[app_name]
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        logger.exception("Ошибка закрытия %r", app_name)
        vh.say(f"Не удалось закрыть программу: {error}")
        return False
    vh.say(f"Запрос на закрытие {app_name} отправлен, сэр.")
    return True


def touch_app(action=None, type=None, app_name=None):
    """Уточняет недостающие параметры один раз и выполняет одну команду."""
    text = vh.query.get("norm_text", "")
    if _blocked(text):
        vh.say(
            "Команда отменена: произнесите одно действие без отрицания, сэр."
        )
        return
    parsed_action, parsed_type, parsed_name = parse_command(text)
    action = action if action is not None else parsed_action
    type = type if type is not None else parsed_type
    app_name = app_name if app_name is not None else parsed_name
    if type in {"file", "folder"} and app_name == parsed_name:
        raw_text = vh.query.get("text", "")
        if raw_text and vh.normalize(raw_text) == text:
            app_name = parse_command(raw_text)[2]
    if action is None:
        action = ask_action()
        if action is None:
            vh.say("Не удалось определить действие, сэр.")
            return
    if type is None:
        type = ask_type()
        if type is None:
            vh.say("Не удалось определить тип объекта, сэр.")
            return
    search_without_name = action == "open" and type in {"file", "folder"}
    if app_name is None and not search_without_name:
        app_name = ask_app_name()
    if _blocked(vh.query.get("norm_text", "")):
        vh.say("Команда отменена, сэр.")
        return
    if (
        action not in ACTION_ALIASES
        or type not in TYPE_ALIASES
        or (not app_name and not search_without_name)
    ):
        vh.say("Не удалось определить команду, сэр.")
        return
    if action == "open":
        open_app(type, app_name)
    else:
        close_app(type, app_name)


cmds = [touch_app]

for intent, cmd in zip(intents, cmds):
    intents[intent]["cmd"] = cmd
