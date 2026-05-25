from flask import Flask, request
import telebot
from telebot.types import ChatPermissions
import os
import time
import random
import datetime

# ---------------- CONFIG ---------------- #

TOKEN = os.getenv("BOT_TOKEN")

bot = telebot.TeleBot(TOKEN)

app = Flask(__name__)

START_TIME = time.time()

# ---------------- HELPERS ---------------- #

def is_group(message):
    return message.chat.type in ['group', 'supergroup']

def is_admin(chat_id, user_id):
    try:
        member = bot.get_chat_member(chat_id, user_id)
        return member.status in ['administrator', 'creator']
    except:
        return False

def bot_is_admin(chat_id):
    try:
        bot_member = bot.get_chat_member(chat_id, bot.get_me().id)
        return bot_member.status in ['administrator', 'creator']
    except:
        return False

def get_target_user(message):
    """Returns (user_id, username) or (None, None) if not found."""
    if message.reply_to_message:
        u = message.reply_to_message.from_user
        return u.id, u.first_name
    parts = message.text.split()
    if len(parts) > 1:
        username = parts[1]
        try:
            member = bot.get_chat_member(message.chat.id, username)
            u = member.user
            return u.id, u.first_name
        except:
            bot.reply_to(message, "❌ User not found.")
            return None, None
    bot.reply_to(message, "❌ Reply to a user or provide @username.")
    return None, None

def format_uptime(seconds):
    d = seconds // 86400
    h = (seconds % 86400) // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    parts = []
    if d: parts.append(f"{d}d")
    if h: parts.append(f"{h}h")
    if m: parts.append(f"{m}m")
    parts.append(f"{s}s")
    return " ".join(parts)

# ---------------- HOME PAGE ---------------- #

@app.route("/", methods=["GET"])
def home():
    uptime = int(time.time() - START_TIME)
    return f"""
<html>
<body style="font-family:monospace;background:#0f0f0f;color:#00ff88;padding:40px">
<h2>🚀 Late-X Bot</h2>
<p>Status: <b>Online</b></p>
<p>Uptime: <b>{format_uptime(uptime)}</b></p>
<p>Started: <b>{datetime.datetime.utcfromtimestamp(START_TIME).strftime('%Y-%m-%d %H:%M:%S UTC')}</b></p>
</body>
</html>
"""

# ---------------- KEEPALIVE (for UptimeRobot / cron-job.org) ---------------- #

@app.route("/api/keepalive", methods=["GET"])
def keepalive():
    return "alive", 200

# ---------------- WEBHOOK ---------------- #

@app.route("/api/webhook", methods=["POST", "GET"])
def webhook():
    if request.method == "POST":
        json_str = request.stream.read().decode("utf-8")
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
        return "OK", 200
    return "Webhook Active", 200

# ================================================================
#  BASIC COMMANDS
# ================================================================

@bot.message_handler(commands=['start'])
def start(message):
    name = message.from_user.first_name
    bot.reply_to(message, f"👋 Hey {name}! I'm Late-X Bot.\nType /help to see what I can do.")

@bot.message_handler(commands=['ping'])
def ping(message):
    bot.reply_to(message, "🏓 Pong!")

@bot.message_handler(commands=['uptime'])
def uptime_cmd(message):
    uptime_seconds = int(time.time() - START_TIME)
    bot.reply_to(message, f"⏱ Bot Uptime: {format_uptime(uptime_seconds)}")

@bot.message_handler(commands=['id'])
def get_id(message):
    text = f"👤 Your ID: `{message.from_user.id}`\n💬 Chat ID: `{message.chat.id}`"
    if message.reply_to_message:
        text += f"\n↩️ Replied-to ID: `{message.reply_to_message.from_user.id}`"
    bot.reply_to(message, text, parse_mode='Markdown')

