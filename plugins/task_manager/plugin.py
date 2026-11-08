import json
import os
import time
import logging
import schedule
import threading
from datetime import datetime
from core import vh


plugin_dir = os.path.dirname(os.path.abspath(__file__))
intents_path = os.path.join(plugin_dir, "intents.json")

with open(intents_path, "r", encoding="utf-8") as file:
    intents = json.load(file)

# Логирование
log_dir = os.path.dirname(os.path.abspath(__file__))
log_file = os.path.join(log_dir, 'error.log')

logger = logging.getLogger('task_manager')
logger.setLevel(logging.ERROR)
if not logger.handlers:
    fh = logging.FileHandler(log_file, encoding='utf-8')
    ch = logging.StreamHandler()
    fmt = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fh.setFormatter(fmt); ch.setFormatter(fmt)
    logger.addHandler(fh); logger.addHandler(ch)

DAYS_MAP = {
    "mon": schedule.every().monday,
    "tue": schedule.every().tuesday,
    "wed": schedule.every().wednesday,
    "thu": schedule.every().thursday,
    "fri": schedule.every().friday,
    "sat": schedule.every().saturday,
    "sun": schedule.every().sunday,
}

# Функции для планировщика
from pathlib import Path
# import os
from urllib.parse import quote


def create_folder(folder_path: str):
    path = Path(folder_path)
    if path.exists():
        va.say(f"Папка уже существует.")
    else:
        va.say("Создаю папку")
        path.mkdir(parents=True)  # parents=True создаст и вложенные родительские папки
        va.say(f"Папка успешно создана.")


def create_file(file_path: str):
    path = Path(file_path)
    if path.exists():
        va.say(f"Файл уже существует.")
    else:
        va.say("Создаю файлы")
        path.touch()
        va.say(f"Файл успешно создан.")


def prepare_for_edu_session(folder_path: str, file_path: str,
                            obsidian_vault: str, obsidian_file_path: str):
    va.say("через 5 минут у вас занятие в вузе")
    va.say("Хотите, чтобы я подготовился к нему?")
    va.say("Если да, то позовите меня и скажите да")

    print("[Планировщик] Подготовка к занятию в вузе. Позовите и скажите да или нет")
    va.detect_wake_word()
    va.say("Хотите, чтобы я подготовился к занятию в вузе?")
    answer = va.recognize_online().lower()

    if "да" in answer:
        create_folder(folder_path)
        create_file(file_path)
        va.say("Я сделал необходимые приготовления")
        va.say("Открываю вам обсидиан с нужным файлом")
        os.system(f'start "" "obsidian://open?vault={quote(obsidian_vault)}&file={quote(obsidian_file_path)}"')
        va.say("Открыл, сэр")
    else:
        va.say("Хорошо, сэр")

    va.say("Удачи вам в занятии")

# Конец функций для планировщика


def setup_tasks():
    """
    Определяйте свои задачи здесь.
    Пример:
        create_task(
            func=my_func,
            time="08:00",
            period="mon|tue|wed|thu|fri",
            start_date="01.01.2026",
            end_date="31.12.2026"
        )
    """

    create_task(
        )
    pass


class TaskManager:
    """Менеджер планировщика. Хранит состояние внутри класса."""
    _instance = None
    _stop_event = None
    _thread = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def start(self):
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event = threading.Event()

        class ScheduleThread(threading.Thread):
            def __init__(self, stop_event):
                super().__init__(daemon=True)
                self.stop_event = stop_event

            def run(self):
                while not self.stop_event.is_set():
                    schedule.run_pending()
                    time.sleep(60)

        setup_tasks()

        self._thread = ScheduleThread(self._stop_event)
        self._thread.start()

    def shutdown(self):
        if self._stop_event is not None:
            self._stop_event.set()
        schedule.clear()
        self._thread = None
        self._stop_event = None
        print("[Планировщик] Остановлен и очищен.")


def _parse_date(s):
    return datetime.strptime(s, "%d.%m.%Y")


def _parse_period(period_str):
    parts = [p.strip().lower() for p in period_str.split("|") if p.strip()]
    return [DAYS_MAP[p] for p in parts if p in DAYS_MAP]


def create_task(func, time_str, period="mon|tue|wed|thu|fri|sat|sun",
                start_date=None, end_date=None):
    """
    Создаёт задачу в планировщике.
    :param func: функция без аргументов
    :param time_str: время "HH:MM"
    :param period: дни недели через "|", например "mon|wed|fri"
    :param start_date: дата начала "DD.MM.YYYY" (или None)
    :param end_date: дата конца "DD.MM.YYYY" (или None)
    """
    try:
        start_dt = _parse_date(start_date) if start_date else None
        end_dt = _parse_date(end_date) if end_date else None
        day_builders = _parse_period(period)

        if not day_builders:
            logger.error(f"Не указаны корректные дни недели: {period}")
            return

        expired_logged = [False]
        task_name = getattr(func, '__name__', 'task')

        def wrapper():
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            if start_dt and today < start_dt:
                return
            if end_dt and today > end_dt:
                if not expired_logged[0]:
                    print(f"[Планировщик] Задача '{task_name}' перестала вызываться: время истекло.")
                    expired_logged[0] = True
                return
            try:
                func()
            except Exception as e:
                logger.error(f"Ошибка в задаче {task_name}: {e}")

        for day_builder in day_builders:
            day_builder.at(time_str).do(wrapper)

        print(f"[Планировщик] Задача '{task_name}' добавлена на {time_str} ({period}).")
    except Exception as e:
        logger.error(f"Ошибка создания задачи: {e}")


def run_task_manager():
    """Активация планировщика."""
    try:
        manager = TaskManager.get_instance()
        manager.start()
        vh.say_random([
            "планировщик задач активирован, сэр",
            "планировщик запущен, сэр",
            "готов выполнять задачи по расписанию, сэр"
        ])
    except Exception as e:
        logger.error(f"Ошибка активации планировщика: {e}")
        vh.say("Произошла ошибка при активации планировщика")


def shutdown():
    """Завершение работы планировщика."""
    try:
        TaskManager.get_instance().shutdown()
    except Exception as e:
        logger.error(f"Ошибка при завершении планировщика: {e}")


cmds = [run_task_manager]

for intent, cmd in zip(intents, cmds):
    intents[intent]["cmd"] = cmd


shutdowns = [shutdown]

for intent, shut in zip(intents, shutdowns):
    intents[intent]["shutdown"] = shut
