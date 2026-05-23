# bot.py — Telegram Group Management Bot (python-telegram-bot v20)
# All handlers registered via create_application() factory for Vercel webhook use.

import asyncio
import os
import re
import random
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

from telegram import (
    Update,
    ChatPermissions,
    ChatMemberStatus,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackContext,
    filters,
)

# ── Token (set BOT_TOKEN in Vercel environment variables) ────────────────────
BOT_TOKEN: str = os.environ.get("BOT_TOKEN", "")

# ── In-memory storage (resets on cold start — acceptable for serverless) ─────
# Key: (chat_id, user_id)  Value: warning count
_warnings: Dict[Tuple[int, int], int] = {}
# Key: chat_id  Value: {note_name: note_text}
_notes: Dict[int, Dict[str, str]] = {}
# Per-chat overridable settings
_rules: Dict[int, str] = {}
_welcome: Dict[int, str] = {}
_blacklist: Dict[int, list] = {}

DEFAULT_RULES = "📜 Group Rules:\n1. Be respectful\n2. No spam\n3. Follow admin instructions"
DEFAULT_WELCOME = "👋 Welcome {mention} to {title}!"

# ── Helpers ───────────────────────────────────────────────────────────────────

async def is_admin(update: Update, user_id: int) -> bool:
    try:
        member = await update.effective_chat.get_member(user_id)
        return member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)
    except Exception:
        return False


async def check_admin(update: Update) -> bool:
    """Return True if caller is admin; otherwise send error and return False."""
    if not update.effective_user:
        return False
    if not await is_admin(update, update.effective_user.id):
        await update.effective_message.reply_text("⛔️ You need admin permissions to use this command.")
        return False
    return True


async def resolve_user(update: Update, args: list) -> Optional[int]:
    """
    Resolve a target user from:
      1. A replied-to message
      2. A numeric user ID argument
      3. A @username argument
    """
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


def fmt_user(user) -> str:
    """Plain-text user reference."""
    return f"@{user.username}" if getattr(user, "username", None) else (user.first_name or "User")


# ── Basic commands ────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: CallbackContext) -> None:
    if update.effective_chat.type == "private":
        await update.message.reply_text(
            "👋 Hi! I'm an advanced Telegram group management bot.\n"
            "Add me to a group, make me admin, then use /help."
        )


async def cmd_help(update: Update, context: CallbackContext) -> None:
    text = (
        "<b>🛠 Group Management Bot — Commands</b>\n\n"
        "<b>👮 Moderation</b>\n"
        "/ban [user] — Ban a user\n"
        "/unban [user] — Unban a user\n"
        "/kick [user] — Kick (remove without ban)\n"
        "/mute [user] [mins] — Mute a user\n"
        "/unmute [user] — Unmute a user\n"
        "/warn [user] — Warn (auto-mute at 3)\n"
        "/unwarn [user] — Remove a warning\n"
        "/warns [user] — Check warning count\n"
        "/purge — Delete messages from reply to here\n"
        "/pin — Pin replied message\n"
        "/unpin — Unpin all messages\n"
        "/promote [user] — Promote to admin\n"
        "/demote [user] — Demote admin\n"
        "/settitle [text] — Change group title\n"
        "/setphoto — Set group photo (reply to image)\n"
        "/setdescription [text] — Set group bio\n\n"
        "<b>📝 Group</b>\n"
        "/setrules [text] — Set rules\n"
        "/rules — Show rules\n"
        "/setwelcome [text] — Set welcome ({mention}, {title})\n"
        "/welcome — Preview welcome message\n"
        "/report — Report a message to admins\n"
        "/staff — List admins\n"
        "/addblacklist [word] — Add blacklist word\n"
        "/rmblacklist [word] — Remove blacklist word\n\n"
        "<b>💾 Utilities</b>\n"
        "/setnote [name] [text] — Save a note\n"
        "/getnote [name] — Get a note\n"
        "/delnote [name] — Delete a note\n"
        "/notes — List saved notes\n"
        "/id — Show user/chat ID\n"
        "/info [user] — Show user info\n"
        "/ping — Check bot latency\n\n"
        "<b>🎉 Fun</b>\n"
        "/slap — Slap a user (reply)\n"
        "/roll — Roll a dice\n"
        "/coin — Flip a coin\n"
        "/say [text] — Make bot say something\n"
    )
    await update.message.reply_text(text, parse_mode="HTML")


