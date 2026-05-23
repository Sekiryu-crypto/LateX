# api/webhook.py
# Self-contained Vercel serverless handler for Telegram bot.
# All bot logic is in this single file so imports never fail.

from http.server import BaseHTTPRequestHandler
import asyncio
import json
import os
import re
import random
import sys
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

# ── Token from Vercel environment variable ────────────────────────────────────
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

# ── In-memory storage (resets on cold start) ─────────────────────────────────
_warnings: Dict[Tuple[int, int], int] = {}
_notes: Dict[int, Dict[str, str]] = {}
_rules: Dict[int, str] = {}
_welcome: Dict[int, str] = {}
_blacklist: Dict[int, list] = {}

DEFAULT_RULES = "📜 Group Rules:\n1. Be respectful\n2. No spam\n3. Follow admin instructions"
DEFAULT_WELCOME = "👋 Welcome {mention} to {title}!"

# ── Lazy imports (so crash shows clear error if package missing) ──────────────
try:
    from telegram import Update, ChatPermissions, ChatMemberStatus
    from telegram.ext import Application, CommandHandler, MessageHandler, CallbackContext, filters
    IMPORTS_OK = True
    IMPORT_ERROR = ""
except Exception as e:
    IMPORTS_OK = False
    IMPORT_ERROR = str(e)

# ── App singleton ─────────────────────────────────────────────────────────────
_app = None

def get_app():
    global _app
    if _app is None:
        _app = build_app()
    return _app

# ── Helpers ───────────────────────────────────────────────────────────────────

async def is_admin(update, user_id: int) -> bool:
    try:
        member = await update.effective_chat.get_member(user_id)
        return member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)
    except Exception:
        return False

async def check_admin(update) -> bool:
    if not update.effective_user:
        return False
    if not await is_admin(update, update.effective_user.id):
        await update.effective_message.reply_text("⛔️ You need admin permissions.")
        return False
    return True

async def resolve_user(update, args: list) -> Optional[int]:
    msg = update.effective_message
    if msg.reply_to_message and msg.reply_to_message.from_user:
        return msg.reply_to_message.from_user.id
    if args:
        ref = args[0]
        if ref.lstrip("-").isdigit():
            return int(ref)
        if ref.startswith("@"):
            try:
                cm = await update.effective_chat.get_member(ref[1:])
                return cm.user.id
            except Exception:
                pass
    return None

def fmt(user) -> str:
    return f"@{user.username}" if getattr(user, "username", None) else (user.first_name or "User")

# ── Commands ──────────────────────────────────────────────────────────────────

async def cmd_start(update, context):
    if update.effective_chat.type == "private":
        await update.message.reply_text(
            "👋 Hi! I'm a group management bot.\n"
            "Add me to a group, make me admin, then use /help."
        )

async def cmd_help(update, context):
    await update.message.reply_text(
        "<b>🛠 Commands</b>\n\n"
        "<b>Moderation:</b>\n"
        "/ban /unban /kick /mute /unmute\n"
        "/warn /unwarn /warns\n"
        "/purge /pin /unpin\n"
        "/promote /demote\n"
        "/settitle /setphoto /setdescription\n\n"
        "<b>Group:</b>\n"
        "/setrules /rules\n"
        "/setwelcome /welcome\n"
        "/report /staff\n"
        "/addblacklist /rmblacklist\n\n"
        "<b>Utilities:</b>\n"
        "/setnote /getnote /delnote /notes\n"
        "/id /info /ping\n\n"
        "<b>Fun:</b>\n"
        "/slap /roll /coin /say",
        parse_mode="HTML"
    )

async def cmd_ping(update, context):
    t0 = datetime.now()
    msg = await update.message.reply_text("🏓 Pinging…")
    ms = (datetime.now() - t0).total_seconds() * 1000
    await msg.edit_text(f"🏓 Pong! <b>{ms:.0f} ms</b>", parse_mode="HTML")

async def cmd_ban(update, context):
    if not await check_admin(update): return
    uid = await resolve_user(update, context.args)
    if not uid:
        await update.message.reply_text("⚠️ Reply to a user or pass @username / ID.")
        return
    try:
        await update.effective_chat.ban_member(uid)
        user = await context.bot.get_chat(uid)
        await update.message.reply_text(f"🔨 Banned {fmt(user)}")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed: {e}")

