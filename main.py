# main.py
import telebot
from telebot import types
import sqlite3
import os
from flask import Flask
from threading import Thread

TOKEN = os.getenv("TOKEN")
bot = telebot.TeleBot(TOKEN)

# Админ ID для управления ботом
ADMIN_ID = 6864791335  # ← замени на свой Telegram ID
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

def keep_alive():
    t = Thread(target=run_flask)
    t.start()

# Подключение к SQLite
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

user_lang = {}
pending_paid_ads = {}

def main_menu(lang, user_id=None):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if lang == "kz":
        markup.row("📢 Жұмыс", "🏠 Жалдау")
        markup.row("➕ Хабарландыру қосу", "📋 Менің хабарландыруларым")
        markup.row("ℹ️ Көмек", "💰 Ақылы хабарландыру")
        if user_id == ADMIN_ID:
            markup.row("🛠 Админ-панель")
    else:
        markup.row("📢 Вакансии", "🏠 Аренда")
        markup.row("➕ Добавить объявление", "📋 Мои объявления")
        markup.row("ℹ️ Помощь", "💰 Платное объявление")
        if user_id == ADMIN_ID:
            markup.row("🛠 Админ-панель")
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"))
    markup.add(types.InlineKeyboardButton("🇰🇿 Қазақша", callback_data="lang_kz"))
    bot.send_message(message.chat.id, "👋 Добро пожаловать в Kyzylorda Helper!\nТілді таңдаңыз / Выберите язык:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("lang_"))
def choose_language(call):
    lang = call.data.split("_")[1]
    user_lang[call.from_user.id] = lang
    text = "✅ Қазақ тілі таңдалды." if lang == "kz" else "✅ Русский язык выбран."
    bot.send_message(call.message.chat.id, text, reply_markup=main_menu(lang, call.from_user.id))

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    if message.chat.id == ADMIN_ID and message.reply_to_message:
        ad_text = message.reply_to_message.text
        bot.send_message(CHANNEL_ID, "💰 Платное объявление\n\n" + ad_text)
    else:
        bot.send_message(ADMIN_ID, f"🖼 Скрин оплаты от @{message.from_user.username or message.from_user.id}")
        bot.forward_message(ADMIN_ID, message.chat.id, message.message_id)

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    lang = user_lang.get(message.from_user.id, "ru")
    text = message.text

    if lang == "kz":
        if text == "📢 Жұмыс":
            bot.send_message(message.chat.id, "Мұнда жұмыстар көрсетіледі.")
        elif text == "🏠 Жалдау":
            bot.send_message(message.chat.id, "Мұнда жалға алу ұсыныстары көрсетіледі.")
        elif text == "➕ Хабарландыру қосу":
            bot.send_message(message.chat.id, "Хабарландыру мәтінін жіберіңіз:")
            bot.register_next_step_handler(message, lambda msg: save_ad(msg, "kz", is_paid=False))
        elif text == "💰 Ақылы хабарландыру":
            bot.send_message(message.chat.id, f"💳 Ақылы жарнама үшін {PRICE}₸ төлеңіз:\nKaspi: {KASPI_CARD}\n\n📸 Төлем скриншотын жіберіңіз.")
            bot.send_message(message.chat.id, "Хабарландыру мәтінін жіберіңіз:")
            bot.register_next_step_handler(message, lambda msg: save_ad(msg, "kz", is_paid=True))
        elif text == "📋 Менің хабарландыруларым":
            show_user_ads(message, lang)
        elif text == "ℹ️ Көмек":
            bot.send_message(message.chat.id, "Бұл бот арқылы сіз хабарландырулар қосып, көруіңізге болады.")
        elif text == "🛠 Админ-панель" and message.from_user.id == ADMIN_ID:
            admin_panel(message)
        else:
            bot.send_message(message.chat.id, "Түсінбедім. Басты мәзірден таңдаңыз.", reply_markup=main_menu(lang, message.from_user.id))
    else:
        if text == "📢 Вакансии":
            bot.send_message(message.chat.id, "Здесь будут отображаться вакансии.")
        elif text == "🏠 Аренда":
            bot.send_message(message.chat.id, "Здесь будут показываться объявления по аренде.")
        elif text == "➕ Добавить объявление":
            bot.send_message(message.chat.id, "Пожалуйста, отправьте текст объявления:")
            bot.register_next_step_handler(message, lambda msg: save_ad(msg, "ru", is_paid=False))
        elif text == "💰 Платное объявление":
            bot.send_message(message.chat.id, f"💳 Для платного объявления переведите {PRICE}₸ на Kaspi:\n{KASPI_CARD}\n\n📸 Отправьте скрин оплаты сюда.")
            bot.send_message(message.chat.id, "Отправьте текст платного объявления:")
            bot.register_next_step_handler(message, lambda msg: save_ad(msg, "ru", is_paid=True))
        elif text == "📋 Мои объявления":
            show_user_ads(message, lang)
        elif text == "ℹ️ Помощь":
            bot.send_message(message.chat.id, "С помощью этого бота вы можете размещать и просматривать объявления.")
        elif text == "🛠 Админ-панель" and message.from_user.id == ADMIN_ID:
            admin_panel(message)
        else:
            bot.send_message(message.chat.id, "Я не понял. Выберите из меню.", reply_markup=main_menu(lang, message.from_user.id))

def save_ad(message, lang, is_paid):
    user_id = message.from_user.id
    text = message.text
    cursor.execute("INSERT INTO ads (user_id, text, category, is_paid) VALUES (?, ?, ?, ?)", (user_id, text, "", int(is_paid)))
    conn.commit()

    if is_paid:
        bot.send_message(user_id, "📸 Пожалуйста, отправьте скрин оплаты в этот чат.")
        bot.send_message(ADMIN_ID, f"🔔 Новое платное объявление от @{message.from_user.username or user_id}:\n\n{text}")
    else:
        bot.send_message(CHANNEL_ID, text)
        msg = "✅ Хабарландыру сақталды." if lang == "kz" else "✅ Объявление опубликовано."
        bot.send_message(user_id, msg, reply_markup=main_menu(lang, user_id))

def show_user_ads(message, lang):
    cursor.execute("SELECT id, text FROM ads WHERE user_id = ?", (message.from_user.id,))
    ads = cursor.fetchall()
    if not ads:
        msg = "Сізде хабарландырулар жоқ." if lang == "kz" else "У вас нет объявлений."
    else:
        msg = "\n\n".join([f"🆔 {ad[0]}:\n{ad[1]}" for ad in ads])
    bot.send_message(message.chat.id, msg)

# 🔒 Админ-панель
@bot.message_handler(commands=['admin'])
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
keep_alive()
bot.polling(non_stop=True)