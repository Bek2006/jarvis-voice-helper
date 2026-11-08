import os
import json
import logging
import subprocess
import time
from core import vh


plugin_dir = os.path.dirname(os.path.abspath(__file__))
intents_path = os.path.join(plugin_dir, "intents.json")

with open(intents_path, "r", encoding="utf-8") as file:
    intents = json.load(file)

try:
    import pyautogui
except ImportError:
    pyautogui = None

config_path = os.path.join(plugin_dir, "config.json")
log_path = os.path.join(plugin_dir, "error.log")

logging.basicConfig(
    filename=log_path,
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

default_config = {
    "enable": {"x": 1271, "y": 340},
    "disable": {"x": 1271, "y": 340},
    "vpn_location": {"x": 233, "y": 513}
}

def load_config():
    if not os.path.exists(config_path):
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(default_config, f, ensure_ascii=False, indent=4)
        return default_config
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)

config = load_config()

ENABLE_KEYWORDS = ["включи", "включить", "активируй", "активировать", "запусти", "запустить"]
DISABLE_KEYWORDS = ["выключи", "выключить", "деактивируй", "деактивировать", "останови", "остановить", "отключи", "отключить"]

def detect_action(text):
    text_lower = text.lower()
    for kw in ENABLE_KEYWORDS:
        if kw in text_lower:
            return "enable"
    for kw in DISABLE_KEYWORDS:
        if kw in text_lower:
            return "disable"
    return None

def toggle_vpn():
    try:
        if pyautogui is None:
            vh.say("Библиотека для управления мышью не установлена, сэр.")
            return

        text = vh.query.get("norm_text", "")
        action = detect_action(text)

        if action is None:
            vh.say("Включить или выключить, сэр?")
            vh.recognize_online()
            text = vh.query.get("norm_text", "")
            action = detect_action(text)

        if action is None:
            vh.say("Я не понял, что нужно сделать с випиэном, сэр.")
            return

        coords = config.get(action, {})
        x = coords.get("x")
        y = coords.get("y")

        if x is None or y is None:
            vh.say("Координаты для випиэна не настроены, сэр.")
            return

        pyautogui.hotkey('winleft', 'd')
        pyautogui.doubleClick(
            config.get("vpn_location").get("x"),
            config.get("vpn_location").get("y"),
            duration=0.5)
        pyautogui.click(x, y, duration=0.5)
        pyautogui.hotkey('winleft', 'down')
        time.sleep(0.1)
        pyautogui.hotkey('winleft', 'tab')
        time.sleep(0.1)
        pyautogui.press('right')
        pyautogui.press('enter')

        if action == "enable":
            vh.say_random([
                "включил випи эн",
                "включил випи эн, сэр",
                "випи эн активирован"
            ])
        else:
            vh.say_random([
                "выключил випи эн",
                "выключил випи эн, сэр",
                "випи эн деактивирован"
            ])

    except Exception as e:
        print(f"Error in toggle_vpn: {e}")
        logging.error(f"toggle_vpn error: {e}")
        vh.say("Произошла ошибка при управлении випиэна, сэр.")

cmds = [toggle_vpn]

for intent, cmd in zip(intents, cmds):
    intents[intent]["cmd"] = cmd