async def cmd_unban(update, context):
    if not await check_admin(update): return
    uid = await resolve_user(update, context.args)
    if not uid:
        await update.message.reply_text("⚠️ Reply to a user or pass @username / ID.")
        return
    try:
        await update.effective_chat.unban_member(uid)
        user = await context.bot.get_chat(uid)
        await update.message.reply_text(f"✅ Unbanned {fmt(user)}")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed: {e}")

async def cmd_kick(update, context):
    if not await check_admin(update): return
    uid = await resolve_user(update, context.args)
    if not uid:
        await update.message.reply_text("⚠️ Reply to a user or pass @username / ID.")
        return
    try:
        await update.effective_chat.ban_member(uid, until_date=datetime.now() + timedelta(seconds=40))
        await asyncio.sleep(1)
        await update.effective_chat.unban_member(uid)
        user = await context.bot.get_chat(uid)
        await update.message.reply_text(f"👢 Kicked {fmt(user)}")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed: {e}")

async def cmd_mute(update, context):
    if not await check_admin(update): return
    uid = await resolve_user(update, context.args)
    if not uid:
        await update.message.reply_text("⚠️ Reply to a user or pass @username / ID.")
        return
    duration = 60
    for arg in reversed(context.args):
        if arg.isdigit():
            duration = int(arg)
            break
    try:
        await update.effective_chat.restrict_member(
            uid,
            ChatPermissions(can_send_messages=False),
            until_date=datetime.now() + timedelta(minutes=duration),
        )
        user = await context.bot.get_chat(uid)
        await update.message.reply_text(f"🔇 Muted {fmt(user)} for {duration} min")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed: {e}")

async def cmd_unmute(update, context):
    if not await check_admin(update): return
    uid = await resolve_user(update, context.args)
    if not uid:
        await update.message.reply_text("⚠️ Reply to a user or pass @username / ID.")
        return
    try:
        await update.effective_chat.restrict_member(
            uid,
            ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
            ),
        )
        user = await context.bot.get_chat(uid)
        await update.message.reply_text(f"🔊 Unmuted {fmt(user)}")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed: {e}")

async def cmd_warn(update, context):
    if not await check_admin(update): return
    uid = await resolve_user(update, context.args)
    if not uid:
        await update.message.reply_text("⚠️ Reply to a user or pass @username / ID.")
        return
    cid = update.effective_chat.id
    key = (cid, uid)
    _warnings[key] = _warnings.get(key, 0) + 1
    count = _warnings[key]
    user = await context.bot.get_chat(uid)
    if count >= 3:
        try:
            await update.effective_chat.restrict_member(
                uid,
                ChatPermissions(can_send_messages=False),
                until_date=datetime.now() + timedelta(hours=24),
            )
            _warnings[key] = 0
            await update.message.reply_text(
                f"🔇 {fmt(user)} hit 3/3 warnings — muted 24h. Warnings reset."
            )
        except Exception as e:
            await update.message.reply_text(f"⚠️ Warned {count}/3 but mute failed: {e}")
    else:
        await update.message.reply_text(f"⚠️ Warned {fmt(user)} — {count}/3 warnings.")

async def cmd_unwarn(update, context):
    if not await check_admin(update): return
    uid = await resolve_user(update, context.args)
    if not uid:
        await update.message.reply_text("⚠️ Reply to a user or pass @username / ID.")
        return
    key = (update.effective_chat.id, uid)
    if _warnings.get(key, 0) > 0:
        _warnings[key] -= 1
        user = await context.bot.get_chat(uid)
        await update.message.reply_text(f"✅ Removed warning from {fmt(user)} — now {_warnings[key]}/3.")
    else:
        await update.message.reply_text("ℹ️ User has no warnings.")

async def cmd_warns(update, context):
    uid = await resolve_user(update, context.args) or update.effective_user.id
    count = _warnings.get((update.effective_chat.id, uid), 0)
    user = await context.bot.get_chat(uid)
    await update.message.reply_text(f"⚠️ {fmt(user)} has {count}/3 warnings.")

async def cmd_purge(update, context):
    if not await check_admin(update): return
    msg = update.effective_message
    if not msg.reply_to_message:
        await msg.reply_text("⚠️ Reply to the first message you want deleted.")
        return
    start_id = msg.reply_to_message.message_id
    end_id = msg.message_id
    chat_id = update.effective_chat.id
    ids = list(range(start_id, end_id + 1))
    deleted = 0
    skipped = 0
    for i in range(0, len(ids), 100):
        chunk = ids[i:i + 100]
        try:
            await context.bot.delete_messages(chat_id=chat_id, message_ids=chunk)
            deleted += len(chunk)
        except Exception:
            for mid in chunk:
                try:
                    await context.bot.delete_message(chat_id=chat_id, message_id=mid)
                    deleted += 1
                except Exception:
                    skipped += 1
    note = await update.effective_chat.send_message(
        f"🧹 Purged {deleted} messages." + (f" ({skipped} skipped)" if skipped else "")
    )
    await asyncio.sleep(5)
    try:
        await note.delete()
    except Exception:
        pass

