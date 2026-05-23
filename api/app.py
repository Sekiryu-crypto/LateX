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

# ------------------- GROUP MANAGEMENT COMMANDS (ADDED) ------------------- #

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

@bot.message_handler(commands=['grouphelp'])
def group_help(message):
    if not is_group(message):
        bot.reply_to(message, "This command works only in groups.")
        return
    bot.reply_to(message, """
👥 **Group Management Commands** (Bot must be admin)
/kick (reply or @username) - Remove user
/ban (reply or @username) - Ban user
/unban (reply or @username) - Unban user
/mute (reply or @username) - Restrict sending messages
/unmute (reply or @username) - Remove restriction
/promote (reply or @username) - Make admin
/demote (reply or @username) - Remove admin rights
/settitle <new name> - Change group title
/setdescription <text> - Change group description
/grouphelp - Show this list
""", parse_mode='Markdown')

@bot.message_handler(commands=['kick'])
def kick_user(message):
    if not is_group(message):
        bot.reply_to(message, "This command works only in groups.")
        return
    if not bot_is_admin(message.chat.id):
        bot.reply_to(message, "I need to be admin to kick members.")
        return
    if not is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "You need admin rights to kick members.")
        return

    user_id = None
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
    elif len(message.text.split()) > 1:
        username = message.text.split()[1]
        try:
            user_id = bot.get_chat_member(message.chat.id, username).user.id
        except:
            bot.reply_to(message, "User not found.")
            return
    else:
        bot.reply_to(message, "Reply to a user or provide @username.")
        return

    try:
        bot.ban_chat_member(message.chat.id, user_id)
        bot.unban_chat_member(message.chat.id, user_id)  # kick = ban + unban
        bot.reply_to(message, f"✅ User kicked.")
    except Exception as e:
        bot.reply_to(message, f"Failed: {str(e)}")

@bot.message_handler(commands=['ban'])
def ban_user(message):
    if not is_group(message):
        bot.reply_to(message, "This command works only in groups.")
        return
    if not bot_is_admin(message.chat.id):
        bot.reply_to(message, "I need to be admin to ban members.")
        return
    if not is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "You need admin rights to ban members.")
        return

    user_id = None
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
    elif len(message.text.split()) > 1:
        username = message.text.split()[1]
        try:
            user_id = bot.get_chat_member(message.chat.id, username).user.id
        except:
            bot.reply_to(message, "User not found.")
            return
    else:
        bot.reply_to(message, "Reply to a user or provide @username.")
        return

    try:
        bot.ban_chat_member(message.chat.id, user_id)
        bot.reply_to(message, f"✅ User banned.")
    except Exception as e:
        bot.reply_to(message, f"Failed: {str(e)}")

@bot.message_handler(commands=['unban'])
def unban_user(message):
    if not is_group(message):
        bot.reply_to(message, "This command works only in groups.")
        return
    if not bot_is_admin(message.chat.id):
        bot.reply_to(message, "I need to be admin to unban members.")
        return
    if not is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "You need admin rights to unban members.")
        return

    if len(message.text.split()) < 2:
        bot.reply_to(message, "Provide @username or user_id to unban.")
        return
    target = message.text.split()[1]
    try:
        if target.startswith('@'):
            bot.reply_to(message, "Please provide the user_id (numeric) for unban. Banned users cannot be fetched by username.")
            return
        else:
            user_id = int(target)
            bot.unban_chat_member(message.chat.id, user_id)
            bot.reply_to(message, f"✅ User unbanned.")
    except Exception as e:
        bot.reply_to(message, f"Failed: {str(e)}")

@bot.message_handler(commands=['mute'])
def mute_user(message):
    if not is_group(message):
        bot.reply_to(message, "This command works only in groups.")
        return
    if not bot_is_admin(message.chat.id):
        bot.reply_to(message, "I need to be admin to mute members.")
        return
    if not is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "You need admin rights to mute members.")
        return

    user_id = None
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
    elif len(message.text.split()) > 1:
        username = message.text.split()[1]
        try:
            user_id = bot.get_chat_member(message.chat.id, username).user.id
        except:
            bot.reply_to(message, "User not found.")
            return
    else:
        bot.reply_to(message, "Reply to a user or provide @username.")
        return

    try:
        bot.restrict_chat_member(message.chat.id, user_id, can_send_messages=False)
        bot.reply_to(message, f"🔇 User muted (cannot send messages).")
    except Exception as e:
        bot.reply_to(message, f"Failed: {str(e)}")

