# main.py
import telebot
from telebot import types
import sqlite3
import os
from flask import Flask
from threading import Thread

# 🔑 Токен и ID
TOKEN = os.getenv("TOKEN")
bot = telebot.TeleBot(TOKEN)
ADMIN_ID = 6864791335  # замени на свой ID
CHANNEL_ID = "@kyzylorda_helper_channel"

# 🗃️ База данных
conn = sqlite3.connect("ads.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS ads
                  (id INTEGER PRIMARY KEY AUTOINCREMENT,
                   user_id INTEGER,
                   category TEXT,
                   text TEXT,
                   is_paid INTEGER)''')
conn.commit()

# 🌐 Flask
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

Thread(target=run_flask).start()

# 🌍 Выбор языка
user_language = {}

def get_text(user_id, ru, kz):
    return ru if user_language.get(user_id) == 'ru' else kz

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("Русский 🇷🇺"), types.KeyboardButton("Қазақша 🇰🇿"))
    bot.send_message(message.chat.id, "👋 Тілді таңдаңыз / Выберите язык:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text in ["Русский 🇷🇺", "Қазақша 🇰🇿"])
def set_language(message):
    user_language[message.from_user.id] = 'ru' if message.text == "Русский 🇷🇺" else 'kz'
    show_main_menu(message)

def show_main_menu(message):
    lang = user_language.get(message.from_user.id, 'ru')
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📢 Вакансии" if lang == 'ru' else "📢 Жұмыс")
    markup.add("🏠 Аренда" if lang == 'ru' else "🏠 Жалға беру")
    markup.add("➕ Добавить объявление" if lang == 'ru' else "➕ Хабарландыру қосу")
    markup.add("💰 Платное объявление" if lang == 'ru' else "💰 Ақылы хабарландыру")
    markup.add("📋 Мои объявления" if lang == 'ru' else "📋 Менің хабарландыруларым")
    markup.add("ℹ️ Помощь" if lang == 'ru' else "ℹ️ Көмек")
    if message.from_user.id == ADMIN_ID:
        markup.add("🔧 Админ-панель")
    welcome = "👋 Добро пожаловать в Kyzylorda Helper!" if lang == 'ru' else "👋 Kyzylorda Helper-ге қош келдіңіз!"
    bot.send_message(message.chat.id, welcome, reply_markup=markup)

@bot.message_handler(func=lambda m: m.text in ["📢 Вакансии", "📢 Жұмыс"])
def show_jobs(message):
    cursor.execute("SELECT text FROM ads WHERE category = 'vacancy'")
    ads = cursor.fetchall()
    if not ads:
        bot.send_message(message.chat.id, get_text(message.from_user.id, "Нет вакансий.", "Жұмыс табылмады."))
    else:
        for ad in ads:
            bot.send_message(message.chat.id, ad[0])

@bot.message_handler(func=lambda m: m.text in ["🏠 Аренда", "🏠 Жалға беру"])
def show_rent(message):
    cursor.execute("SELECT text FROM ads WHERE category = 'rent'")
    ads = cursor.fetchall()
    if not ads:
        bot.send_message(message.chat.id, get_text(message.from_user.id, "Нет объявлений по аренде.", "Жалға беру хабарландырулары жоқ."))
    else:
        for ad in ads:
            bot.send_message(message.chat.id, ad[0])

@bot.message_handler(func=lambda m: m.text in ["➕ Добавить объявление", "➕ Хабарландыру қосу"])
def ask_category(message):
    lang = user_language.get(message.from_user.id, 'ru')
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("📢 Вакансии" if lang == 'ru' else "📢 Жұмыс")
    markup.add("🏠 Аренда" if lang == 'ru' else "🏠 Жалға беру")
    bot.send_message(message.chat.id, get_text(message.from_user.id, "Выберите категорию:", "Санатты таңдаңыз:"), reply_markup=markup)
    bot.register_next_step_handler(message, get_ad_text)

def get_ad_text(message):
    category = 'vacancy' if "Вакансии" in message.text or "Жұмыс" in message.text else 'rent'
    bot.send_message(message.chat.id, get_text(message.from_user.id, "Отправьте текст объявления:", "Хабарландыру мәтінін жіберіңіз:"))
    bot.register_next_step_handler(message, save_ad, category)

def save_ad(message, category):
    cursor.execute("INSERT INTO ads (user_id, category, text, is_paid) VALUES (?, ?, ?, ?)",
                   (message.from_user.id, category, message.text, 0))
    conn.commit()
    bot.send_message(message.chat.id, get_text(message.from_user.id, "✅ Объявление сохранено.", "✅ Хабарландыру сақталды."))

@bot.message_handler(func=lambda m: m.text in ["💰 Платное объявление", "💰 Ақылы хабарландыру"])
def paid_ad(message):
    text = get_text(message.from_user.id,
        "💰 Для размещения платного объявления отправьте 1000₸ на Kaspi:\n📱 +7 777 777 7777\nПосле оплаты отправьте скриншот сюда.",
        "💰 Ақылы хабарландыру үшін Kaspi-ге 1000₸ жіберіңіз:\n📱 +7 777 777 7777\nТөлем жасаған соң скриншот жіберіңіз.")
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: m.text in ["📋 Мои объявления", "📋 Менің хабарландыруларым"])
def my_ads(message):
    cursor.execute("SELECT text FROM ads WHERE user_id = ?", (message.from_user.id,))
    ads = cursor.fetchall()
    if not ads:
        bot.send_message(message.chat.id, get_text(message.from_user.id, "У вас нет объявлений.", "Сізде хабарландыру жоқ."))
    else:
        for ad in ads:
            bot.send_message(message.chat.id, ad[0])

@bot.message_handler(func=lambda m: m.text in ["ℹ️ Помощь", "ℹ️ Көмек"])
def help_message(message):
    text = get_text(message.from_user.id,
        "ℹ️ Чтобы добавить объявление, выберите категорию и отправьте текст.\nПлатные объявления публикуются в канале.",
        "ℹ️ Хабарландыру қосу үшін санатты таңдап, мәтінді жіберіңіз.\nАқылы хабарландырулар арнада жарияланады.")
    bot.send_message(message.chat.id, text)

# 🔧 Админ-панель
@bot.message_handler(func=lambda m: m.text == "🔧 Админ-панель")
def admin_panel(message):
    if message.from_user.id != ADMIN_ID:
        return
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📋 Все объявления", callback_data="admin_all_ads"))
    markup.add(types.InlineKeyboardButton("❌ Удалить объявление", callback_data="admin_delete"))
    markup.add(types.InlineKeyboardButton("🔄 Обновить", callback_data="admin_refresh"))
    bot.send_message(message.chat.id, "🔐 Админ-панель:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_"))
def handle_admin_panel(call):
    if call.from_user.id != ADMIN_ID:
        return

    if call.data == "admin_all_ads":
        cursor.execute("SELECT id, user_id, text, is_paid FROM ads")
        ads = cursor.fetchall()
        if not ads:
            bot.send_message(call.message.chat.id, "❌ Объявлений нет.")
        else:
            for ad in ads:
                paid = "💰" if ad[3] else ""
                msg = f"🆔 {ad[0]} | 👤 {ad[1]} {paid}\n{ad[2]}"
                bot.send_message(call.message.chat.id, msg[:4096])

    elif call.data == "admin_delete":
        bot.send_message(call.message.chat.id, "✏️ Напиши команду: `/delete ID`", parse_mode="Markdown")

    elif call.data == "admin_refresh":
        admin_panel(call.message)

@bot.message_handler(commands=['delete'])
def delete_ad(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        ad_id = int(message.text.split()[1])
        cursor.execute("DELETE FROM ads WHERE id = ?", (ad_id,))
        conn.commit()
        bot.send_message(message.chat.id, f"✅ Объявление {ad_id} удалено.")
    except:
        bot.send_message(message.chat.id, "❗ Использование: /delete [ID]")

# 🟢 Запуск
bot.polling(non_stop=True)