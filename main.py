# main.py

import telebot
from telebot import types
import sqlite3
import os
from flask import Flask
from threading import Thread

# Настройки
TOKEN = os.getenv("TOKEN")
bot = telebot.TeleBot(TOKEN)

ADMIN_ID = 6864791335  # ← замени на свой
CHANNEL_ID = "@kyzylorda_helper_channel"
KASPI_CARD = "4400430247434142"
PRICE = 500

conn = sqlite3.connect("ads.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""CREATE TABLE IF NOT EXISTS ads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    category TEXT,
    title TEXT,
    description TEXT,
    phone TEXT,
    is_paid INTEGER DEFAULT 0
)""")
conn.commit()

user_data = {}
user_states = {}

# Flask для UptimeRobot
app = Flask(__name__)
@app.route("/")
def index():
    return "Бот работает"
def run():
    app.run(host="0.0.0.0", port=8080)
Thread(target=run).start()

# 👋 Приветствие
@bot.message_handler(commands=["start"])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🇷🇺 Русский", "🇰🇿 Қазақша")
    bot.send_message(message.chat.id, "👋 Добро пожаловать в Kyzylorda Helper!\nТілді таңдаңыз / Выберите язык:", reply_markup=markup)

# Выбор языка
@bot.message_handler(func=lambda msg: msg.text in ["🇷🇺 Русский", "🇰🇿 Қазақша"])
def language_choice(message):
    lang = "ru" if message.text == "🇷🇺 Русский" else "kz"
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if lang == "ru":
        markup.add("📢 Вакансия", "🏠 Аренда")
        markup.add("➕ Добавить объявление")
        markup.add("📋 Мои объявления", "ℹ️ Помощь")
    else:
        markup.add("📢 Вакансиялар", "🏠 Жалға беру")
        markup.add("➕ Хабарландыру қосу")
        markup.add("📋 Менің хабарландыруларым", "ℹ️ Көмек")
    bot.send_message(message.chat.id, "Меню:", reply_markup=markup)

# 🆘 Помощь с кнопкой на канал
@bot.message_handler(func=lambda msg: msg.text in ["ℹ️ Помощь", "ℹ️ Көмек"])
def help_message(message):
    text = (
        "ℹ️ Этот бот помогает размещать и находить объявления по аренде и вакансиям.\n\n"
        "➕ Чтобы добавить объявление, нажми кнопку '➕ Добавить объявление'.\n"
        "📋 Для просмотра своих объявлений — '📋 Мои объявления'.\n\n"
        "📢 А также подпишись на наш канал, где публикуются лучшие объявления!"
    )
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📲 Перейти в канал", url="https://t.me/kyzylorda_helper_channel"))
    bot.send_message(message.chat.id, text, reply_markup=markup)

# Выбор категории объявления
@bot.message_handler(func=lambda msg: msg.text in ["📢 Вакансия", "🏠 Аренда", "📢 Вакансиялар", "🏠 Жалға беру"])
def choose_category(message):
    if "Ваканс" in message.text:
        category = "vacancy"
    elif "Аренда" in message.text or "Жалға" in message.text:
        category = "rent"
    else:
        category = "other"
    user_data[message.from_user.id] = {'category': category}
    user_states[message.from_user.id] = {'step': 'enter_details'}
    bot.send_message(message.chat.id, "✏️ Введите заголовок, описание и телефон одним сообщением.\nПример:\n\nПродавец в магазин\nОпыт не обязателен. График 2/2\n87071234567")

# ➕ Добавление объявления
@bot.message_handler(func=lambda msg: msg.text in ["➕ Добавить объявление", "➕ Хабарландыру қосу"])
def add_ad(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📢 Вакансия", "🏠 Аренда")
    markup.add("📢 Вакансиялар", "🏠 Жалға беру")
    bot.send_message(message.chat.id, "📂 Выберите категорию объявления:", reply_markup=markup)

# Получение данных объявления
@bot.message_handler(func=lambda msg: user_states.get(msg.from_user.id, {}).get('step') == 'enter_details')
def receive_details(message):
    category = user_data.get(message.from_user.id, {}).get("category")
    lines = message.text.split("\n")
    if len(lines) < 3:
        bot.send_message(message.chat.id, "❌ Пожалуйста, укажите минимум 3 строки: заголовок, описание и телефон.")
        return
    title, description, phone = lines[0], "\n".join(lines[1:-1]), lines[-1]
    cursor.execute("INSERT INTO ads (user_id, category, title, description, phone) VALUES (?, ?, ?, ?, ?)", (message.from_user.id, category, title, description, phone))
    conn.commit()
    ad_id = cursor.lastrowid

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("💰 Сделать платным", callback_data=f"pay_{ad_id}"))
    bot.send_message(message.chat.id, f"✅ Объявление сохранено с ID {ad_id}.\nЕсли хотите, можете сделать его платным и получить приоритет в канале.", reply_markup=markup)
    user_states.pop(message.from_user.id, None)

# 💰 Кнопка платного объявления
@bot.callback_query_handler(func=lambda call: call.data.startswith("pay_"))
def pay_ad(call):
    ad_id = call.data.split("_")[1]
    bot.send_message(call.message.chat.id, f"💳 Переведите {PRICE}₸ на Kaspi номер: {KASPI_CARD}.\nПосле оплаты отправьте скриншот админу.")
    bot.answer_callback_query(call.id, "Инструкция по оплате отправлена.")

# 👤 Мои объявления
@bot.message_handler(func=lambda msg: msg.text in ["📋 Мои объявления", "📋 Менің хабарландыруларым"])
def my_ads(message):
    cursor.execute("SELECT id, title FROM ads WHERE user_id = ?", (message.from_user.id,))
    ads = cursor.fetchall()
    if ads:
        text = "\n".join([f"🆔 {ad[0]} — {ad[1]}" for ad in ads])
        bot.send_message(message.chat.id, f"📋 Ваши объявления:\n{text}")
    else:
        bot.send_message(message.chat.id, "У вас нет объявлений.")

# 🔐 Панель админа (все объявления с кнопками)
@bot.message_handler(func=lambda msg: msg.text == "📋 Все объявления" and msg.from_user.id == ADMIN_ID)
def list_all_ads(message):
    cursor.execute("SELECT id, title, description, phone FROM ads")
    ads = cursor.fetchall()
    if not ads:
        bot.send_message(message.chat.id, "Нет объявлений.")
    else:
        for ad in ads:
            ad_id = ad[0]
            text = f"🆔 {ad_id}\n📌 {ad[1]}\n📝 {ad[2]}\n📞 {ad[3]}"
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("🗑 Удалить", callback_data=f"action_delete_{ad_id}"),
                types.InlineKeyboardButton("📢 Опубликовать", callback_data=f"action_post_{ad_id}")
            )
            bot.send_message(message.chat.id, text, reply_markup=markup)

# 🔘 Инлайн-кнопки действий
@bot.callback_query_handler(func=lambda call: call.data.startswith("action_"))
def handle_admin_action(call):
    if call.from_user.id != ADMIN_ID:
        return

    action, ad_id = call.data.split("_")[1:]
    ad_id = int(ad_id)

    if action == "delete":
        cursor.execute("DELETE FROM ads WHERE id = ?", (ad_id,))
        conn.commit()
        bot.answer_callback_query(call.id, f"Удалено объявление {ad_id}")
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)

    elif action == "post":
        cursor.execute("SELECT title, description, phone FROM ads WHERE id = ?", (ad_id,))
        ad = cursor.fetchone()
        if ad:
            text = f"📌 {ad[0]}\n📝 {ad[1]}\n📞 {ad[2]}"
            bot.send_message(CHANNEL_ID, text)
            bot.answer_callback_query(call.id, "✅ Опубликовано")
        else:
            bot.answer_callback_query(call.id, "❌ Объявление не найдено")

# ⏳ Запуск бота
print("Бот запущен")
bot.polling(none_stop=True)