@bot.message_handler(commands=['info'])
def user_info(message):
    u = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    name = f"{u.first_name} {u.last_name or ''}".strip()
    username = f"@{u.username}" if u.username else "None"
    bot.reply_to(message,
        f"👤 *User Info*\n"
        f"Name: {name}\n"
        f"Username: {username}\n"
        f"ID: `{u.id}`\n"
        f"Language: {u.language_code or 'Unknown'}",
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['help'])
def help_command(message):
    bot.reply_to(message, """
📚 *Late-X Bot Commands*

*Basic*
/start — Start bot
/ping — Check bot
/uptime — Bot uptime
/id — Your / chat ID
/info — User info
/help — This menu

*Group Management* (admin only)
/grouphelp — Group commands list

*Fun Commands*
/funhelp — Fun commands list
""", parse_mode='Markdown')

# ================================================================
#  GROUP MANAGEMENT COMMANDS
# ================================================================

@bot.message_handler(commands=['grouphelp'])
def group_help(message):
    if not is_group(message):
        bot.reply_to(message, "❌ This command works only in groups.")
        return
    bot.reply_to(message, """
👥 *Group Management Commands*
_(Bot must be admin)_

/kick — Remove user from group
/ban — Permanently ban user
/unban <user\_id> — Unban a user
/mute — Mute user (no messages)
/tmute <minutes> — Mute for X minutes
/unmute — Unmute user
/promote — Make admin
/demote — Remove admin rights
/warn — Warn a user (3 warns = ban)
/warns — Check user's warnings
/clearwarns — Clear user's warnings
/settitle <name> — Change group title
/setdesc <text> — Change description
/pin — Pin replied message
/unpin — Unpin current pinned msg
/purge — Delete msgs (reply = from that msg to now)
/membercount — Show member count

Use by replying to a user or with @username.
""", parse_mode='Markdown')

# --- Kick ---
@bot.message_handler(commands=['kick'])
def kick_user(message):
    if not is_group(message): return bot.reply_to(message, "❌ Groups only.")
    if not bot_is_admin(message.chat.id): return bot.reply_to(message, "❌ I need admin rights.")
    if not is_admin(message.chat.id, message.from_user.id): return bot.reply_to(message, "❌ You need admin rights.")

    user_id, name = get_target_user(message)
    if not user_id: return
    try:
        bot.ban_chat_member(message.chat.id, user_id)
        bot.unban_chat_member(message.chat.id, user_id)
        bot.reply_to(message, f"👢 *{name}* has been kicked.", parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, f"❌ Failed: {e}")

# --- Ban ---
@bot.message_handler(commands=['ban'])
def ban_user(message):
    if not is_group(message): return bot.reply_to(message, "❌ Groups only.")
    if not bot_is_admin(message.chat.id): return bot.reply_to(message, "❌ I need admin rights.")
    if not is_admin(message.chat.id, message.from_user.id): return bot.reply_to(message, "❌ You need admin rights.")

    user_id, name = get_target_user(message)
    if not user_id: return
    try:
        bot.ban_chat_member(message.chat.id, user_id)
        bot.reply_to(message, f"🔨 *{name}* has been banned.", parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, f"❌ Failed: {e}")

# --- Unban ---
@bot.message_handler(commands=['unban'])
def unban_user(message):
    if not is_group(message): return bot.reply_to(message, "❌ Groups only.")
    if not bot_is_admin(message.chat.id): return bot.reply_to(message, "❌ I need admin rights.")
    if not is_admin(message.chat.id, message.from_user.id): return bot.reply_to(message, "❌ You need admin rights.")

    parts = message.text.split()
    if len(parts) < 2:
        return bot.reply_to(message, "❌ Provide user_id: `/unban 123456789`", parse_mode='Markdown')
    try:
        user_id = int(parts[1])
        bot.unban_chat_member(message.chat.id, user_id)
        bot.reply_to(message, f"✅ User `{user_id}` unbanned.", parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, f"❌ Failed: {e}")

