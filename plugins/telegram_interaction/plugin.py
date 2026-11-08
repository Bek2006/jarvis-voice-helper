import os
import json
import logging
import asyncio
from core import vh

try:
    from telethon import TelegramClient
except ImportError:
    TelegramClient = None

plugin_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(plugin_dir, "config.json")
log_path = os.path.join(plugin_dir, "error.log")
session_path = os.path.join(plugin_dir, "session")

logging.basicConfig(
    filename=log_path,
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

default_config = {
    "api_id": 123456,
    "api_hash": "your_api_hash_here",
    "contacts": {
        "мама": "+1234567890",
        "папа": "@username"
    },
    "groups": {
        "родителям": "family_group",
        "в группу": "my_group"
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

def extract_recipient_and_message(text):
    text_lower = text.lower()
    
    keywords = ["напиши", "сообщи", "отправь", "написать", "сообщить", "отправить"]
    for kw in keywords:
        if kw in text_lower:
            text_lower = text_lower.replace(kw, "").strip()
            break
    
    if "что" in text_lower:
        parts = text_lower.split("что", 1)
        recipient = parts[0].strip()
        message = parts[1].strip() if len(parts) > 1 else ""
        return recipient, message
    
    return "", ""

def send_telegram_message():
    try:
        if TelegramClient is None:
            vh.say("Библиотека для телеграм не установлена, сэр.")
            return
        
        text = vh.query.get("norm_text", "")
        recipient, message = extract_recipient_and_message(text)
        
        if not recipient:
            vh.say("Кому написать, сэр?")
            vh.recognize_online()
            text = vh.query.get("norm_text", "")
            recipient, message = extract_recipient_and_message(text)
        
        if not message:
            vh.say("Что написать, сэр?")
            vh.recognize_online()
            text = vh.query.get("norm_text", "")
            _, message = extract_recipient_and_message(text)
        
        if not recipient or not message:
            vh.say("Не понял, что и кому написать, сэр.")
            return
        
        target = None
        target_name = recipient
        
        if recipient in config.get("contacts", {}):
            target = config["contacts"][recipient]
        elif recipient in config.get("groups", {}):
            target = config["groups"][recipient]
        
        if not target:
            vh.say(f"Не знаю, кто такой {recipient}, сэр.")
            return
        
        api_id = config.get("api_id")
        api_hash = config.get("api_hash")
        
        if not api_id or not api_hash or api_id == 123456:
            vh.say("Настройки телеграм не заполнены, сэр.")
            return
        
        client = TelegramClient(session_path, api_id, api_hash)
        
        async def send():
            await client.start()
            await client.send_message(target, message)
            await client.disconnect()

        asyncio.run(send())
        
        vh.say_random([
            f"написал {target_name}, что {message}",
            f"сообщение отправлено {target_name}",
            f"написал {target_name}, сэр"
        ])
    except Exception as e:
        print(f"Error in send_telegram_message: {e}")
        logging.error(f"send_telegram_message error: {e}")
        vh.say("Не удалось отправить сообщение, сэр.")

intents = {
    "send_telegram": {
        "examples": [
            "напиши что я дома",
            "сообщи родителям что",
            "напиши в группу что",
            "написать что я дом",
            "сообщить родитель что",
            "написать в группа что",
        ],
        "responses": [
            "пишу",
            "отправляю",
            "сообщаю"
        ],
        "cmd": send_telegram_message
    }
}
