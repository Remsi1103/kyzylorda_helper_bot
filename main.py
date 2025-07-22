# main.py
import telebot
from telebot import types
import sqlite3
import os
from flask import Flask
from threading import Thread

TOKEN = os.getenv("TOKEN")
bot = telebot.TeleBot(TOKEN)

# Админ ID
ADMIN_ID = 6864791335  # ← замени на свой при необходимости
CHANNEL_ID = "@kyzylorda_helper_channel"
KASPI_CARD = "4400430247434142"
PRICE = 500

# Flask для UptimeRobot
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

Thread(target=run_flask).start()

# Создание таблицы объявлений
conn = sqlite3.connect('ads.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS ads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    category TEXT,
    title TEXT,
    description TEXT,
    phone TEXT,
    is_paid INTEGER DEFAULT 0
)''')
conn.commit()

# Главное меню
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📢 Вакансии", "🏠 Аренда")
    markup.row("➕ Добавить объявление", "📋 Мои объявления")
    markup.row("💰 Платное объявление", "ℹ️ Помощь")
    return markup

# Команда /start
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Выберите действие:", reply_markup=main_menu())

# Категории
@bot.message_handler(func=lambda message: message.text == "📢 Вакансии" or message.text == "🏠 Аренда")
def show_category(message):
    category = "Вакансии" if message.text == "📢 Вакансии" else "Аренда"
    cursor.execute("SELECT id, title, description, phone FROM ads WHERE category=? ORDER BY id DESC", (category,))
    ads = cursor.fetchall()
    if ads:
        for ad in ads:
            bot.send_message(message.chat.id, f"🆔 {ad[0]}\n📌 {ad[1]}\n📝 {ad[2]}\n📞 {ad[3]}")
    else:
        bot.send_message(message.chat.id, "Объявлений пока нет.")

# Добавить объявление
@bot.message_handler(func=lambda message: message.text == "➕ Добавить объявление")
def add_ad(message):
    msg = bot.send_message(message.chat.id, "Выберите категорию: Вакансии или Аренда")
    bot.register_next_step_handler(msg, get_category)

def get_category(message):
    category = message.text
    if category not in ["Вакансии", "Аренда"]:
        bot.send_message(message.chat.id, "Неверная категория.")
        return
    msg = bot.send_message(message.chat.id, "Введите заголовок:")
    bot.register_next_step_handler(msg, get_title, category)

def get_title(message, category):
    title = message.text
    msg = bot.send_message(message.chat.id, "Введите описание:")
    bot.register_next_step_handler(msg, get_description, category, title)

def get_description(message, category, title):
    description = message.text
    msg = bot.send_message(message.chat.id, "Введите номер телефона:")
    bot.register_next_step_handler(msg, save_ad, category, title, description)

def save_ad(message, category, title, description):
    phone = message.text
    cursor.execute("INSERT INTO ads (user_id, category, title, description, phone) VALUES (?, ?, ?, ?, ?)",
                   (message.from_user.id, category, title, description, phone))
    conn.commit()
    bot.send_message(message.chat.id, "✅ Объявление добавлено!", reply_markup=main_menu())

# Мои объявления
@bot.message_handler(func=lambda message: message.text == "📋 Мои объявления")
def my_ads(message):
    cursor.execute("SELECT id, category, title FROM ads WHERE user_id=?", (message.from_user.id,))
    ads = cursor.fetchall()
    if ads:
        text = ""
        for ad in ads:
            text += f"🆔 {ad[0]} | 📂 {ad[1]} | {ad[2]}\n"
        bot.send_message(message.chat.id, text)
    else:
        bot.send_message(message.chat.id, "У вас нет объявлений.")

# Платное объявление
@bot.message_handler(func=lambda message: message.text == "💰 Платное объявление")
def paid_ad(message):
    msg = ("💰 Стоимость платного объявления — {} тг.\n\n"
           "Переведите на Kaspi:\n{}\n\n"
           "После оплаты отправьте сюда скриншот, и мы опубликуем объявление в канале.").format(PRICE, KASPI_CARD)
    bot.send_message(message.chat.id, msg)

# Помощь
@bot.message_handler(func=lambda message: message.text == "ℹ️ Помощь")
def help_msg(message):
    bot.send_message(message.chat.id, "Напишите нам: @your_support_username")

# Команда /admin — админ-панель
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID:
        return
    cursor.execute("SELECT * FROM ads ORDER BY id DESC")
    ads = cursor.fetchall()
    if not ads:
        bot.send_message(message.chat.id, "Нет объявлений.")
        return
    for ad in ads:
        bot.send_message(message.chat.id,
                         f"🆔 {ad[0]}\n👤 User ID: {ad[1]}\n📂 {ad[2]}\n📌 {ad[3]}\n📝 {ad[4]}\n📞 {ad[5]}\n💰 Платное: {'Да' if ad[6] else 'Нет'}")

# Команда /delete <id> — удаление объявления (только админ)
@bot.message_handler(commands=['delete'])
def delete_ad(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        ad_id = int(message.text.split()[1])
        cursor.execute("SELECT * FROM ads WHERE id=?", (ad_id,))
        ad = cursor.fetchone()
        if ad:
            cursor.execute("DELETE FROM ads WHERE id=?", (ad_id,))
            conn.commit()
            bot.send_message(message.chat.id, f"🗑 Объявление с ID {ad_id} удалено.")
        else:
            bot.send_message(message.chat.id, "❌ Объявление не найдено.")
    except:
        bot.send_message(message.chat.id, "❗ Используй команду так: /delete <id>")

# Запуск
bot.polling(none_stop=True)