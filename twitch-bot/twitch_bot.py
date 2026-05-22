# twitch_bot_skeleton.py
# Бот для Twitch чата с ИИ-ответами

import socket
import random
import time
import threading
import re
import json
import os
from datetime import datetime
from typing import Optional

class AIBrain:
    """Класс для работы с нейросетью"""
    
    def __init__(self, api_key: str = None, api_url: str = None):
        # 👇 СЮДА ВСТАВЬ СВОЮ API СТРОКУ ДЛЯ НЕЙРОНКИ
        self.API_KEY = api_key or os.getenv("AI_API_KEY", "your_api_key_here")
        self.API_URL = api_url or os.getenv("AI_API_URL", "https://api.openai.com/v1/chat/completions")
        
        self.system_prompt = "Ты - дружелюбный бот в Twitch чате. Отвечай кратко и с юмором."
        
    def generate_response(self, user: str, message: str, is_from_streamer: bool = False) -> Optional[str]:
        """Генерация ответа через нейросеть"""
        # Пример запроса к API (замени под свою нейросеть)
        try:
            # Здесь будет код отправки запроса к твоей нейросети
            # Пример для OpenAI:
            # import requests
            # response = requests.post(
            #     self.API_URL,
            #     headers={"Authorization": f"Bearer {self.API_KEY}"},
            #     json={"messages": [{"role": "user", "content": message}]}
            # )
            # return response.json()["choices"][0]["message"]["content"]
            
            # Заглушка для теста
            responses = [
                f"@{user} Привет! Хороший вопрос!",
                f"@{user} Хм, интересно...",
                f"@{user} Согласен с тобой!",
            ]
            return random.choice(responses)
            
        except Exception as e:
            print(f"Ошибка API: {e}")
            return None
    
    def is_addressed(self, message: str) -> bool:
        """Проверка, обращаются ли к боту"""
        bot_names = ['бот', 'bot', 'дима', 'dima']  # добавь свои имена
        return any(name in message.lower() for name in bot_names)


