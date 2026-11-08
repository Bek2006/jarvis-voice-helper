import re
import sys
import json
import random
import os.path
from pathlib import Path

from pymorphy3 import MorphAnalyzer  # Для лемматизации

import speech_recognition as sr  # Для Speech-To-Text

import vosk  # Для распознавания речи без доступа  к интернету
import wave

# Для Text-To-Speech
import torch
from torch.package import PackageImporter  # Для загрузки TTS Модели
import sounddevice as sd
import soundfile as sf
import numpy as np

# Для Wake Word Detection
import pyaudio
# import numpy as np
from openwakeword.model import Model

# Для загрузки плагинов
import importlib

# Для красочного вывода
from termcolor import cprint
from colorama import init
init()

import thefuzz.process  # Для нечеткого стравнения
import thefuzz.fuzz     #

lemmatizer = MorphAnalyzer()

recognizer = sr.Recognizer()
microphone = sr.Microphone()  # Микрофон

# root
root = str(Path(__file__).parent)

# Выключаем логирование от vosk
vosk.SetLogLevel(-1)
model = vosk.Model(model_path=os.path.join(root, "vosk_small_ru_model"))

# Загрузка модели
wake_model = Model(wakeword_models=["hey_jarvis"], inference_framework="onnx")

# Инициализация pyaudio
p = pyaudio.PyAudio()

# Настройка аудио
FORMAT = pyaudio.paInt16
CHUNK = 1280
CHANNELS = 1
RATE = 16000
# Открытие потока
stream = p.open(
    format=FORMAT,
    channels=CHANNELS,
    rate=RATE,
    input=True,
    frames_per_buffer=CHUNK
)

# Настройка голоса
model_path = os.path.join(root, r"silero_tts_model\v5_5_ru.pt")
importer = PackageImporter(model_path)
silero_model = importer.load_pickle("tts_models", "model")
silero_model.to(torch.device('cpu'))

# Список wav-файлов для фраз
sounds = os.path.join(root, "sounds")
phrase_files = set(os.listdir(sounds))


# Для корректировки названия файлов
def sanitize_filename(filename):
    # Для Windows: < > : " / \ | ? *
    # Для Linux/macOS: / (и некоторые другие)
    return re.sub(r'[<>:"/\\|?*]', '_', filename)


