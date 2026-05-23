from pyrogram import Client, filters, enums
from pyrogram.types import Message, ChatPermissions, ChatPrivileges
from dotenv import load_dotenv
from googletrans import Translator
from datetime import datetime, timedelta

import asyncio
import random
import time
import os

# -------------------- LOAD ENV --------------------

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# -------------------- BOT INIT --------------------

app = Client(
    "group_manager_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# -------------------- STORAGE --------------------

warnings_db = {}
notes_db = {}

rules_text = (
    "📜 Group Rules:\n"
    "1. Respect everyone\n"
    "2. No spam\n"
    "3. Follow admin instructions"
)

welcome_message = "👋 Welcome {mention} to {title}!"

translator = Translator()

# -------------------- HELPERS --------------------

async def is_admin(client, chat_id: int, user_id: int):
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in [
            enums.ChatMemberStatus.ADMINISTRATOR,
            enums.ChatMemberStatus.OWNER
        ]
    except:
        return False


async def require_admin(client, message: Message):
    if not await is_admin(client, message.chat.id, message.from_user.id):
        await message.reply("⛔ You must be an admin to use this command.")
        return False
    return True


async def get_target_user(client, message: Message):

    if message.reply_to_message:
        return message.reply_to_message.from_user

    if len(message.command) < 2:
        return None

    user_input = message.command[1]

    try:
        if user_input.isdigit():
            return await client.get_users(int(user_input))

        if user_input.startswith("@"):
            return await client.get_users(user_input)

    except Exception:
        return None

    return None


def mention(user):
    if user.username:
        return f"@{user.username}"
    return user.mention

# -------------------- START --------------------

@app.on_message(filters.command("start") & filters.private)
async def start(_, message: Message):
    await message.reply(
        "👋 Hello!\n\n"
        "I am an advanced Telegram Group Management Bot.\n"
        "Add me to your group and promote me as admin."
    )

# -------------------- HELP --------------------

@app.on_message(filters.command("help"))
async def help_command(_, message: Message):

    text = """
🛠 Group Management Bot

👮 Moderation:
/ban
/unban
/kick
/mute
/unmute
/warn
/unwarn
/warns
/purge
/pin
/unpin

📝 Group:
/setrules
/rules
/setwelcome
/welcome
/report
/staff

💾 Utility:
/setnote
/getnote
/id
/info
/translate

🎉 Fun:
/slap
/roll
/coin
/say
/ping
    """

    await message.reply(text)

# -------------------- PING --------------------

@app.on_message(filters.command("ping"))
async def ping(_, message: Message):

    start = time.time()

    msg = await message.reply("🏓 Pinging...")

    end = time.time()

    await msg.edit(
        f"🏓 Pong! {(end - start) * 1000:.2f} ms"
    )

# -------------------- BAN --------------------

@app.on_message(filters.command("ban") & filters.group)
async def ban_user(client, message: Message):

    if not await require_admin(client, message):
        return

    target = await get_target_user(client, message)

    if not target:
        await message.reply("⚠ Reply to a user or provide username.")
        return

    try:
        await client.ban_chat_member(message.chat.id, target.id)

        await message.reply(
            f"🔨 Banned {mention(target)}"
        )

    except Exception as e:
        await message.reply(f"❌ Error: {e}")

# -------------------- UNBAN --------------------

@app.on_message(filters.command("unban") & filters.group)
async def unban_user(client, message: Message):

    if not await require_admin(client, message):
        return

    target = await get_target_user(client, message)

    if not target:
        await message.reply("⚠ Reply to a user or provide username.")
        return

    try:
        await client.unban_chat_member(message.chat.id, target.id)

        await message.reply(
            f"✅ Unbanned {mention(target)}"
        )

    except Exception as e:
        await message.reply(f"❌ Error: {e}")

# -------------------- KICK --------------------

@app.on_message(filters.command("kick") & filters.group)
async def kick_user(client, message: Message):

    if not await require_admin(client, message):
        return

    target = await get_target_user(client, message)

    if not target:
        await message.reply("⚠ Reply to a user.")
        return

    try:
        await client.ban_chat_member(
            message.chat.id,
            target.id,
            until_date=datetime.now() + timedelta(seconds=10)
        )

        await client.unban_chat_member(message.chat.id, target.id)

        await message.reply(f"👢 Kicked {mention(target)}")

    except Exception as e:
        await message.reply(f"❌ Error: {e}")

# -------------------- MUTE --------------------

@app.on_message(filters.command("mute") & filters.group)
async def mute_user(client, message: Message):

    if not await require_admin(client, message):
        return

    target = await get_target_user(client, message)

    if not target:
        await message.reply("⚠ Reply to a user.")
        return

    duration = 10

    if len(message.command) >= 3:
        try:
            duration = int(message.command[2])
        except:
            pass

    try:
        permissions = ChatPermissions()

        await client.restrict_chat_member(
            message.chat.id,
            target.id,
            permissions=permissions,
            until_date=datetime.now() + timedelta(minutes=duration)
        )

        await message.reply(
            f"🔇 Muted {mention(target)} for {duration} minutes"
        )

    except Exception as e:
        await message.reply(f"❌ Error: {e}")

# -------------------- UNMUTE --------------------

@app.on_message(filters.command("unmute") & filters.group)
async def unmute_user(client, message: Message):

    if not await require_admin(client, message):
        return

    target = await get_target_user(client, message)

    if not target:
        await message.reply("⚠ Reply to a user.")
        return

    try:
        permissions = ChatPermissions(
            can_send_messages=True,
            can_send_media_messages=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True
        )

        await client.restrict_chat_member(
            message.chat.id,
            target.id,
            permissions=permissions
        )

        await message.reply(f"🔊 Unmuted {mention(target)}")

    except Exception as e:
        await message.reply(f"❌ Error: {e}")

# -------------------- WARN --------------------

@app.on_message(filters.command("warn") & filters.group)
async def warn_user(client, message: Message):

    if not await require_admin(client, message):
        return

    target = await get_target_user(client, message)

    if not target:
        await message.reply("⚠ Reply to a user.")
        return

    chat_id = message.chat.id
    user_id = target.id

    if chat_id not in warnings_db:
        warnings_db[chat_id] = {}

    if user_id not in warnings_db[chat_id]:
        warnings_db[chat_id][user_id] = 0

    warnings_db[chat_id][user_id] += 1

    count = warnings_db[chat_id][user_id]

    if count >= 3:

        permissions = ChatPermissions()

        await client.restrict_chat_member(
            chat_id,
            user_id,
            permissions=permissions,
            until_date=datetime.now() + timedelta(hours=24)
        )

        warnings_db[chat_id][user_id] = 0

        await message.reply(
            f"🔇 {mention(target)} muted for 24 hours due to warnings."
        )

    else:
        await message.reply(
            f"⚠ {mention(target)} warned ({count}/3)"
        )

# -------------------- WARNS --------------------

@app.on_message(filters.command("warns") & filters.group)
async def warns(_, message: Message):

    if message.reply_to_message:
        target = message.reply_to_message.from_user
    else:
        target = message.from_user

    chat_id = message.chat.id
    user_id = target.id

    count = warnings_db.get(chat_id, {}).get(user_id, 0)

    await message.reply(
        f"⚠ {mention(target)} has {count}/3 warnings"
    )

# -------------------- RULES --------------------

@app.on_message(filters.command("rules") & filters.group)
async def rules(_, message: Message):
    await message.reply(rules_text)

# -------------------- SET RULES --------------------

@app.on_message(filters.command("setrules") & filters.group)
async def setrules(client, message: Message):

    global rules_text

    if not await require_admin(client, message):
        return

    if len(message.command) < 2:
        await message.reply("⚠ Usage: /setrules text")
        return

    rules_text = message.text.split(None, 1)[1]

    await message.reply("✅ Rules updated")

# -------------------- WELCOME --------------------

@app.on_message(filters.new_chat_members)
async def welcome(_, message: Message):

    for user in message.new_chat_members:

        text = welcome_message.replace(
            "{mention}",
            user.mention
        ).replace(
            "{title}",
            message.chat.title
        )

        await message.reply(text)

# -------------------- SET WELCOME --------------------

@app.on_message(filters.command("setwelcome") & filters.group)
async def setwelcome(client, message: Message):

    global welcome_message

    if not await require_admin(client, message):
        return

    if len(message.command) < 2:
        await message.reply("⚠ Usage: /setwelcome text")
        return

    welcome_message = message.text.split(None, 1)[1]

    await message.reply("✅ Welcome message updated")

# -------------------- NOTES --------------------

@app.on_message(filters.command("setnote") & filters.group)
async def setnote(_, message: Message):

    if len(message.command) < 3:
        await message.reply("⚠ Usage: /setnote name text")
        return

    chat_id = message.chat.id

    name = message.command[1].lower()

    text = " ".join(message.command[2:])

    if chat_id not in notes_db:
        notes_db[chat_id] = {}

    notes_db[chat_id][name] = text

    await message.reply(f"📝 Note '{name}' saved")

# -------------------- GET NOTE --------------------

@app.on_message(filters.command("getnote") & filters.group)
async def getnote(_, message: Message):

    if len(message.command) < 2:
        await message.reply("⚠ Usage: /getnote name")
        return

    chat_id = message.chat.id

    name = message.command[1].lower()

    note = notes_db.get(chat_id, {}).get(name)

    if note:
        await message.reply(note)
    else:
        await message.reply("❌ Note not found")

# -------------------- TRANSLATE --------------------

@app.on_message(filters.command("translate"))
async def translate(_, message: Message):

    if len(message.command) < 2:
        await message.reply("⚠ Usage: /translate text")
        return

    text = " ".join(message.command[1:])

    try:
        translated = translator.translate(text, dest="en")

        await message.reply(
            f"🌐 Translation:\n\n{translated.text}"
        )

    except Exception as e:
        await message.reply(f"❌ Error: {e}")

# -------------------- ID --------------------

@app.on_message(filters.command("id"))
async def ids(_, message: Message):

    if message.reply_to_message:

        user = message.reply_to_message.from_user

        await message.reply(
            f"👤 {mention(user)}\nID: `{user.id}`"
        )

    else:

        await message.reply(
            f"👤 Your ID: `{message.from_user.id}`\n"
            f"💬 Chat ID: `{message.chat.id}`"
        )

# -------------------- INFO --------------------

@app.on_message(filters.command("info"))
async def info(client, message: Message):

    target = await get_target_user(client, message)

    if not target:
        target = message.from_user

    try:

        member = await client.get_chat_member(
            message.chat.id,
            target.id
        )

        text = (
            f"👤 User Info\n\n"
            f"🆔 ID: `{target.id}`\n"
            f"📛 Name: {target.first_name}\n"
            f"👤 Username: @{target.username if target.username else 'None'}\n"
            f"🛡 Status: {member.status.name}"
        )

        await message.reply(text)

    except Exception as e:
        await message.reply(f"❌ Error: {e}")

# -------------------- FUN --------------------

@app.on_message(filters.command("slap") & filters.group)
async def slap(_, message: Message):

    if not message.reply_to_message:
        await message.reply("⚠ Reply to someone")
        return

    target = message.reply_to_message.from_user

    await message.reply(
        f"👋 {message.from_user.mention} slapped {target.mention}!"
    )

@app.on_message(filters.command("roll"))
async def roll(_, message: Message):
    await message.reply(f"🎲 {random.randint(1, 6)}")

@app.on_message(filters.command("coin"))
async def coin(_, message: Message):

    result = random.choice(["Heads", "Tails"])

    await message.reply(f"🪙 {result}")

@app.on_message(filters.command("say"))
async def say(_, message: Message):

    if len(message.command) < 2:
        await message.reply("⚠ Usage: /say text")
        return

    text = message.text.split(None, 1)[1]

    await message.reply(text)

# -------------------- RUN --------------------

if __name__ == "__main__":
    print("✅ Group Manager Bot Started")
    app.run()