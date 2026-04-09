# app.py
import os
import threading
from flask import Flask
import bot

app = Flask(__name__)

@app.route('/')
def home():
    return "🌸 Fant Bot работает! 🌸"

@app.route('/health')
def health():
    return "OK", 200

def run_flask():
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

def run_bot():
    bot.bot.infinity_polling()

if __name__ == '__main__':
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()
    run_flask()