class TwitchBot:
    """Основной класс Twitch бота"""
    
    def __init__(self, token: str, channel: str, ai_api_key: str = None, ai_api_url: str = None):
        # Конфигурация
        self.token = token
        self.channel = "#" + channel.lower()
        self.nickname = "my_twitch_bot"
        self.server = "irc.chat.twitch.tv"
        self.port = 6667
        
        # ИИ компонент
        self.brain = AIBrain(api_key=ai_api_key, api_url=ai_api_url)
        
        # Состояние бота
        self.sock = None
        self.connected = False
        self.running = True
        
        # Настройки чата
        self.cooldown = 1.5  # секунд между сообщениями
        self.last_msg = 0
        
        # Игнорируемые боты
        self.ignored_bots = ["streamelements", "nightbot", "moobot", "fossabot"]
        
        # Статистика
        self.stats = {"sent": 0, "recv": 0, "start_time": time.time()}
        
        # Пинг менеджер
        self.last_pong = time.time()
        threading.Thread(target=self._pinger, daemon=True).start()
        
        print("✅ Бот инициализирован")
    
    def connect(self):
        """Подключение к Twitch IRC"""
        while self.running:
            try:
                print("🔄 Подключение к Twitch...")
                
                self.sock = socket.socket()
                self.sock.settimeout(10)
                self.sock.connect((self.server, self.port))
                self.sock.settimeout(None)
                
                # Авторизация
                self._send_raw(f"PASS {self.token}")
                time.sleep(0.5)
                self._send_raw(f"NICK {self.nickname}")
                time.sleep(0.5)
                self._send_raw(f"JOIN {self.channel}")
                self._send_raw("CAP REQ :twitch.tv/tags twitch.tv/commands")
                
                time.sleep(1)
                self.connected = True
                print(f"✅ Подключен к {self.channel}")
                
                # Приветственное сообщение
                self.send_message("Привет всем! Я бот на нейросети 👋")
                
                self._listen()
                break
                
            except Exception as e:
                print(f"❌ Ошибка подключения: {e}")
                self.connected = False
                time.sleep(5)
    
    def _listen(self):
        """Прослушивание сообщений чата"""
        buffer = ""
        
        while self.connected and self.running:
            try:
                data = self.sock.recv(4096).decode(errors='ignore')
                
                if not data:
                    time.sleep(0.1)
                    continue
                
                buffer += data
                lines = buffer.split('\r\n')
                buffer = lines.pop()
                
                for line in lines:
                    if line.startswith("PING"):
                        self._send_raw("PONG :tmi.twitch.tv")
                        self.last_pong = time.time()
                        continue
                    
                    if "PRIVMSG" in line:
                        self._handle_message(line)
                        
            except Exception as e:
                print(f"❌ Ошибка: {e}")
                break
        
        if self.running:
            print("🔄 Переподключение...")
            self.connected = False
            time.sleep(3)
            self.connect()
    
    def _handle_message(self, line: str):
        """Обработка входящего сообщения"""
        try:
            match = re.search(r':(\w+)!.*PRIVMSG.*:(.*)', line)
            if match:
                user = match.group(1)
                msg = match.group(2)
                
                # Фильтрация
                if user.lower() in self.ignored_bots or user.lower() == self.nickname.lower():
                    return
                
                self.stats["recv"] += 1
                print(f'[{datetime.now().strftime("%H:%M:%S")}] {user}: {msg}')
                
                # Проверка, обращаются ли к боту
                if self.brain.is_addressed(msg) and time.time() - self.last_msg > self.cooldown:
                    time.sleep(random.uniform(0.5, 1.5))
                    response = self.brain.generate_response(user, msg)
                    if response:
                        self.send_message(f"@{user} {response}")
                        self.last_msg = time.time()
                        
        except Exception as e:
            print(f"Ошибка обработки: {e}")
    
    def send_message(self, text: str) -> bool:
        """Отправка сообщения в чат"""
        if not self.connected:
            return False
        
        try:
            # Обрезаем длинные сообщения
            if len(text) > 450:
                text = text[:447] + "..."
            
            self._send_raw(f"PRIVMSG {self.channel} :{text}")
            self.stats["sent"] += 1
            
            mins = int((time.time() - self.stats["start_time"]) / 60)
            print(f'📤 [{mins}мин] {text}')
            return True
            
        except Exception as e:
            print(f"❌ Ошибка отправки: {e}")
            return False
    
    def _send_raw(self, data: str):
        """Отправка raw данных в сокет"""
        try:
            self.sock.send(f"{data}\r\n".encode())
        except:
            pass
    
    def _pinger(self):
        """Пинг менеджер для поддержания соединения"""
        while self.running:
            time.sleep(30)
            if self.connected:
                try:
                    self._send_raw("PING :tmi.twitch.tv")
                except:
                    pass
                
                if time.time() - self.last_pong > 180:
                    print("⚠️ Потеря соединения")
                    self.connected = False
                    break
    
    def stop(self):
        """Остановка бота"""
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
        
        print("\n" + "="*50)
        print(f"👋 Бот остановлен")
        print(f"📊 Статистика: отправлено {self.stats['sent']}, получено {self.stats['recv']}")
        print("="*50)


# ============= КОНФИГУРАЦИЯ =============
# 👇 СЮДА ВСТАВЬ СВОИ ДАННЫЕ
TOKEN = "oauth:your_token_here"  # OAuth токен Twitch
CHANNEL = "your_channel_name"    # Название канала

# 👇 API НЕЙРОНКИ (вставь свою строку)
AI_API_KEY = "your_openai_api_key_here"      # или другой API ключ
AI_API_URL = "https://api.openai.com/v1/chat/completions"  # URL твоей нейросети

# ИЛИ используй переменные окружения для безопасности:
# AI_API_KEY = os.getenv("OPENAI_API_KEY")
# ========================================


if __name__ == "__main__":
    print("🎯 ЗАПУСК TWITCH БОТА")
    print(f"📺 Канал: https://www.twitch.tv/{CHANNEL}")
    
    bot = TwitchBot(TOKEN, CHANNEL, AI_API_KEY, AI_API_URL)
    
    try:
        bot.connect()
        while bot.running:
            time.sleep(1)
    except KeyboardInterrupt:
        bot.stop()