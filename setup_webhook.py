#!/usr/bin/env python3
"""
setup_webhook.py
~~~~~~~~~~~~~~~~
Run this ONCE after you deploy to Vercel to tell Telegram where to send updates.

Usage:
    BOT_TOKEN=<token> VERCEL_URL=<your-app>.vercel.app python setup_webhook.py

Or if you have a custom domain:
    BOT_TOKEN=<token> VERCEL_URL=mybot.example.com python setup_webhook.py
"""

import asyncio
import os
import sys

try:
    from telegram import Bot
except ImportError:
    print("❌  Run:  pip install python-telegram-bot==20.6")
    sys.exit(1)

BOT_TOKEN  = os.environ.get("BOT_TOKEN",  "").strip()
VERCEL_URL = os.environ.get("VERCEL_URL", "").strip().rstrip("/")

if not BOT_TOKEN:
    print("❌  Set BOT_TOKEN environment variable first.")
    sys.exit(1)
if not VERCEL_URL:
    print("❌  Set VERCEL_URL environment variable first (e.g. mybot.vercel.app).")
    sys.exit(1)

WEBHOOK_URL = f"https://{VERCEL_URL}/webhook"


async def main() -> None:
    bot = Bot(token=BOT_TOKEN)

    print(f"🔗  Setting webhook → {WEBHOOK_URL}")
    await bot.set_webhook(
        url=WEBHOOK_URL,
        allowed_updates=["message", "callback_query", "chat_member"],
        drop_pending_updates=True,
        max_connections=40,
    )

    info = await bot.get_webhook_info()
    print(f"✅  Webhook active:  {info.url}")
    print(f"    Pending updates: {info.pending_update_count}")
    if info.last_error_message:
        print(f"    ⚠️  Last error:     {info.last_error_message}")
    else:
        print("    No errors — you're good to go! 🚀")


if __name__ == "__main__":
    asyncio.run(main())