async def cmd_pin(update, context):
    if not await check_admin(update): return
    if not update.effective_message.reply_to_message:
        await update.message.reply_text("⚠️ Reply to the message you want pinned.")
        return
    try:
        await update.effective_message.reply_to_message.pin(disable_notification=True)
        await update.message.reply_text("📌 Pinned.")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed: {e}")

async def cmd_unpin(update, context):
    if not await check_admin(update): return
    try:
        await update.effective_chat.unpin_all_messages()
        await update.message.reply_text("📌 All messages unpinned.")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed: {e}")

async def cmd_promote(update, context):
    if not await check_admin(update): return
    uid = await resolve_user(update, context.args)
    if not uid:
        await update.message.reply_text("⚠️ Reply to a user or pass @username / ID.")
        return
    try:
        await update.effective_chat.promote_member(
            uid, can_manage_chat=True, can_delete_messages=True,
            can_manage_video_chats=True, can_restrict_members=True,
            can_change_info=True, can_invite_users=True, can_pin_messages=True,
        )
        user = await context.bot.get_chat(uid)
        await update.message.reply_text(f"👑 Promoted {fmt(user)} to admin!")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed: {e}")

async def cmd_demote(update, context):
    if not await check_admin(update): return
    uid = await resolve_user(update, context.args)
    if not uid:
        await update.message.reply_text("⚠️ Reply to a user or pass @username / ID.")
        return
    try:
        await update.effective_chat.promote_member(
            uid, can_manage_chat=False, can_delete_messages=False,
            can_manage_video_chats=False, can_restrict_members=False,
            can_change_info=False, can_invite_users=False, can_pin_messages=False,
        )
        user = await context.bot.get_chat(uid)
        await update.message.reply_text(f"👤 Demoted {fmt(user)}.")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed: {e}")

async def cmd_settitle(update, context):
    if not await check_admin(update): return
    if not context.args:
        await update.message.reply_text("⚠️ Usage: /settitle <text>")
        return
    try:
        await update.effective_chat.set_title(" ".join(context.args))
        await update.message.reply_text("✅ Title updated!")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed: {e}")

async def cmd_setphoto(update, context):
    if not await check_admin(update): return
    reply = update.effective_message.reply_to_message
    if not reply or not reply.photo:
        await update.message.reply_text("⚠️ Reply to a photo.")
        return
    try:
        f = await reply.photo[-1].get_file()
        await update.effective_chat.set_photo(f)
        await update.message.reply_text("✅ Photo updated!")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed: {e}")

async def cmd_setdescription(update, context):
    if not await check_admin(update): return
    if not context.args:
        await update.message.reply_text("⚠️ Usage: /setdescription <text>")
        return
    try:
        await update.effective_chat.set_description(" ".join(context.args))
        await update.message.reply_text("✅ Description updated!")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed: {e}")

async def cmd_setrules(update, context):
    if not await check_admin(update): return
    if not context.args:
        await update.message.reply_text("⚠️ Usage: /setrules <text>")
        return
    _rules[update.effective_chat.id] = " ".join(context.args)
    await update.message.reply_text("✅ Rules saved!")

async def cmd_rules(update, context):
    await update.message.reply_text(_rules.get(update.effective_chat.id, DEFAULT_RULES))

async def cmd_setwelcome(update, context):
    if not await check_admin(update): return
    if not context.args:
        await update.message.reply_text("⚠️ Usage: /setwelcome <text>\nUse {mention} {title} {first_name}")
        return
    _welcome[update.effective_chat.id] = " ".join(context.args)
    await update.message.reply_text("✅ Welcome message saved!")

async def cmd_welcome(update, context):
    tpl = _welcome.get(update.effective_chat.id, DEFAULT_WELCOME)
    preview = tpl.replace("{mention}", update.effective_user.mention_html()) \
                 .replace("{first_name}", update.effective_user.first_name or "User") \
                 .replace("{title}", update.effective_chat.title or "this group")
    await update.message.reply_text(f"<b>Preview:</b>\n{preview}", parse_mode="HTML")

