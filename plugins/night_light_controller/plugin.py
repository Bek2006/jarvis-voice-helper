import os
import json
import logging
from core import vh


plugin_dir = os.path.dirname(os.path.abspath(__file__))
intents_path = os.path.join(plugin_dir, "intents.json")

with open(intents_path, "r", encoding="utf-8") as file:
    intents = json.load(file)

try:
    import tinytuya
    import requests
except ImportError:
    tinytuya = None
    requests = None

config_path = os.path.join(plugin_dir, "config.json")
log_path = os.path.join(plugin_dir, "error.log")

logging.basicConfig(
    filename=log_path,
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

default_config = {
    "apiRegion": "eu",
    "apiKey": "your_api_key",
    "apiSecret": "your_api_secret",
    "apiDeviceID": "your_device_id"
}


def load_config():
    if not os.path.exists(config_path):
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(default_config, f, ensure_ascii=False, indent=4)
        return default_config

    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def control_night_light():
    try:
        if tinytuya is None:
            vh.say("Библиотека tinytuya не установлена, сэр.")
            return

        text = vh.query.get("norm_text", "")
        action = "off" if "выключ" in text else "on"

        config = load_config()

        if config.get("apiKey") == "your_api_key":
            vh.say("Настройки ночника не заполнены, сэр.")
            return

        cloud = tinytuya.Cloud(
            apiRegion=config["apiRegion"],
            apiKey=config["apiKey"],
            apiSecret=config["apiSecret"]
        )

        device_id = config["apiDeviceID"]

        status = cloud.getstatus(device_id)

        value = True if action == "on" else False
        commands = {
            "commands": [
                {"code": "switch_1", "value": value}
            ]
        }

        result = cloud.sendcommand(device_id, commands)

        if action == "on":
            vh.say("включил, сэр")
        else:
            vh.say("выключил, сэр")

    except requests.exceptions.ConnectionError:
        vh.say("Нет подключения к интернету, сэр.")
    except Exception as e:
        print(f"Error in control_night_light: {e}")
        logging.error(f"control_night_light error: {e}")
        vh.say("Не удалось управлять ночником, сэр.")


cmds = [control_night_light]

for intent, cmd in zip(intents, cmds):
    intents[intent]["cmd"] = cmd