# --- Mute ---
@bot.message_handler(commands=['mute'])
def mute_user(message):
    if not is_group(message): return bot.reply_to(message, "❌ Groups only.")
    if not bot_is_admin(message.chat.id): return bot.reply_to(message, "❌ I need admin rights.")
    if not is_admin(message.chat.id, message.from_user.id): return bot.reply_to(message, "❌ You need admin rights.")

    user_id, name = get_target_user(message)
    if not user_id: return
    try:
        bot.restrict_chat_member(message.chat.id, user_id, ChatPermissions(can_send_messages=False))
        bot.reply_to(message, f"🔇 *{name}* has been muted.", parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, f"❌ Failed: {e}")

# --- Timed Mute ---
@bot.message_handler(commands=['tmute'])
def timed_mute(message):
    if not is_group(message): return bot.reply_to(message, "❌ Groups only.")
    if not bot_is_admin(message.chat.id): return bot.reply_to(message, "❌ I need admin rights.")
    if not is_admin(message.chat.id, message.from_user.id): return bot.reply_to(message, "❌ You need admin rights.")

    parts = message.text.split()
    if not message.reply_to_message:
        return bot.reply_to(message, "❌ Reply to a user. Usage: `/tmute 10`", parse_mode='Markdown')
    try:
        minutes = int(parts[1]) if len(parts) > 1 else 5
    except:
        return bot.reply_to(message, "❌ Invalid minutes. Usage: `/tmute 10`", parse_mode='Markdown')

    user_id = message.reply_to_message.from_user.id
    name = message.reply_to_message.from_user.first_name
    until = int(time.time()) + minutes * 60
    try:
        bot.restrict_chat_member(message.chat.id, user_id,
                                  ChatPermissions(can_send_messages=False),
                                  until_date=until)
        bot.reply_to(message, f"🔇 *{name}* muted for {minutes} minute(s).", parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, f"❌ Failed: {e}")

# --- Unmute ---
@bot.message_handler(commands=['unmute'])
def unmute_user(message):
    if not is_group(message): return bot.reply_to(message, "❌ Groups only.")
    if not bot_is_admin(message.chat.id): return bot.reply_to(message, "❌ I need admin rights.")
    if not is_admin(message.chat.id, message.from_user.id): return bot.reply_to(message, "❌ You need admin rights.")

    user_id, name = get_target_user(message)
    if not user_id: return
    try:
        bot.restrict_chat_member(message.chat.id, user_id, ChatPermissions(
            can_send_messages=True, can_send_media_messages=True,
            can_send_polls=True, can_send_other_messages=True,
            can_add_web_page_previews=True
        ))
        bot.reply_to(message, f"🔊 *{name}* has been unmuted.", parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, f"❌ Failed: {e}")

# --- Promote ---
@bot.message_handler(commands=['promote'])
def promote_user(message):
    if not is_group(message): return bot.reply_to(message, "❌ Groups only.")
    if not bot_is_admin(message.chat.id): return bot.reply_to(message, "❌ I need admin rights.")
    if not is_admin(message.chat.id, message.from_user.id): return bot.reply_to(message, "❌ You need admin rights.")

    user_id, name = get_target_user(message)
    if not user_id: return
    try:
        bot.promote_chat_member(message.chat.id, user_id,
                                can_change_info=True, can_delete_messages=True,
                                can_restrict_members=True, can_invite_users=True,
                                can_pin_messages=True, can_promote_members=False)
        bot.reply_to(message, f"⭐ *{name}* promoted to admin.", parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, f"❌ Failed: {e}")

# --- Demote ---
@bot.message_handler(commands=['demote'])
def demote_user(message):
    if not is_group(message): return bot.reply_to(message, "❌ Groups only.")
    if not bot_is_admin(message.chat.id): return bot.reply_to(message, "❌ I need admin rights.")
    if not is_admin(message.chat.id, message.from_user.id): return bot.reply_to(message, "❌ You need admin rights.")

    user_id, name = get_target_user(message)
    if not user_id: return
    try:
        bot.promote_chat_member(message.chat.id, user_id,
                                can_change_info=False, can_delete_messages=False,
                                can_restrict_members=False, can_invite_users=False,
                                can_pin_messages=False, can_promote_members=False)
        bot.reply_to(message, f"🔻 *{name}*'s admin rights removed.", parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, f"❌ Failed: {e}")