@bot.message_handler(commands=['unmute'])
def unmute_user(message):
    if not is_group(message):
        bot.reply_to(message, "This command works only in groups.")
        return
    if not bot_is_admin(message.chat.id):
        bot.reply_to(message, "I need to be admin to unmute members.")
        return
    if not is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "You need admin rights to unmute members.")
        return

    user_id = None
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
    elif len(message.text.split()) > 1:
        username = message.text.split()[1]
        try:
            user_id = bot.get_chat_member(message.chat.id, username).user.id
        except:
            bot.reply_to(message, "User not found.")
            return
    else:
        bot.reply_to(message, "Reply to a user or provide @username.")
        return

    try:
        bot.restrict_chat_member(message.chat.id, user_id, can_send_messages=True)
        bot.reply_to(message, f"🔊 User unmuted.")
    except Exception as e:
        bot.reply_to(message, f"Failed: {str(e)}")

@bot.message_handler(commands=['promote'])
def promote_user(message):
    if not is_group(message):
        bot.reply_to(message, "This command works only in groups.")
        return
    if not bot_is_admin(message.chat.id):
        bot.reply_to(message, "I need to be admin to promote members.")
        return
    if not is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "You need admin rights to promote members.")
        return

    user_id = None
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
    elif len(message.text.split()) > 1:
        username = message.text.split()[1]
        try:
            user_id = bot.get_chat_member(message.chat.id, username).user.id
        except:
            bot.reply_to(message, "User not found.")
            return
    else:
        bot.reply_to(message, "Reply to a user or provide @username.")
        return

    try:
        bot.promote_chat_member(message.chat.id, user_id,
                                can_change_info=True,
                                can_delete_messages=True,
                                can_restrict_members=True,
                                can_invite_users=True,
                                can_pin_messages=True,
                                can_promote_members=False)
        bot.reply_to(message, f"✅ User promoted to admin (without promote rights).")
    except Exception as e:
        bot.reply_to(message, f"Failed: {str(e)}")

@bot.message_handler(commands=['demote'])
def demote_user(message):
    if not is_group(message):
        bot.reply_to(message, "This command works only in groups.")
        return
    if not bot_is_admin(message.chat.id):
        bot.reply_to(message, "I need to be admin to demote members.")
        return
    if not is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "You need admin rights to demote members.")
        return

    user_id = None
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
    elif len(message.text.split()) > 1:
        username = message.text.split()[1]
        try:
            user_id = bot.get_chat_member(message.chat.id, username).user.id
        except:
            bot.reply_to(message, "User not found.")
            return
    else:
        bot.reply_to(message, "Reply to a user or provide @username.")
        return

    try:
        bot.promote_chat_member(message.chat.id, user_id,
                                can_change_info=False,
                                can_delete_messages=False,
                                can_restrict_members=False,
                                can_invite_users=False,
                                can_pin_messages=False,
                                can_promote_members=False)
        bot.reply_to(message, f"✅ Admin rights removed.")
    except Exception as e:
        bot.reply_to(message, f"Failed: {str(e)}")

@bot.message_handler(commands=['settitle'])
def set_title(message):
    if not is_group(message):
        bot.reply_to(message, "This command works only in groups.")
        return
    if not bot_is_admin(message.chat.id):
        bot.reply_to(message, "I need to be admin to change group title.")
        return
    if not is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "You need admin rights to change group title.")
        return

    new_title = message.text.replace('/settitle', '').strip()
    if not new_title:
        bot.reply_to(message, "Please provide a new title. Example: `/settitle My Awesome Group`", parse_mode='Markdown')
        return

    try:
        bot.set_chat_title(message.chat.id, new_title)
        bot.reply_to(message, f"✅ Group title changed to: {new_title}")
    except Exception as e:
        bot.reply_to(message, f"Failed: {str(e)}")

@bot.message_handler(commands=['setdescription'])
def set_description(message):
    if not is_group(message):
        bot.reply_to(message, "This command works only in groups.")
        return
    if not bot_is_admin(message.chat.id):
        bot.reply_to(message, "I need to be admin to change group description.")
        return
    if not is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "You need admin rights to change group description.")
        return

    new_desc = message.text.replace('/setdescription', '').strip()
    if not new_desc:
        bot.reply_to(message, "Please provide a description. Example: `/setdescription Welcome to our group!`", parse_mode='Markdown')
        return

    try:
        bot.set_chat_description(message.chat.id, new_desc)
        bot.reply_to(message, f"✅ Group description updated.")
    except Exception as e:
        bot.reply_to(message, f"Failed: {str(e)}")