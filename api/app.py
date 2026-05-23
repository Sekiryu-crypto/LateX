from flask import Flask, request
import telebot
import os
import time

# ---------------- CONFIG ---------------- #

TOKEN = os.getenv("BOT_TOKEN")

bot = telebot.TeleBot(TOKEN)

app = Flask(__name__)

START_TIME = time.time()

# ---------------- HOME PAGE ---------------- #

@app.route("/", methods=["GET"])
def home():

    uptime = int(time.time() - START_TIME)

    return f"""
🚀 Late-X Bot Running Successfully!

Status: Online
Uptime: {uptime} seconds
"""

# ---------------- WEBHOOK ---------------- #

@app.route("/api/webhook", methods=["POST", "GET"])
def webhook():

    if request.method == "POST":

        json_str = request.stream.read().decode("utf-8")

        update = telebot.types.Update.de_json(json_str)

        bot.process_new_updates([update])

        return "OK", 200

    return "Webhook Active", 200

# ---------------- BOT COMMANDS ---------------- #

@bot.message_handler(commands=['start'])
def start(message):

    bot.reply_to(
        message,
        "🚀 Late-X Bot is working successfully on Vercel!"
    )

@bot.message_handler(commands=['ping'])
def ping(message):

    bot.reply_to(
        message,
        "🏓 Pong!"
    )

@bot.message_handler(commands=['help'])
def help_command(message):

    bot.reply_to(
        message,
        """
📚 Available Commands

/start - Start bot
/ping - Check bot
/help - Show commands
/uptime - Bot uptime
"""
    )

@bot.message_handler(commands=['uptime'])
def uptime(message):

    uptime_seconds = int(time.time() - START_TIME)

    bot.reply_to(
        message,
        f"⏱ Bot Uptime: {uptime_seconds} seconds"
    )

# ---------------- IMPORTANT ---------------- #

app = app