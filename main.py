# main.py

import telebot
from telebot import types
import sqlite3
import os
from flask import Flask
from threading import Thread

TOKEN = os.getenv("TOKEN")
bot = telebot.TeleBot(TOKEN)

ADMIN_ID = 6864791335  # ← замени на свой
CHANNEL_ID = "@kyzylorda_helper_channel"
KASPI_CARD = "4400430247434142"
PRICE = 500

user_language = {}
user_data = {}

def init_db():
    conn = sqlite3.connect('ads.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            category TEXT,
            title TEXT,
            description TEXT,
            phone TEXT,
            is_paid INTEGER DEFAULT 0,
            is_posted INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🇷🇺 Русский"), types.KeyboardButton("🇰🇿 Қазақша"))
    bot.send_message(message.chat.id, "👋 Добро пожаловать в Kyzylorda Helper!\n\nТілді таңдаңыз / Выберите язык:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text in ["🇷🇺 Русский", "🇰🇿 Қазақша"])
def set_language(message):
    lang = 'ru' if message.text == "🇷🇺 Русский" else 'kz'
    user_language[message.chat.id] = lang
    send_main_menu(message.chat.id)

def send_main_menu(chat_id):
    lang = user_language.get(chat_id, 'ru')
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📢 Вакансии" if lang == 'ru' else "📢 Жұмыс", 
               "🏠 Аренда" if lang == 'ru' else "🏠 Жалға беру")
    markup.add("➕ Добавить объявление" if lang == 'ru' else "➕ Хабарландыру қосу", 
               "📋 Мои объявления" if lang == 'ru' else "📋 Менің хабарландыруларым")
    markup.add("💰 Платное объявление" if lang == 'ru' else "💰 Ақылы хабарландыру", 
               "ℹ️ Помощь" if lang == 'ru' else "ℹ️ Көмек")
    text = "Главное меню" if lang == 'ru' else "Басты мәзір"
    bot.send_message(chat_id, text, reply_markup=markup)

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id == ADMIN_ID:
        conn = sqlite3.connect('ads.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, category, title, is_posted FROM ads")
        ads = cursor.fetchall()
        conn.close()
        if not ads:
            bot.send_message(message.chat.id, "Объявлений нет.")
            return
        for ad in ads:
            status = "✅ Опубликовано" if ad[3] else "❌ Не опубликовано"
            bot.send_message(message.chat.id, f"ID: {ad[0]}\nКатегория: {ad[1]}\nЗаголовок: {ad[2]}\nСтатус: {status}")
    else:
        bot.send_message(message.chat.id, "Доступ запрещен.")

@bot.message_handler(commands=['post'])
def post_ad(message):
    if message.from_user.id == ADMIN_ID:
        msg = bot.send_message(message.chat.id, "Введите ID объявления для публикации:")
        bot.register_next_step_handler(msg, handle_post_id)

def handle_post_id(message):
    ad_id = message.text.strip()
    conn = sqlite3.connect('ads.db')
    cursor = conn.cursor()
    cursor.execute("SELECT title, description, phone FROM ads WHERE id=? AND is_posted=0", (ad_id,))
    ad = cursor.fetchone()
    if ad:
        post_text = f"📢 {ad[0]}\n\n{ad[1]}\n\n📞 {ad[2]}"
        bot.send_message(CHANNEL_ID, post_text)
        cursor.execute("UPDATE ads SET is_posted=1 WHERE id=?", (ad_id,))
        conn.commit()
        bot.send_message(message.chat.id, "Объявление опубликовано.")
    else:
        bot.send_message(message.chat.id, "Объявление не найдено или уже опубликовано.")
    conn.close()

@bot.message_handler(func=lambda m: m.text in ["📢 Вакансии", "📢 Жұмыс", "🏠 Аренда", "🏠 Жалға беру"])
def show_ads(message):
    lang = user_language.get(message.chat.id, 'ru')
    category_map = {
        "📢 Вакансии": "Вакансии", "📢 Жұмыс": "Вакансии",
        "🏠 Аренда": "Аренда", "🏠 Жалға беру": "Аренда"
    }
    category = category_map.get(message.text)
    conn = sqlite3.connect('ads.db')
    cursor = conn.cursor()
    cursor.execute("SELECT title, description, phone FROM ads WHERE category=? AND is_posted=1", (category,))
    results = cursor.fetchall()
    conn.close()
    if not results:
        text = "Пока нет объявлений в этой категории." if lang == 'ru' else "Бұл санатта хабарландырулар жоқ."
        bot.send_message(message.chat.id, text)
    else:
        for ad in results:
            bot.send_message(message.chat.id, f"📢 {ad[0]}\n\n{ad[1]}\n\n📞 {ad[2]}")

@bot.message_handler(func=lambda m: m.text in ["➕ Добавить объявление", "➕ Хабарландыру қосу"])
def add_ad(message):
    lang = user_language.get(message.chat.id, 'ru')
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("📢 Вакансии" if lang == 'ru' else "📢 Жұмыс", 
               "🏠 Аренда" if lang == 'ru' else "🏠 Жалға беру")
    text = "Выберите категорию объявления:" if lang == 'ru' else "Хабарландыру санатын таңдаңыз:"
    msg = bot.send_message(message.chat.id, text, reply_markup=markup)
    bot.register_next_step_handler(msg, get_category)

def get_category(message):
    user_data[message.chat.id] = {'category': message.text}
    lang = user_language.get(message.chat.id, 'ru')
    text = ("Введите объявление в формате:\nЗаголовок\nОписание\nКонтактный телефон" 
            if lang == 'ru' else 
            "Хабарландыруды келесі форматта жазыңыз:\nТақырып\nСипаттама\nБайланыс нөмірі")
    msg = bot.send_message(message.chat.id, text)
    bot.register_next_step_handler(msg, get_ad_details)

def get_ad_details(message):
    parts = message.text.split("\n")
    if len(parts) < 3:
        bot.send_message(message.chat.id, "Формат дұрыс емес. Үшеуін енгізіңіз: тақырып, сипаттама, телефон.")
        return
    user_data[message.chat.id].update({
        'title': parts[0],
        'description': parts[1],
        'phone': parts[2]
    })

    data = user_data[message.chat.id]
    conn = sqlite3.connect('ads.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO ads (user_id, category, title, description, phone) VALUES (?, ?, ?, ?, ?)",
                   (message.chat.id, data['category'], data['title'], data['description'], data['phone']))
    conn.commit()
    conn.close()

    lang = user_language.get(message.chat.id, 'ru')
    bot.send_message(ADMIN_ID, f"🆕 Жаңа хабарландыру @{message.from_user.username or message.from_user.id}\n"
                               f"Санат: {data['category']}\nТақырып: {data['title']}")
    text = "Ваше объявление отправлено на модерацию." if lang == 'ru' else "Хабарландыру модерацияға жіберілді."
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: m.text in ["📋 Мои объявления", "📋 Менің хабарландыруларым"])
def my_ads(message):
    lang = user_language.get(message.chat.id, 'ru')
    conn = sqlite3.connect('ads.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, is_posted FROM ads WHERE user_id=?", (message.chat.id,))
    ads = cursor.fetchall()
    conn.close()
    if not ads:
        text = "У вас пока нет объявлений." if lang == 'ru' else "Сізде әлі хабарландыру жоқ."
        bot.send_message(message.chat.id, text)
    else:
        for ad in ads:
            status = "✅ Опубликовано" if ad[2] else "🕓 На модерации"
            bot.send_message(message.chat.id, f"ID: {ad[0]}\n{ad[1]}\nСтатус: {status}")

@bot.message_handler(func=lambda m: m.text in ["ℹ️ Помощь", "ℹ️ Көмек"])
def help_section(message):
    lang = user_language.get(message.chat.id, 'ru')
    if lang == 'ru':
        text = f"Чтобы подать объявление:\n➕ Нажмите «Добавить объявление»\n\n" \
               f"Для платного объявления:\n💰 Оплатите {PRICE}₸ на Kaspi: {KASPI_CARD} и отправьте скриншот админу."
    else:
        text = f"Хабарландыру қосу үшін:\n➕ «Хабарландыру қосу» батырмасын басыңыз\n\n" \
               f"Ақылы хабарландыру үшін:\n💰 {PRICE}₸ Kaspi нөміріне жіберіңіз: {KASPI_CARD} және түбіртекті админе жолдаңыз."
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📢 Каналға өту" if lang == 'kz' else "📢 Перейти в канал", 
                                          url=f"https://t.me/{CHANNEL_ID[1:]}"))
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.message_handler(func=lambda m: m.text in ["💰 Платное объявление", "💰 Ақылы хабарландыру"])
def paid_ad(message):
    lang = user_language.get(message.chat.id, 'ru')
    if lang == 'ru':
        text = f"💰 Стоимость платного объявления: {PRICE}₸\nПереведите на Kaspi: {KASPI_CARD}\nПосле оплаты отправьте скриншот админу."
    else:
        text = f"💰 Ақылы хабарландыру бағасы: {PRICE}₸\nKaspi: {KASPI_CARD}\nТөлем жасағаннан кейін түбіртекті админе жіберіңіз."
    bot.send_message(message.chat.id, text)

# Flask для UptimeRobot
app = Flask(__name__)

@app.route('/')
def index():
    return "Bot is running!"

def run():
    app.run(host="0.0.0.0", port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

keep_alive()

bot.polling(none_stop=True)