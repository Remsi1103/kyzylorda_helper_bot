# main.py

import telebot
from telebot import types
import sqlite3
import os
from flask import Flask
from threading import Thread

TOKEN = os.getenv("TOKEN")
bot = telebot.TeleBot(TOKEN)

# Константы
ADMIN_ID = 6864791335 
CHANNEL_ID = "@kyzylorda_helper_channel"
KASPI_CARD = "4400430247434142"
PRICE = 500  # цена за платное объявление

# Flask для UptimeRobot
app = Flask(__name__)
@app.route('/')
def home():
    return "Bot is running!"
def run_flask():
    app.run(host="0.0.0.0", port=8080)
Thread(target=run_flask).start()

# Инициализация базы
conn = sqlite3.connect('ads.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS ads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    category TEXT,
    title TEXT,
    description TEXT,
    phone TEXT,
    is_paid INTEGER DEFAULT 0
)''')
conn.commit()

# Хранение состояний
user_states = {}
user_data = {}

# Старт и выбор языка
@bot.message_handler(commands=['start'])
def start(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Қазақша", callback_data='lang_kz'))
    markup.add(types.InlineKeyboardButton("Русский", callback_data='lang_ru'))
    bot.send_message(message.chat.id, "👋 Добро пожаловать в Kyzylorda Helper!\nТілді таңдаңыз / Выберите язык:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('lang_'))
def handle_lang(call):
    lang = call.data.split('_')[1]
    user_states[call.from_user.id] = {'lang': lang}
    send_main_menu(call.message.chat.id, lang)

def send_main_menu(chat_id, lang):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if lang == 'kz':
        markup.add("📢 Вакансиялар", "🏠 Жалға беру")
        markup.add("➕ Хабарландыру қосу", "📋 Менің хабарландыруларым")
        markup.add("ℹ️ Көмек", "💰 Ақылы хабарландыру")
    else:
        markup.add("📢 Вакансии", "🏠 Аренда")
        markup.add("➕ Добавить объявление", "📋 Мои объявления")
        markup.add("ℹ️ Помощь", "💰 Платное объявление")
    bot.send_message(chat_id, "📋 Главное меню:", reply_markup=markup)

# Обработка кнопок
@bot.message_handler(func=lambda msg: msg.text in [
    "📢 Вакансии", "🏠 Аренда", "📢 Вакансиялар", "🏠 Жалға беру"
])
def show_category_ads(message):
    lang = user_states.get(message.from_user.id, {}).get('lang', 'ru')
    category = 'vacancy' if "Ваканс" in message.text or "Вакансия" in message.text else 'rent'
    cursor.execute("SELECT id, title, description, phone FROM ads WHERE category = ?", (category,))
    ads = cursor.fetchall()
    if not ads:
        text = "Пока нет объявлений." if lang == 'ru' else "Хабарландырулар жоқ."
        bot.send_message(message.chat.id, text)
    else:
        for ad in ads:
            text = f"🆔 {ad[0]}\n📌 {ad[1]}\n📝 {ad[2]}\n📞 {ad[3]}"
            bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda msg: msg.text in [
    "➕ Добавить объявление", "➕ Хабарландыру қосу"
])
def add_ad(message):
    user_states[message.from_user.id]['step'] = 'choose_category'
    lang = user_states[message.from_user.id]['lang']
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if lang == 'kz':
        markup.add("📢 Вакансия", "🏠 Жалға беру")
    else:
        markup.add("📢 Вакансия", "🏠 Аренда")
    bot.send_message(message.chat.id, "Выберите категорию:", reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.text in ["📢 Вакансия", "🏠 Аренда", "📢 Вакансия", "🏠 Жалға беру"])
def choose_category(message):
    user_data[message.from_user.id] = {'category': 'vacancy' if "Вакансия" in message.text else 'rent'}
    user_states[message.from_user.id]['step'] = 'enter_details'
    bot.send_message(message.chat.id, "✏️ Введите заголовок, описание и телефон одним сообщением.\nПример:\n\nПродавец в магазин\nОпыт не обязателен. График 2/2\n87071234567")

@bot.message_handler(func=lambda msg: user_states.get(msg.from_user.id, {}).get('step') == 'enter_details')
def save_ad(message):
    parts = message.text.split('\n')
    if len(parts) < 3:
        bot.send_message(message.chat.id, "Пожалуйста, отправьте заголовок, описание и телефон *тремя строками*.")
        return
    title, description, phone = parts[0], parts[1], parts[2]
    data = user_data[message.from_user.id]
    cursor.execute("INSERT INTO ads (user_id, username, category, title, description, phone) VALUES (?, ?, ?, ?, ?, ?)", (
        message.from_user.id, message.from_user.username, data['category'], title, description, phone
    ))
    conn.commit()
    bot.send_message(message.chat.id, "✅ Объявление сохранено. Хотите платное размещение? Нажмите '💰 Платное объявление'.")

@bot.message_handler(func=lambda msg: msg.text in ["📋 Мои объявления", "📋 Менің хабарландыруларым"])
def my_ads(message):
    cursor.execute("SELECT id, title FROM ads WHERE user_id = ?", (message.from_user.id,))
    ads = cursor.fetchall()
    if not ads:
        bot.send_message(message.chat.id, "У вас нет объявлений.")
    else:
        for ad in ads:
            bot.send_message(message.chat.id, f"🆔 {ad[0]} - {ad[1]}")

@bot.message_handler(func=lambda msg: msg.text in ["ℹ️ Помощь", "ℹ️ Көмек"])
def help_msg(message):
    text = "Для размещения платного объявления:\n1. Переведите *{} тг* на Kaspi:\n`{}`\n2. Отправьте скрин оплаты сюда.\n\nПосле подтверждения, ваше объявление будет опубликовано в канале.".format(PRICE, KASPI_CARD)
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text in ["💰 Платное объявление", "💰 Ақылы хабарландыру"])
def pay_ad(message):
    help_msg(message)

# Обработка скрина оплаты
@bot.message_handler(content_types=['photo'])
def handle_payment_photo(message):
    if message.caption and "оплата" in message.caption.lower():
        bot.forward_message(ADMIN_ID, message.chat.id, message.message_id)
        bot.send_message(message.chat.id, "✅ Скрін отправлен. После проверки админ опубликует объявление.")
    else:
        bot.send_message(message.chat.id, "Отправьте скрин оплаты *с подписью* — например: `оплата за объявление`", parse_mode="Markdown")

# Команда /admin для админа
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID:
        return
    cursor.execute("SELECT id, title, description, phone FROM ads")
    ads = cursor.fetchall()
    if not ads:
        bot.send_message(message.chat.id, "Нет объявлений.")
    else:
        for ad in ads:
            text = f"🆔 {ad[0]}\n📌 {ad[1]}\n📝 {ad[2]}\n📞 {ad[3]}"
            bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['delete'])
def delete_ad(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        ad_id = int(message.text.split()[1])
        cursor.execute("DELETE FROM ads WHERE id = ?", (ad_id,))
        conn.commit()
        bot.send_message(message.chat.id, f"🗑️ Объявление {ad_id} удалено.")
    except:
        bot.send_message(message.chat.id, "❗ Используй: /delete ID")

# Публикация в канал (после ручной оплаты)
@bot.message_handler(commands=['post'])
def post_ad(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        ad_id = int(message.text.split()[1])
        cursor.execute("SELECT title, description, phone FROM ads WHERE id = ?", (ad_id,))
        ad = cursor.fetchone()
        if ad:
            text = f"📌 {ad[0]}\n📝 {ad[1]}\n📞 {ad[2]}"
            bot.send_message(CHANNEL_ID, text)
            bot.send_message(message.chat.id, "✅ Опубликовано в канале.")
        else:
            bot.send_message(message.chat.id, "❌ Объявление не найдено.")
    except:
        bot.send_message(message.chat.id, "❗ Используй: /post ID")

bot.polling(none_stop=True)