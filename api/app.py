from flask import Flask, request
import telebot
import os
import platform
from datetime import datetime

TOKEN = os.environ.get("BOT_TOKEN")

bot = telebot.TeleBot(TOKEN)

app = Flask(__name__)

# ---------------- WEB ---------------- #

@app.route("/")
def home():
    return "Late-X Bot Running Successfully!"

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    json_str = request.get_data().decode("UTF-8")
    update = telebot.types.Update.de_json(json_str)

    bot.process_new_updates([update])

    return "OK", 200

# ---------------- BOT COMMANDS ---------------- #

@bot.message_handler(commands=['start'])
def start(message):
    text = """
🚀 Welcome to Late-X Bot!

Available Commands:

/start - Start bot
/help - Show commands
/ping - Check bot speed
/time - Current server time
/info - Bot information
/system - Server information
/about - About this bot
"""
    bot.reply_to(message, text)

@bot.message_handler(commands=['help'])
def help_cmd(message):
    text = """
📚 Help Menu

/start → Start the bot
/ping → Check bot status
/time → Show current time
/system → Show server info
/about → About bot
"""
    bot.reply_to(message, text)

@bot.message_handler(commands=['ping'])
def ping(message):
    bot.reply_to(message, "🏓 Pong! Bot is online.")

@bot.message_handler(commands=['time'])
def time_cmd(message):
    current_time = datetime.now().strftime("%H:%M:%S")
    bot.reply_to(message, f"⏰ Server Time: {current_time}")

@bot.message_handler(commands=['info'])
def info(message):
    text = f"""
🤖 Bot Information

Username: @{bot.get_me().username}
Bot Name: {bot.get_me().first_name}
"""
    bot.reply_to(message, text)

@bot.message_handler(commands=['system'])
def system(message):
    text = f"""
💻 System Information

OS: {platform.system()}
Release: {platform.release()}
Python: {platform.python_version()}
"""
    bot.reply_to(message, text)

@bot.message_handler(commands=['about'])
def about(message):
    bot.reply_to(
        message,
        "⚡ Late-X Telegram Bot hosted on Vercel using Flask webhook."
    )

# ---------------- RUN ---------------- #

app = app