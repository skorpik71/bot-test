import os
from telegram import Bot
from telegram.ext import Updater, CommandHandler
import threading
from flask import Flask

# Токен и chat_id из переменных окружения
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

bot = Bot(token=TOKEN)
app = Flask(__name__)

def send_notification():
    while True:
        try:
            bot.send_message(chat_id=CHAT_ID, text="Я не сплю, бот работает!")
            # Ждём 30 минут (1800 секунд)
            threading.Event().wait(1800)
        except Exception as e:
            print(f"Ошибка: {e}")

def start(update, context):
    update.message.reply_text("Бот запущен! Сообщения будут приходить каждые 30 минут.")

@app.route('/')
def home():
    return "Бот жив и работает!"

def run_flask():
    app.run(host='0.0.0.0', port=10000)

def main():
    # Запускаем Flask в отдельном потоке
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # Запускаем Telegram-бота
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))

    # Запускаем уведомления в отдельном потоке
    notification_thread = threading.Thread(target=send_notification)
    notification_thread.daemon = True
    notification_thread.start()

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()