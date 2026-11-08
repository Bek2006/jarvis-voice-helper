import json
import os
import sys
import importlib
import logging
from core import vh


plugin_dir = os.path.dirname(os.path.abspath(__file__))
intents_path = os.path.join(plugin_dir, "intents.json")

with open(intents_path, "r", encoding="utf-8") as file:
    intents = json.load(file)

log_path = os.path.join(plugin_dir, "error.log")

logging.basicConfig(
    filename=log_path,
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def restart_plugin():
    try:
        vh.say_random([
            "Какой плагин нужно перезагрузить?",
            "Какой плагин перезагрузить, сэр?",
            "Назовите плагин для перезагрузки.",
            "Какой модуль обновить?"
        ])

        plugin_name = input("Напишите название плагина > ").strip().lower()

        if not plugin_name:
            vh.say("Название не указано, сэр.")
            return

        module_path = f"plugins.{plugin_name}.plugin"

        if module_path in sys.modules:
            plugin = importlib.reload(sys.modules[module_path])
        else:
            plugin = importlib.import_module(module_path)

        new_intents = getattr(plugin, "intents", {})
        if hasattr(vh, "intents") and isinstance(vh.intents, dict):
            vh.intents.update(new_intents)

        vh.say_random([
            f"плагин {plugin_name} перезагружен",
            f"плагин {plugin_name} успешно обновлён, сэр",
            f"готово, плагин {plugin_name} перезапущен"
        ])
    except ModuleNotFoundError:
        logging.error(f"Plugin not found: {plugin_name}")
        vh.say("Такой плагин не найден, сэр.")
    except Exception as e:
        print(f"Error in restart_plugin: {e}")
        logging.error(f"restart_plugin error: {e}")
        vh.say("Не удалось перезагрузить плагин, сэр.")


cmds = [restart_plugin]

for intent, cmd in zip(intents, cmds):
    intents[intent]["cmd"] = cmd
