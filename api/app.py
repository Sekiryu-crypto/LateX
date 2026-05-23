from flask import Flask, request
import telebot
import os

TOKEN = os.getenv("BOT_TOKEN")

bot = telebot.TeleBot(TOKEN)

app = Flask(__name__)

# Home page
@app.route("/", methods=["GET"])
def home():
    return "Late-X Bot Running Successfully!"

# Telegram webhook
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = telebot.types.Update.de_json(
        request.stream.read().decode("utf-8")
    )

    bot.process_new_updates([update])

    return "OK", 200

# Start command
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(
        message,
        "🚀 Late-X Bot is working successfully on Vercel!"
    )

# Ping command
@bot.message_handler(commands=['ping'])
def ping(message):
    bot.reply_to(message, "🏓 Pong!")

# Help command
@bot.message_handler(commands=['help'])
def help_command(message):
    bot.reply_to(
        message,
        "/start - Start bot\n"
        "/ping - Check bot\n"
        "/help - Commands"
    )

# Important for Vercel
app = app