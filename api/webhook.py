import os
import json
import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ================= LOGGING =================
logging.basicConfig(level=logging.INFO)

# ================= BOT TOKEN =================
BOT_TOKEN = os.environ.get("7468327119:AAFzswUn3TAcDhI_OE62YP9AeEAl5JLm05w")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set in Vercel environment variables")

# ================= APPLICATION =================
app = Application.builder().token(BOT_TOKEN).build()

# ================= COMMANDS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot is alive on Vercel")

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏓 Pong")

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("ping", ping))

# initialize once at cold start
import asyncio
asyncio.get_event_loop().run_until_complete(app.initialize())

# ================= VERCEL HANDLER =================
def handler(request):
    try:
        if request.method == "GET":
            return {
                "statusCode": 200,
                "body": "Bot running"
            }

        if request.method != "POST":
            return {
                "statusCode": 405,
                "body": "Method not allowed"
            }

        body = request.get_body().decode("utf-8")
        data = json.loads(body)

        update = Update.de_json(data, app.bot)

        # IMPORTANT: run sync-safe (NO async loops in Vercel)
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        loop.run_until_complete(app.process_update(update))

        return {
            "statusCode": 200,
            "body": "ok"
        }

    except Exception as e:
        logging.exception(e)

        return {
            "statusCode": 500,
            "body": str(e)
        }