async def cmd_ping(update: Update, context: CallbackContext) -> None:
    t0 = datetime.now()
    msg = await update.message.reply_text("🏓 Pinging…")
    ms = (datetime.now() - t0).total_seconds() * 1000
    await msg.edit_text(f"🏓 Pong! <b>{ms:.0f} ms</b>", parse_mode="HTML")


# ── Moderation ────────────────────────────────────────────────────────────────

async def cmd_ban(update: Update, context: CallbackContext) -> None:
    if not await check_admin(update):
        return
    uid = await resolve_user(update, context.args)
    if not uid:
        await update.message.reply_text("⚠️ Reply to a user or pass their @username / ID.")
        return
    reason = " ".join(context.args[1:]) if len(context.args) > 1 else "No reason given"
    try:
        await update.effective_chat.ban_member(uid)
        user = await context.bot.get_chat(uid)
        await update.message.reply_text(f"🔨 <b>Banned</b> {fmt_user(user)}\n📝 Reason: {reason}", parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ Ban failed: {e}")


async def cmd_unban(update: Update, context: CallbackContext) -> None:
    if not await check_admin(update):
        return
    uid = await resolve_user(update, context.args)
    if not uid:
        await update.message.reply_text("⚠️ Reply to a user or pass their @username / ID.")
        return
    try:
        await update.effective_chat.unban_member(uid)
        user = await context.bot.get_chat(uid)
        await update.message.reply_text(f"✅ <b>Unbanned</b> {fmt_user(user)}", parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ Unban failed: {e}")


async def cmd_kick(update: Update, context: CallbackContext) -> None:
    if not await check_admin(update):
        return
    uid = await resolve_user(update, context.args)
    if not uid:
        await update.message.reply_text("⚠️ Reply to a user or pass their @username / ID.")
        return
    try:
        # Ban briefly then unban → user is removed but can rejoin
        await update.effective_chat.ban_member(uid, until_date=datetime.now() + timedelta(seconds=40))
        await asyncio.sleep(1)
        await update.effective_chat.unban_member(uid)
        user = await context.bot.get_chat(uid)
        await update.message.reply_text(f"👢 <b>Kicked</b> {fmt_user(user)}", parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ Kick failed: {e}")


async def cmd_mute(update: Update, context: CallbackContext) -> None:
    if not await check_admin(update):
        return
    uid = await resolve_user(update, context.args)
    if not uid:
        await update.message.reply_text("⚠️ Reply to a user or pass their @username / ID.")
        return
    # Parse duration — last numeric arg wins, default 60 min
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
        await update.message.reply_text(
            f"🔇 <b>Muted</b> {fmt_user(user)} for {duration} min", parse_mode="HTML"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Mute failed: {e}")


async def cmd_unmute(update: Update, context: CallbackContext) -> None:
    if not await check_admin(update):
        return
    uid = await resolve_user(update, context.args)
    if not uid:
        await update.message.reply_text("⚠️ Reply to a user or pass their @username / ID.")
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
        await update.message.reply_text(f"🔊 <b>Unmuted</b> {fmt_user(user)}", parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ Unmute failed: {e}")


async def cmd_warn(update: Update, context: CallbackContext) -> None:
    if not await check_admin(update):
        return
    uid = await resolve_user(update, context.args)
    if not uid:
        await update.message.reply_text("⚠️ Reply to a user or pass their @username / ID.")
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
                f"🔇 {fmt_user(user)} reached <b>3/3 warnings</b> — muted for 24 h. Warnings reset.",
                parse_mode="HTML",
            )
        except Exception as e:
            await update.message.reply_text(
                f"⚠️ Warning {count}/3 added but auto-mute failed: {e}"
            )
    else:
        await update.message.reply_text(
            f"⚠️ Warned {fmt_user(user)} — <b>{count}/3</b> warnings.", parse_mode="HTML"
        )


async def cmd_unwarn(update: Update, context: CallbackContext) -> None:
    if not await check_admin(update):
        return
    uid = await resolve_user(update, context.args)
    if not uid:
        await update.message.reply_text("⚠️ Reply to a user or pass their @username / ID.")
        return
    key = (update.effective_chat.id, uid)
    if _warnings.get(key, 0) > 0:
        _warnings[key] -= 1
        user = await context.bot.get_chat(uid)
        await update.message.reply_text(
            f"✅ Removed one warning from {fmt_user(user)} — now <b>{_warnings[key]}/3</b>.",
            parse_mode="HTML",
        )
    else:
        await update.message.reply_text("ℹ️ That user has no warnings.")


async def cmd_warns(update: Update, context: CallbackContext) -> None:
    uid = await resolve_user(update, context.args) or update.effective_user.id
    count = _warnings.get((update.effective_chat.id, uid), 0)
    user = await context.bot.get_chat(uid)
    await update.message.reply_text(
        f"⚠️ {fmt_user(user)} has <b>{count}/3</b> warnings.", parse_mode="HTML"
    )


async def cmd_purge(update: Update, context: CallbackContext) -> None:
    """Delete every message from the replied-to message up to (and including) this command."""
    if not await check_admin(update):
        return
    msg = update.effective_message
    if not msg.reply_to_message:
        await msg.reply_text("⚠️ Reply to the first message you want deleted.")
        return

    start_id = msg.reply_to_message.message_id
    end_id = msg.message_id          # delete the /purge command itself too
    chat_id = update.effective_chat.id
    ids = list(range(start_id, end_id + 1))

    deleted = 0
    skipped = 0
    # Telegram allows up to 100 IDs per delete_messages call
    for i in range(0, len(ids), 100):
        chunk = ids[i : i + 100]
        try:
            await context.bot.delete_messages(chat_id=chat_id, message_ids=chunk)
            deleted += len(chunk)
        except Exception:
            # Fall back to one-by-one for chunks that contain missing IDs
            for mid in chunk:
                try:
                    await context.bot.delete_message(chat_id=chat_id, message_id=mid)
                    deleted += 1
                except Exception:
                    skipped += 1

    note = await update.effective_chat.send_message(
        f"🧹 Purged <b>{deleted}</b> messages." + (f" ({skipped} not found)" if skipped else ""),
        parse_mode="HTML",
    )
    await asyncio.sleep(5)
    try:
        await note.delete()
    except Exception:
        pass


async def cmd_pin(update: Update, context: CallbackContext) -> None:
    if not await check_admin(update):
        return
    if not update.effective_message.reply_to_message:
        await update.message.reply_text("⚠️ Reply to the message you want pinned.")
        return
    try:
        await update.effective_message.reply_to_message.pin(disable_notification=True)
        await update.message.reply_text("📌 Message pinned.")
    except Exception as e:
        await update.message.reply_text(f"❌ Pin failed: {e}")


async def cmd_unpin(update: Update, context: CallbackContext) -> None:
    if not await check_admin(update):
        return
    try:
        await update.effective_chat.unpin_all_messages()
        await update.message.reply_text("📌 All messages unpinned.")
    except Exception as e:
        await update.message.reply_text(f"❌ Unpin failed: {e}")


async def cmd_promote(update: Update, context: CallbackContext) -> None:
    if not await check_admin(update):
        return
    uid = await resolve_user(update, context.args)
    if not uid:
        await update.message.reply_text("⚠️ Reply to a user or pass their @username / ID.")
        return
    try:
        await update.effective_chat.promote_member(
            uid,
            can_manage_chat=True,
            can_delete_messages=True,
            can_manage_video_chats=True,
            can_restrict_members=True,
            can_change_info=True,
            can_post_messages=True,
            can_edit_messages=True,
            can_invite_users=True,
            can_pin_messages=True,
            can_manage_topics=True,
        )
        user = await context.bot.get_chat(uid)
        await update.message.reply_text(f"👑 <b>Promoted</b> {fmt_user(user)} to admin!", parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ Promote failed: {e}")


async def cmd_demote(update: Update, context: CallbackContext) -> None:
    if not await check_admin(update):
        return
    uid = await resolve_user(update, context.args)
    if not uid:
        await update.message.reply_text("⚠️ Reply to a user or pass their @username / ID.")
        return
    try:
        await update.effective_chat.promote_member(
            uid,
            can_manage_chat=False,
            can_delete_messages=False,
            can_manage_video_chats=False,
            can_restrict_members=False,
            can_change_info=False,
            can_post_messages=False,
            can_edit_messages=False,
            can_invite_users=False,
            can_pin_messages=False,
            can_manage_topics=False,
        )
        user = await context.bot.get_chat(uid)
        await update.message.reply_text(f"👤 <b>Demoted</b> {fmt_user(user)} from admin.", parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ Demote failed: {e}")


async def cmd_settitle(update: Update, context: CallbackContext) -> None:
    if not await check_admin(update):
        return
    if not context.args:
        await update.message.reply_text("⚠️ Usage: /settitle <new title>")
        return
    try:
        await update.effective_chat.set_title(" ".join(context.args))
        await update.message.reply_text("✅ Group title updated!")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed: {e}")


async def cmd_setphoto(update: Update, context: CallbackContext) -> None:
    if not await check_admin(update):
        return
    reply = update.effective_message.reply_to_message
    if not reply or not reply.photo:
        await update.message.reply_text("⚠️ Reply to a photo to set it as the group picture.")
        return
    try:
        f = await reply.photo[-1].get_file()
        await update.effective_chat.set_photo(f)
        await update.message.reply_text("✅ Group photo updated!")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed: {e}")


async def cmd_setdescription(update: Update, context: CallbackContext) -> None:
    if not await check_admin(update):
        return
    if not context.args:
        await update.message.reply_text("⚠️ Usage: /setdescription <text>")
        return
    try:
        await update.effective_chat.set_description(" ".join(context.args))
        await update.message.reply_text("✅ Group description updated!")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed: {e}")


# ── Group settings ────────────────────────────────────────────────────────────

async def cmd_setrules(update: Update, context: CallbackContext) -> None:
    if not await check_admin(update):
        return
    if not context.args:
        await update.message.reply_text("⚠️ Usage: /setrules <text>")
        return
    _rules[update.effective_chat.id] = " ".join(context.args)
    await update.message.reply_text("✅ Rules saved!")


async def cmd_rules(update: Update, context: CallbackContext) -> None:
    text = _rules.get(update.effective_chat.id, DEFAULT_RULES)
    await update.message.reply_text(text)


async def cmd_setwelcome(update: Update, context: CallbackContext) -> None:
    if not await check_admin(update):
        return
    if not context.args:
        await update.message.reply_text(
            "⚠️ Usage: /setwelcome <text>\nPlaceholders: {mention}, {title}, {first_name}"
        )
        return
    _welcome[update.effective_chat.id] = " ".join(context.args)
    await update.message.reply_text("✅ Welcome message saved!")


async def cmd_welcome(update: Update, context: CallbackContext) -> None:
    tpl = _welcome.get(update.effective_chat.id, DEFAULT_WELCOME)
    preview = (
        tpl.replace("{mention}", update.effective_user.mention_html())
           .replace("{first_name}", update.effective_user.first_name or "User")
           .replace("{title}", update.effective_chat.title or "this group")
    )
    await update.message.reply_text(f"<b>Preview:</b>\n{preview}", parse_mode="HTML")


async def on_new_member(update: Update, context: CallbackContext) -> None:
    if not update.message or not update.message.new_chat_members:
        return
    tpl = _welcome.get(update.effective_chat.id, DEFAULT_WELCOME)
    for user in update.message.new_chat_members:
        if user.is_bot:
            continue
        text = (
            tpl.replace("{mention}", user.mention_html())
               .replace("{first_name}", user.first_name or "User")
               .replace("{title}", update.effective_chat.title or "this group")
        )
        await update.message.reply_text(text, parse_mode="HTML")


async def cmd_report(update: Update, context: CallbackContext) -> None:
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ Reply to the message you want to report.")