async def on_new_member(update, context):
    if not update.message or not update.message.new_chat_members:
        return
    tpl = _welcome.get(update.effective_chat.id, DEFAULT_WELCOME)
    for user in update.message.new_chat_members:
        if user.is_bot:
            continue
        text = tpl.replace("{mention}", user.mention_html()) \
                  .replace("{first_name}", user.first_name or "User") \
                  .replace("{title}", update.effective_chat.title or "this group")
        await update.message.reply_text(text, parse_mode="HTML")

async def cmd_report(update, context):
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ Reply to the message you want to report.")
        return
    try:
        admins = await update.effective_chat.get_administrators()
        mentions = [m.user.mention_html() for m in admins if not m.user.is_bot]
    except Exception as e:
        await update.message.reply_text(f"❌ Could not fetch admins: {e}")
        return
    link = update.message.reply_to_message.link or "(no link)"
    await update.message.reply_text(
        f"🚨 <b>Report</b>\n"
        f"👤 By: {update.effective_user.mention_html()}\n"
        f"🔗 Message: {link}\n\n"
        f"🛡 Admins:\n" + ("\n".join(mentions) or "None"),
        parse_mode="HTML"
    )

async def cmd_staff(update, context):
    try:
        admins = await update.effective_chat.get_administrators()
        lines = [m.user.mention_html() for m in admins if not m.user.is_bot]
    except Exception as e:
        await update.message.reply_text(f"❌ Failed: {e}")
        return
    await update.message.reply_text(
        "👮 <b>Admins:</b>\n" + ("\n".join(lines) or "None"),
        parse_mode="HTML"
    )

async def cmd_addblacklist(update, context):
    if not await check_admin(update): return
    if not context.args:
        await update.message.reply_text("⚠️ Usage: /addblacklist <word>")
        return
    cid = update.effective_chat.id
    word = context.args[0].lower()
    _blacklist.setdefault(cid, [])
    if word not in _blacklist[cid]:
        _blacklist[cid].append(word)
        await update.message.reply_text(f"✅ Added <code>{word}</code> to blacklist.", parse_mode="HTML")
    else:
        await update.message.reply_text("ℹ️ Already blacklisted.")

async def cmd_rmblacklist(update, context):
    if not await check_admin(update): return
    if not context.args:
        await update.message.reply_text("⚠️ Usage: /rmblacklist <word>")
        return
    cid = update.effective_chat.id
    word = context.args[0].lower()
    if word in _blacklist.get(cid, []):
        _blacklist[cid].remove(word)
        await update.message.reply_text(f"✅ Removed <code>{word}</code>.", parse_mode="HTML")
    else:
        await update.message.reply_text("ℹ️ Not in blacklist.")

async def cmd_setnote(update, context):
    if not await check_admin(update): return
    if len(context.args) < 2:
        await update.message.reply_text("⚠️ Usage: /setnote <name> <text>")
        return
    cid = update.effective_chat.id
    _notes.setdefault(cid, {})[context.args[0]] = " ".join(context.args[1:])
    await update.message.reply_text(f"📝 Note <code>{context.args[0]}</code> saved.", parse_mode="HTML")

async def cmd_getnote(update, context):
    if not context.args:
        await update.message.reply_text("⚠️ Usage: /getnote <name>")
        return
    text = _notes.get(update.effective_chat.id, {}).get(context.args[0])
    if text:
        await update.message.reply_text(text)
    else:
        await update.message.reply_text(f"⚠️ Note <code>{context.args[0]}</code> not found.", parse_mode="HTML")

async def cmd_delnote(update, context):
    if not await check_admin(update): return
    if not context.args:
        await update.message.reply_text("⚠️ Usage: /delnote <name>")
        return
    cid = update.effective_chat.id
    if _notes.get(cid, {}).pop(context.args[0], None) is not None:
        await update.message.reply_text(f"🗑 Deleted note <code>{context.args[0]}</code>.", parse_mode="HTML")
    else:
        await update.message.reply_text("⚠️ Note not found.")

async def cmd_notes(update, context):
    ns = list(_notes.get(update.effective_chat.id, {}).keys())
    if ns:
        await update.message.reply_text(
            "📋 <b>Notes:</b>\n" + "\n".join(f"• <code>{n}</code>" for n in ns),
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text("ℹ️ No notes saved.")

async def cmd_id(update, context):
    if update.effective_chat.type == "private":
        await update.message.reply_text(f"🆔 Your ID: <code>{update.effective_user.id}</code>", parse_mode="HTML")
    elif update.message.reply_to_message and update.message.reply_to_message.from_user:
        u = update.message.reply_