# main.py
import telebot
import sqlite3
import os

TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(
        message.chat.id,
        "👋 Қош келдіңіз / Добро пожаловать в *Kyzylorda Helper*!",
        parse_mode="Markdown"
    )

# Добавим обработчики позже

bot.polling()
