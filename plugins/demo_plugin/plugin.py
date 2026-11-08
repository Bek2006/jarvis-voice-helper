import json
import os.path
from core import vh


plugin_dir = os.path.dirname(os.path.abspath(__file__))
intents_path = os.path.join(plugin_dir, "intents.json")

with open(intents_path, "r", encoding="utf-8") as file:
    intents = json.load(file)


def f():
    """
    Обязательная функция,
    которая выполняет определенный функционал,
    подробно сообщая на каком этапе исполнения находится.
    К примеру, открывание программы, запуск определенных скриптов и т.п.
    """
    pass


def shutdown():
    """
    Необязательная функция,
    которая будет вызываться при выключении
    для завершение работы этого плагина.
    К примеру, закрытие файлов, потоков и т.п.
    """
    pass


cmds = [f]

for intent, cmd in zip(intents, cmds):
    intents[intent]["cmd"] = cmd


shutdowns = [shutdown]

for intent, shut in zip(intents, shutdowns):
    intents[intent]["shutdown"] = shut
