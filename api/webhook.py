import os
import logging
from datetime import datetime, timedelta

from telegram import (
    Update,
    ChatPermissions
)

from telegram.constants import ChatMemberStatus

from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes
)

# ================= CONFIG =================

BOT_TOKEN = "7468327119:AAFzswUn3TAcDhI_OE62YP9AeEAl5JLm05w"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ================= MEMORY =================

warnings_db = {}

# ================= HELPERS =================

async def is_admin(chat, user_id):
    member = await chat.get_member(user_id)
    return member.status in (
        ChatMemberStatus.ADMINISTRATOR,
        ChatMemberStatus.OWNER
    )

async def get_target_user(update, context):
    if update.message.reply_to_message:
        return update.message.reply_to_message.from_user

    if context.args:
        try:
            user_id = int(context.args[0])
            chat_member = await update.effective_chat.get_member(user_id)
            return chat_member.user
        except:
            return None

    return None

# ================= COMMANDS =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Advanced Telegram Management Bot Online!"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """
🛠 COMMANDS

/ban
/unban
/kick
/mute
/unmute
/warn
/warns
/id
/ping
"""
    await update.message.reply_text(text)

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start = datetime.now()

    msg = await update.message.reply_text("🏓 Pinging...")

    latency = (datetime.now() - start).total_seconds() * 1000

    await msg.edit_text(f"🏓 Pong: {latency:.2f}ms")

async def user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"""
👤 User ID: {update.effective_user.id}
💬 Chat ID: {update.effective_chat.id}
"""
    )

# ================= MODERATION =================

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    if not await is_admin(update.effective_chat, user.id):
        return await update.message.reply_text("❌ Admin only.")

    target = await get_target_user(update, context)

    if not target:
        return await update.message.reply_text(
            "Reply to a user or provide user ID."
        )

    try:
        await update.effective_chat.ban_member(target.id)

        await update.message.reply_text(
            f"🔨 Banned {target.mention_html()}",
            parse_mode="HTML"
        )

    except Exception as e:
        await update.message.reply_text(f"❌ {e}")

async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    if not await is_admin(update.effective_chat, user.id):
        return await update.message.reply_text("❌ Admin only.")

    target = await get_target_user(update, context)

    if not target:
        return await update.message.reply_text(
            "Reply to a user or provide user ID."
        )

    try:
        await update.effective_chat.unban_member(target.id)

        await update.message.reply_text(
            f"✅ Unbanned {target.mention_html()}",
            parse_mode="HTML"
        )

    except Exception as e:
        await update.message.reply_text(f"❌ {e}")

async def kick(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    if not await is_admin(update.effective_chat, user.id):
        return await update.message.reply_text("❌ Admin only.")

    target = await get_target_user(update, context)

    if not target:
        return await update.message.reply_text(
            "Reply to a user or provide user ID."
        )

    try:
        await update.effective_chat.ban_member(
            target.id,
            until_date=datetime.now() + timedelta(seconds=5)
        )

        await update.effective_chat.unban_member(target.id)

        await update.message.reply_text(
            f"👢 Kicked {target.mention_html()}",
            parse_mode="HTML"
        )

    except Exception as e:
        await update.message.reply_text(f"❌ {e}")

async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    if not await is_admin(update.effective_chat, user.id):
        return await update.message.reply_text("❌ Admin only.")

    target = await get_target_user(update, context)

    if not target:
        return await update.message.reply_text(
            "Reply to a user or provide user ID."
        )

    minutes = 10

    if len(context.args) > 1:
        try:
            minutes = int(context.args[1])
        except:
            pass

    try:
        await update.effective_chat.restrict_member(
            target.id,
            permissions=ChatPermissions(
                can_send_messages=False
            ),
            until_date=datetime.now() + timedelta(minutes=minutes)
        )

        await update.message.reply_text(
            f"🔇 Muted {target.mention_html()} for {minutes}m",
            parse_mode="HTML"
        )

    except Exception as e:
        await update.message.reply_text(f"❌ {e}")

async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    if not await is_admin(update.effective_chat, user.id):
        return await update.message.reply_text("❌ Admin only.")

    target = await get_target_user(update, context)

    if not target:
        return await update.message.reply_text(
            "Reply to a user or provide user ID."
        )

    try:
        await update.effective_chat.restrict_member(
            target.id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True
            )
        )

        await update.message.reply_text(
            f"🔊 Unmuted {target.mention_html()}",
            parse_mode="HTML"
        )

    except Exception as e:
        await update.message.reply_text(f"❌ {e}")

async def warn(update: Update, context: ContextTypes.DEFAULT_TYPE):

    admin = update.effective_user

    if not await is_admin(update.effective_chat, admin.id):
        return await update.message.reply_text("❌ Admin only.")

    target = await get_target_user(update, context)

    if not target:
        return await update.message.reply_text(
            "Reply to a user."
        )

    key = f"{update.effective_chat.id}:{target.id}"

    warnings_db[key] = warnings_db.get(key, 0) + 1

    count = warnings_db[key]

    await update.message.reply_text(
        f"⚠️ {target.mention_html()} warned ({count}/3)",
        parse_mode="HTML"
    )

    if count >= 3:

        warnings_db[key] = 0

        await update.effective_chat.restrict_member(
            target.id,
            permissions=ChatPermissions(
                can_send_messages=False
            ),
            until_date=datetime.now() + timedelta(hours=24)
        )

        await update.message.reply_text(
            f"🔇 {target.mention_html()} muted for 24h",
            parse_mode="HTML"
        )

async def warns(update: Update, context: ContextTypes.DEFAULT_TYPE):

    target = await get_target_user(update, context)

    if not target:
        target = update.effective_user

    key = f"{update.effective_chat.id}:{target.id}"

    count = warnings_db.get(key, 0)

    await update.message.reply_text(
        f"⚠️ Warnings: {count}/3"
    )

# ================= APPLICATION =================

app = (
    Application.builder()
    .token(BOT_TOKEN)
    .updater(None)
    .build()
)

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(CommandHandler("ping", ping))
app.add_handler(CommandHandler("id", user_id))

app.add_handler(CommandHandler("ban", ban))
app.add_handler(CommandHandler("unban", unban))
app.add_handler(CommandHandler("kick", kick))
app.add_handler(CommandHandler("mute", mute))
app.add_handler(CommandHandler("unmute", unmute))
app.add_handler(CommandHandler("warn", warn))
app.add_handler(CommandHandler("warns", warns))

# ================= VERCEL HANDLER =================

async def handler(request):

    if request.method != "POST":
        return {
            "statusCode": 200,
            "body": "Telegram bot is running."
        }

    try:

        data = await request.json()

        update = Update.de_json(data, app.bot)

        await app.initialize()
        await app.process_update(update)

        return {
            "statusCode": 200,
            "body": "ok"
        }

    except Exception as e:
        logging.error(str(e))

        return {
            "statusCode": 500,
            "body": str(e)
        }