class VoiceHelper:
    """Экземпляр класса VoiceHelper позволяет делать следующее:

        1) Удалять все символы кроме букв и пробела
            с помощью метода normalize_char(self, phrase: str) -> str

        2) Каждое русское слово превращать в начальную форму
            с помощью метода lemmatize(self, phrase: str) -> str

        3) Метод normalize(self, phrase) -> str эквивалентен
            lemmatize(self, normalize_char(self, phrase: str))

        4) Воспроизводить русскую речь на основе написанного текста на русском
            с помощью метода say(self, phrase: str) -> None

        5) Воспроизводить случайную фразу из предложенных в списке написанных на русском
            с помощью метода say_random(self, phrases: [tuple, list, set, frozenset]) -> None

        6) Распознавать русскую речь
            с помощью  метода recognize_online(self, phrases: [tuple, list, set, frozenset]=None) -> str
            (с помощью интернета)

        7) Распознавать русскую речь
            с помощью  метода recognize_offline(self, data: bytes, phrases: [tuple, list, set, frozenset]=None) -> str
            (без интернета)
        8) Детектировать активационную фразу "hey Jarvis"
            с помощью метода detect_wake_word(self, threshold=0.1) -> bool
    """
    def __init__(self):
        self.plugins_path = os.path.join(root, "plugins")
        self.intents = {}
        self.query = {
            "text": "",
            "norm_text": "",
            "intent": {}
        }
        self.listen_phrases = [
            "да?",
            "да, сэр?",
            "слушаю",
            "слушаю, сэр",
            "чем могу помочь, сэр?",
            # "могу ли я помочь чем-нибудь вам",
            # "могу ли я помочь чем-нибудь",
            # "могу ли я помочь чем-нибудь, сэр",
            # "могу ли я помочь",
            # "чем могу помочь",
            # "чем я могу помочь",
            # "чем я могу помочь, сэр",
            # "чем-нибудь помочь вам",
            # "чем-нибудь помочь вам, сэр",
            # "чем-нибудь помочь",
        ]
        self.ready_phrases = [
            "Я готов, сэр"
        ]
        self.thinking_phrases = [
            "дайте подумать",
            "дайте подумать, сэр",
            "одну минуту",
            "одну минуту, сэр",
            "генерирую ответ",
            "генерирую ответ, сэр",
            "секундочку",
            "секундочку, сэр",
            "формулирую мысль",
            "формулирую мысль, сэр",
            "дайте сформулировать мысль",
            "дайте сформулировать мысль, сэр",
        ]

    # ----- Natural-Language-Processing ----- #

    def normalize_char(self, phrase: str) -> str:
        assert isinstance(phrase, str), 'type of "phrase" must be "str"'

        pattern = re.compile("[^а-яА-ЯA-Za-z ]")
        return pattern.sub("", phrase.lower())

    def lemmatize(self, phrase: str) -> str:
        assert isinstance(phrase, str), 'type of "phrase" must be "str"'

        return " ".join(
            (lemmatizer.normal_forms(word)[0] for word in phrase.split())
        )

    def normalize(self, phrase) -> str:
        assert isinstance(phrase, str), 'type of "phrase" must be "str"'

        return self.lemmatize(self.normalize_char(phrase))

    # ----- Text-To-Speech ----- #

    def generate_voice(self, phrase, phrase_abspath) -> None:
        silero_model.save_wav(
            text=phrase,
            speaker="eugene",
            audio_path=phrase_abspath)

    def generate_voices(self, phrases):
        for phrase in phrases:
            phrase_file = sanitize_filename(phrase) + ".wav"
            if phrase_file in phrase_files: continue
            phrase_abspath = os.path.join(sounds, phrase_file)
            self.generate_voice(phrase, phrase_abspath)

    def say_thinking_phrase(self, wait=True):
        thinking_phrase = random.choice(self.thinking_phrases)
        thinking_phrase_file = thinking_phrase + ".wav"
        phrase_abspath = os.path.join(sounds, thinking_phrase_file)

        if thinking_phrase_file not in phrase_files:
            self.generate_voice(thinking_phrase, phrase_abspath)
            phrase_files.add(thinking_phrase_file)

        phrase_data, fs = sf.read(phrase_abspath, dtype='float32')

        # Добавляем 0.5 секунды тишины в конец wav-файлов
        silence = np.zeros(int(fs * 0.5))

        # Проигрываем аудио
        sd.play(np.concatenate((phrase_data, silence)), fs)
        if wait: sd.wait()  # Ждем окончания воспроизведения
        cprint(f"Jarvis> {thinking_phrase}", "light_cyan")

    def say(self, phrase: str) -> None:
        assert isinstance(phrase, str), 'type of "phrase" must be "str"'

        phrase_file = sanitize_filename(phrase) + ".wav"
        phrase_abspath = os.path.join(sounds, phrase_file)

        if phrase_file not in phrase_files:
            self.say_thinking_phrase(wait=False)
            self.generate_voice(phrase, phrase_abspath)
            phrase_files.add(phrase_file)
            sd.wait()

        phrase_data, fs = sf.read(phrase_abspath, dtype='float32')

        # Добавляем 0.5 секунды тишины в конец wav-файлов
        silence = np.zeros(int(fs * 0.5))

        # Проигрываем аудио
        sd.play(np.concatenate((phrase_data, silence)), fs)
        cprint(f"Jarvis> {phrase}", "light_cyan")
        sd.wait()  # Ждем окончания воспроизведения

    def say_random(self, phrases: [tuple, list, set, frozenset]) -> None:
        assert isinstance(phrases, (tuple, list, set, frozenset)), \
            'type of "phrases" must be (tuple | list | set | frozenset)'

        if phrases:  # <=> len(phrases) != 0
            self.say(random.choice(phrases))

    # ----- Speech-To-Text ----- #

    def recognize_online(self, phrases: [tuple, list, set, frozenset]=None) -> str:
        assert isinstance(phrases, (tuple, list, set, frozenset, type(None))), \
            'type of "phrases" must be (tuple | list | set | frozenset)'

        with microphone as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.2)

            if phrases is None:
                cprint("Jarvis is listenning...",  "cyan")
            else:
                self.say_random(phrases)

            audio = recognizer.listen(source)

            try:
                return recognizer.recognize_google(audio, language="ru-RU")
            except (sr.UnknownValueError, sr.RequestError):
                return self.recognize_offline(audio.get_wav_data())

    def recognize_offline(self, data: bytes, phrases: [tuple, list, set, frozenset]=None) -> str:
        assert isinstance(phrases, (tuple, list, set, frozenset, type(None))), \
            'type of "phrases" must be (tuple | list | set | frozenset)'

        wav_file = os.path.join(sounds, "wav_data_for_recognize_online.wav")

        with open(wav_file, "wb") as f:
            f.write(data)

        with wave.open(wav_file, "rb") as wf:
            rec = vosk.KaldiRecognizer(model, wf.getframerate())

            data = wf.readframes(4000)
            while data:
                rec.AcceptWaveform(data)
                data = wf.readframes(4000)
            return json.loads(rec.FinalResult())["text"]

    # ----- Intents-Detection ----- #

    def get_intent(self, phrase: str, threshold: int=75):
        results = {}

        for intent in self.intents:
            result, p = thefuzz.process.extractOne(
                phrase,
                self.intents[intent]["examples"],
            )
            if p >= threshold:
                results[intent] = p

        # Если не нашел намерения, то вернем пустой словарь
        # и не будем искать максимум
        if not results: return results

        best_intent = max(results, key=results.get)
        return {best_intent: results.get(best_intent)}

    # ----- Intents-Execution ----- #

    def exe_intent(self, intent):
        if intent:
            self.intents[tuple(intent)[0]]["cmd"]()

    # ----- Wake-Word_Detection ----- #

    def detect_wake_word(self, threshold=0.6) -> bool:
        """
        Детектирование wake word "hey jarvis" с использованием pyaudio

        Args:
            threshold: порог уверенности (0.5-0.7)

        Returns:
            bool: True если wake word обнаружен
        """
        while True:
            # Чтение данных из микрофона
            data = stream.read(CHUNK)

            # Преобразование в numpy массив
            audio_data = np.frombuffer(data, dtype=np.int16)

            # Детектирование
            predictions = wake_model.predict(audio_data)
            score = predictions.get('hey_jarvis', 0)

            # Проверка порога
            if score > threshold:
                wake_model.reset()
                return True


    # ----- Intents-Loader ----- #

    def load_intents(self) -> None:
        for plugin_folder in os.listdir(self.plugins_path):
            if plugin_folder in {"demo_plugin", "__pycache__", "__init__.py"}:
                continue

            try:
                plugin = importlib.import_module(f"plugins.{plugin_folder}.plugin")
            except ImportError:
                cprint(f"plugin \"{plugin_folder}\" has NOT plugin module!", "red")
                continue

            if not hasattr(plugin, "intents"):
                cprint(f"plugin \"{plugin_folder}\" has NOT intents!", "white", "on_red")
                continue

            cprint(f"plugin \"{plugin_folder}\" is loaded!", "light_green")
            self.intents.update(plugin.intents)

        print("-" * 80)

    # ----- EntryPoint ----- #

    def shutdown(self):
        """Корректное завершение работы"""
        cprint("\nЗавершение работы...", "yellow")

        # 1. Вызов shutdown каждого плагина
        for intent_name, intent_data in self.intents.items():
            if "shutdown" in intent_data:
                try:
                    intent_data["shutdown"]()
                    cprint(f"Ресурсы плагина \"{intent_name}\" освобождены", "green")
                except Exception as e:
                    cprint(f"Ошибка при shutdown плагина \"{intent_name}\": {e}", "red")

            # 2. Закрытие PyAudio
            stream.stop_stream()
            stream.close()
            p.terminate()

            # 3. Сброс SoundDevice
            sd.stop()

            # 4. Успешный код завершения
            cprint("Работа завершена", "green")
            sys.exit(0)

    # ----- EntryPoint ----- #

    def run(self):
        self.load_intents()
        cprint("Jarvis ready!", "cyan")
        self.say_random(self.ready_phrases)
        try:
            while True:
                print("-" * 80)
                cprint('Say "Hey Jarvis" to activate', "cyan")
                if self.detect_wake_word():
                    cprint("\tJarvis is activated", "cyan")
                    self.say_random(self.listen_phrases)
                    self.query["text"] = self.recognize_online().lower()

                    while not self.query["text"] and self.query["text"] != "хватить слушать":
                        self.say("я вас не расслышал. Скажите еще раз")
                        self.query["text"] = self.recognize_online()

                    if self.query["text"] == "хватить слушать":
                        continue

                    cprint(f'> {self.query["text"]}', "light_yellow")
                    self.query["norm_text"] = self.normalize(self.query["text"])
                    cprint(f'norm > {self.query["norm_text"]}', "light_yellow")
                    self.query["intent"] = self.get_intent(self.query["norm_text"])
                    cprint(f'intent > {self.query["intent"]}', "light_yellow")
                    self.exe_intent(self.query["intent"])
        except (KeyboardInterrupt, SystemExit):
            self.shutdown()