# --- Set Title ---
@bot.message_handler(commands=['settitle'])
def set_title(message):
    if not is_group(message): return bot.reply_to(message, "❌ Groups only.")
    if not bot_is_admin(message.chat.id): return bot.reply_to(message, "❌ I need admin rights.")
    if not is_admin(message.chat.id, message.from_user.id): return bot.reply_to(message, "❌ You need admin rights.")

    new_title = message.text.replace('/settitle', '').strip()
    if not new_title:
        return bot.reply_to(message, "❌ Usage: `/settitle My Group`", parse_mode='Markdown')
    try:
        bot.set_chat_title(message.chat.id, new_title)
        bot.reply_to(message, f"✅ Group title changed to: *{new_title}*", parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, f"❌ Failed: {e}")

# --- Set Description ---
@bot.message_handler(commands=['setdesc', 'setdescription'])
def set_description(message):
    if not is_group(message): return bot.reply_to(message, "❌ Groups only.")
    if not bot_is_admin(message.chat.id): return bot.reply_to(message, "❌ I need admin rights.")
    if not is_admin(message.chat.id, message.from_user.id): return bot.reply_to(message, "❌ You need admin rights.")

    new_desc = message.text.split(None, 1)[1].strip() if len(message.text.split(None, 1)) > 1 else ''
    if not new_desc:
        return bot.reply_to(message, "❌ Usage: `/setdesc Welcome to our group!`", parse_mode='Markdown')
    try:
        bot.set_chat_description(message.chat.id, new_desc)
        bot.reply_to(message, "✅ Group description updated.")
    except Exception as e:
        bot.reply_to(message, f"❌ Failed: {e}")

# --- Pin Message ---
@bot.message_handler(commands=['pin'])
def pin_message(message):
    if not is_group(message): return bot.reply_to(message, "❌ Groups only.")
    if not bot_is_admin(message.chat.id): return bot.reply_to(message, "❌ I need admin rights.")
    if not is_admin(message.chat.id, message.from_user.id): return bot.reply_to(message, "❌ You need admin rights.")
    if not message.reply_to_message:
        return bot.reply_to(message, "❌ Reply to a message to pin it.")
    try:
        bot.pin_chat_message(message.chat.id, message.reply_to_message.message_id)
        bot.reply_to(message, "📌 Message pinned.")
    except Exception as e:
        bot.reply_to(message, f"❌ Failed: {e}")

# --- Unpin Message ---
@bot.message_handler(commands=['unpin'])
def unpin_message(message):
    if not is_group(message): return bot.reply_to(message, "❌ Groups only.")
    if not bot_is_admin(message.chat.id): return bot.reply_to(message, "❌ I need admin rights.")
    if not is_admin(message.chat.id, message.from_user.id): return bot.reply_to(message, "❌ You need admin rights.")
    try:
        bot.unpin_chat_message(message.chat.id)
        bot.reply_to(message, "📌 Message unpinned.")
    except Exception as e:
        bot.reply_to(message, f"❌ Failed: {e}")

# --- Purge Messages ---
@bot.message_handler(commands=['purge'])
def purge_messages(message):
    if not is_group(message): return bot.reply_to(message, "❌ Groups only.")
    if not bot_is_admin(message.chat.id): return bot.reply_to(message, "❌ I need admin rights.")
    if not is_admin(message.chat.id, message.from_user.id): return bot.reply_to(message, "❌ You need admin rights.")
    if not message.reply_to_message:
        return bot.reply_to(message, "❌ Reply to the message you want to start purging from.")

    from_id = message.reply_to_message.message_id
    to_id = message.message_id
    deleted = 0
    for msg_id in range(from_id, to_id + 1):
        try:
            bot.delete_message(message.chat.id, msg_id)
            deleted += 1
        except:
            pass
    try:
        m = bot.send_message(message.chat.id, f"🗑 Purged {deleted} messages.")
        time.sleep(3)
        bot.delete_message(message.chat.id, m.message_id)
    except:
        pass

