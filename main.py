# main.py
import telebot
from telebot import types
import sqlite3
import os
from flask import Flask
from threading import Thread

TOKEN = os.getenv("TOKEN")
bot = telebot.TeleBot(TOKEN)

# Flask для UptimeRobot
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

def keep_alive():
    t = Thread(target=run_flask)
    t.start()

# Подключение к БД
conn = sqlite3.connect('ads.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS ads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    category TEXT,
    text TEXT,
    is_paid INTEGER DEFAULT 0
)
''')
conn.commit()

# Хранение языка
user_lang = {}

# Кнопки
def main_menu(lang):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if lang == "kz":
        markup.row("📢 Жұмыс", "🏠 Жалдау")
        markup.row("➕ Хабарландыру қосу", "📋 Менің хабарландыруларым")
        markup.row("ℹ️ Көмек", "💰 Ақылы хабарландыру")
    else:
        markup.row("📢 Вакансии", "🏠 Аренда")
        markup.row("➕ Добавить объявление", "📋 Мои объявления")
        markup.row("ℹ️ Помощь", "💰 Платное объявление")
    return markup

# /start
@bot.message_handler(commands=['start'])
def start(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"))
    markup.add(types.InlineKeyboardButton("🇰🇿 Қазақша", callback_data="lang_kz"))
    bot.send_message(message.chat.id, "👋 Добро пожаловать в Kyzylorda Helper!\nТілді таңдаңыз / Выберите язык:", reply_markup=markup)

# Выбор языка
@bot.callback_query_handler(func=lambda call: call.data.startswith("lang_"))
def choose_language(call):
    lang = call.data.split("_")[1]
    user_lang[call.from_user.id] = lang
    if lang == "kz":
        text = "✅ Қазақ тілі таңдалды."
    else:
        text = "✅ Русский язык выбран."
    bot.send_message(call.message.chat.id, text, reply_markup=main_menu(lang))

# Обработка всех текстов
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    lang = user_lang.get(message.from_user.id, "ru")

    if lang == "kz":
        if message.text == "📢 Жұмыс":
            bot.send_message(message.chat.id, "Мұнда жұмыстар көрсетіледі.")
        elif message.text == "🏠 Жалдау":
            bot.send_message(message.chat.id, "Мұнда жалға алу ұсыныстары көрсетіледі.")
        elif message.text == "➕ Хабарландыру қосу":
            bot.send_message(message.chat.id, "Хабарландыру мәтінін жіберіңіз:")
            bot.register_next_step_handler(message, lambda msg: save_ad(msg, "kz"))
        elif message.text == "📋 Менің хабарландыруларым":
            show_user_ads(message, lang)
        elif message.text == "ℹ️ Көмек":
            bot.send_message(message.chat.id, "Бұл бот арқылы сіз хабарландырулар қосып, көруіңізге болады.")
        elif message.text == "💰 Ақылы хабарландыру":
            bot.send_message(message.chat.id, "Ақылы жарнама үшін Kaspi немесе басқа әдіс арқылы төлеңіз. Байланыс: @Xnelxve1")
        else:
            bot.send_message(message.chat.id, "Түсінбедім. Басты мәзірден таңдаңыз.", reply_markup=main_menu(lang))

    else:
        if message.text == "📢 Вакансии":
            bot.send_message(message.chat.id, "Здесь будут отображаться вакансии.")
        elif message.text == "🏠 Аренда":
            bot.send_message(message.chat.id, "Здесь будут показываться объявления по аренде.")
        elif message.text == "➕ Добавить объявление":
            bot.send_message(message.chat.id, "Пожалуйста, отправьте текст объявления:")
            bot.register_next_step_handler(message, lambda msg: save_ad(msg, "ru"))
        elif message.text == "📋 Мои объявления":
            show_user_ads(message, lang)
        elif message.text == "ℹ️ Помощь":
            bot.send_message(message.chat.id, "С помощью этого бота вы можете размещать и просматривать объявления.")
        elif message.text == "💰 Платное объявление":
            bot.send_message(message.chat.id, "Для платного объявления свяжитесь через Kaspi или другой метод. Контакт: @Xnelxve1")
        else:
            bot.send_message(message.chat.id, "Я не понял. Выберите из меню.", reply_markup=main_menu(lang))

# Сохранить объявление
def save_ad(message, lang):
    cursor.execute("INSERT INTO ads (user_id, text, category) VALUES (?, ?, ?)", (message.from_user.id, message.text, ""))
    conn.commit()
    if lang == "kz":
        bot.send_message(message.chat.id, "✅ Хабарландыру сақталды.", reply_markup=main_menu(lang))
    else:
        bot.send_message(message.chat.id, "✅ Объявление сохранено.", reply_markup=main_menu(lang))

# Показать мои объявления
def show_user_ads(message, lang):
    cursor.execute("SELECT id, text FROM ads WHERE user_id = ?", (message.from_user.id,))
    ads = cursor.fetchall()
    if not ads:
        msg = "Сізде хабарландырулар жоқ." if lang == "kz" else "У вас нет объявлений."
    else:
        msg = "\n\n".join([f"🆔 {ad[0]}:\n{ad[1]}" for ad in ads])
    bot.send_message(message.chat.id, msg)

# Запуск
keep_alive()
bot.polling(non_stop=True)