# --- Member Count ---
@bot.message_handler(commands=['membercount'])
def member_count(message):
    if not is_group(message): return bot.reply_to(message, "❌ Groups only.")
    try:
        count = bot.get_chat_member_count(message.chat.id)
        bot.reply_to(message, f"👥 This group has *{count}* members.", parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, f"❌ Failed: {e}")

# --- Warn System (in-memory; resets on restart) ---
warn_db = {}  # {chat_id: {user_id: count}}

@bot.message_handler(commands=['warn'])
def warn_user(message):
    if not is_group(message): return bot.reply_to(message, "❌ Groups only.")
    if not is_admin(message.chat.id, message.from_user.id): return bot.reply_to(message, "❌ You need admin rights.")

    user_id, name = get_target_user(message)
    if not user_id: return

    chat_id = message.chat.id
    warn_db.setdefault(chat_id, {})
    warn_db[chat_id][user_id] = warn_db[chat_id].get(user_id, 0) + 1
    count = warn_db[chat_id][user_id]

    if count >= 3:
        try:
            bot.ban_chat_member(chat_id, user_id)
            warn_db[chat_id][user_id] = 0
            bot.reply_to(message, f"🔨 *{name}* has been banned after 3 warnings.", parse_mode='Markdown')
        except Exception as e:
            bot.reply_to(message, f"❌ Could not ban: {e}")
    else:
        bot.reply_to(message, f"⚠️ *{name}* warned. ({count}/3 warnings)\n3 warnings = ban.", parse_mode='Markdown')

@bot.message_handler(commands=['warns'])
def check_warns(message):
    if not is_group(message): return bot.reply_to(message, "❌ Groups only.")
    user_id, name = get_target_user(message)
    if not user_id: return
    count = warn_db.get(message.chat.id, {}).get(user_id, 0)
    bot.reply_to(message, f"⚠️ *{name}* has {count}/3 warnings.", parse_mode='Markdown')

@bot.message_handler(commands=['clearwarns'])
def clear_warns(message):
    if not is_group(message): return bot.reply_to(message, "❌ Groups only.")
    if not is_admin(message.chat.id, message.from_user.id): return bot.reply_to(message, "❌ You need admin rights.")
    user_id, name = get_target_user(message)
    if not user_id: return
    warn_db.setdefault(message.chat.id, {})[user_id] = 0
    bot.reply_to(message, f"✅ Cleared warnings for *{name}*.", parse_mode='Markdown')

# ================================================================
#  FUN COMMANDS
# ================================================================

@bot.message_handler(commands=['funhelp'])
def fun_help(message):
    bot.reply_to(message, """
🎉 *Fun Commands*

/roll — Roll a dice 🎲
/flip — Flip a coin 🪙
/8ball <question> — Magic 8 ball 🎱
/rps <rock|paper|scissors> — Play RPS ✂️
/joke — Random joke 😂
/quote — Motivational quote 💬
/slap — Slap someone (reply) 👋
/hug — Hug someone (reply) 🤗
/ship — Ship two users 💘
/roast — Roast someone (reply) 🔥
/compliment — Compliment someone 🌸
/rate — Rate something out of 10 ⭐
/choose <a|b|c> — Bot picks for you 🤔
/truth — Truth question 😳
/dare — Dare challenge 😈
""", parse_mode='Markdown')

# --- Roll Dice ---
@bot.message_handler(commands=['roll'])
def roll_dice(message):
    result = random.randint(1, 6)
    faces = ["⚀","⚁","⚂","⚃","⚄","⚅"]
    bot.reply_to(message, f"🎲 You rolled: *{faces[result-1]} ({result})*", parse_mode='Markdown')

# --- Flip Coin ---
@bot.message_handler(commands=['flip'])
def flip_coin(message):
    result = random.choice(["🪙 Heads!", "🪙 Tails!"])
    bot.reply_to(message, result)

# --- Magic 8 Ball ---
EIGHT_BALL = [
  