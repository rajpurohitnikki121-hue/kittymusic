# ==========================================================
# Copyright (c) 2026 ArtistBots
# All Rights Reserved.
#
# Project      : ArtistBots API Telegram Music Bot
# Powered By   : Artist
# Type         : API Based Telegram Music Bot
#
# Bot          : @ArtistApibot
# Channel      : https://t.me/artistbots
# GitHub       : https://github.com/elevenyts
#
# Unauthorized copying, modification, or redistribution
# of this source code without permission is prohibited.
# ==========================================================
import html
import logging
from datetime import datetime

from pyrogram import Client, filters
from pyrogram.enums import ChatType, ChatMemberStatus, ChatMembersFilter
from pyrogram.types import Message

from Elevenyts import app

logger = logging.getLogger(__name__)


def _age_text(created: datetime) -> str:
    """'12 Mar 2024  (1y 7m 13d ago)' from the group's first message date."""
    now = datetime.now(created.tzinfo) if created.tzinfo else datetime.now()
    years = now.year - created.year
    months = now.month - created.month
    days = now.day - created.day
    if days < 0:
        months -= 1
        days += 30
    if months < 0:
        years -= 1
        months += 12
    if years < 0:
        years, months, days = 0, 0, 0
    parts = []
    if years:
        parts.append(f"{years}y")
    if months:
        parts.append(f"{months}m")
    parts.append(f"{days}d")
    return f"{created.strftime('%d %b %Y')}  (~{' '.join(parts)} ago)"


async def _group_created(client: Client, chat_id: int):
    """Telegram does not give a group's creation date to bots. The best
    estimate is the date of the oldest message that still exists (the
    'group created' message is usually id 1)."""
    try:
        msgs = await client.get_messages(chat_id, list(range(1, 21)))
        if not isinstance(msgs, list):
            msgs = [msgs]
        dates = [
            m.date for m in msgs
            if m and not getattr(m, "empty", False) and getattr(m, "date", None)
        ]
        return min(dates) if dates else None
    except Exception as e:
        logger.debug(f"groupdata: could not read first messages of {chat_id}: {e}")
        return None


@app.on_message(filters.command(["groupdata", "chatinfo", "groupinfo"]) & filters.group)
async def group_data_handler(client: Client, message: Message):
    """Display comprehensive information about the current group"""
    chat = message.chat
    chat_id = chat.id
    user_id = message.from_user.id if message.from_user else None

    # Auto-delete command message
    try:
        await message.delete()
    except Exception:
        pass

    try:
        # Get chat information
        chat_info = await client.get_chat(chat_id)

        # Count members by type
        total_members = 0
        admin_count = 0
        bot_count = 0
        banned_count = 0
        deleted_count = 0
        premium_count = 0

        try:
            total_members = await client.get_chat_members_count(chat_id)
        except Exception:
            pass

        try:
            async for _ in client.get_chat_members(chat_id, filter=ChatMembersFilter.ADMINISTRATORS):
                admin_count += 1
        except Exception:
            pass

        try:
            async for _ in client.get_chat_members(chat_id, filter=ChatMembersFilter.BOTS):
                bot_count += 1
        except Exception:
            pass

        try:
            async for _ in client.get_chat_members(chat_id, filter=ChatMembersFilter.BANNED):
                banned_count += 1
        except Exception:
            pass

        # Sample of members to count deleted accounts and premium users
        try:
            async for member in client.get_chat_members(chat_id, filter=ChatMembersFilter.SEARCH, limit=200):
                if member.user.is_deleted:
                    deleted_count += 1
                if getattr(member.user, "is_premium", False):
                    premium_count += 1
        except Exception:
            pass

        created = await _group_created(client, chat_id)

        # Build information text
        info_lines = []
        info_lines.append("<b>📊 GROUP INFORMATION</b>\n")

        # Basic info
        info_lines.append(f"<b>📌 ɴᴀᴍᴇ:</b> {html.escape(chat_info.title or '')}")
        info_lines.append(f"<b>🆔 ɪᴅ:</b> <code>{chat_id}</code>")

        if chat_info.username:
            info_lines.append(f"<b>🔗 ᴜꜱᴇʀɴᴀᴍᴇ:</b> @{chat_info.username}")

        # Chat type
        chat_type_str = "ɢʀᴏᴜᴘ" if chat.type == ChatType.GROUP else "ꜱᴜᴘᴇʀɢʀᴏᴜᴘ"
        info_lines.append(f"<b>📂 ᴛʏᴘᴇ:</b> {chat_type_str}")

        # Group age (estimated from the oldest message)
        if created:
            info_lines.append(f"<b>📅 ᴄʀᴇᴀᴛᴇᴅ:</b> {_age_text(created)}")

        # Member statistics
        info_lines.append(f"\n<b>👥 ᴍᴇᴍʙᴇʀꜱ:</b> {total_members}")
        info_lines.append(f"<b>👮 ᴀᴅᴍɪɴꜱ:</b> {admin_count}")
        info_lines.append(f"<b>🤖 ʙᴏᴛꜱ:</b> {bot_count}")

        if banned_count > 0:
            info_lines.append(f"<b>🚫 ʙᴀɴɴᴇᴅ:</b> {banned_count}")

        if deleted_count > 0:
            info_lines.append(f"<b>👻 ᴅᴇʟᴇᴛᴇᴅ ᴀᴄᴄᴏᴜɴᴛꜱ:</b> {deleted_count}")

        if premium_count > 0:
            info_lines.append(f"<b>⭐ ᴘʀᴇᴍɪᴜᴍ ᴜꜱᴇʀꜱ:</b> {premium_count}")

        # Description if available
        if chat_info.description:
            desc = chat_info.description
            if len(desc) > 100:
                desc = desc[:100] + "..."
            info_lines.append(f"\n<b>📝 ᴅᴇꜱᴄʀɪᴘᴛɪᴏɴ:</b>\n{html.escape(desc)}")

        # Linked chat if available
        linked = getattr(chat_info, "linked_chat", None)
        if linked:
            info_lines.append(f"\n<b>🔗 ʟɪɴᴋᴇᴅ ᴄʜᴀɴɴᴇʟ:</b> {html.escape(linked.title or '')}")
            info_lines.append(f"<b>🆔 ᴄʜᴀɴɴᴇʟ ɪᴅ:</b> <code>{linked.id}</code>")

        # Check user's admin status
        if user_id:
            try:
                user_member = await client.get_chat_member(chat_id, user_id)
                if user_member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                    role = 'ᴏᴡɴᴇʀ' if user_member.status == ChatMemberStatus.OWNER else 'ᴀᴅᴍɪɴɪꜱᴛʀᴀᴛᴏʀ'
                    info_lines.append(f"\n<b>🔐 ʏᴏᴜʀ ʀᴏʟᴇ:</b> {role}")
            except Exception:
                pass

        # Combine all info
        response = "<blockquote>" + "\n".join(info_lines) + "</blockquote>"

        await client.send_message(chat_id, response)

    except Exception as e:
        logger.warning(f"groupdata failed in {chat_id}: {e}")
        try:
            await client.send_message(
                chat_id,
                f"<blockquote>❌ <b>ᴇʀʀᴏʀ ɢᴇᴛᴛɪɴɢ ɢʀᴏᴜᴘ ᴅᴀᴛᴀ:</b>\n<code>{html.escape(str(e))}</code></blockquote>",
            )
        except Exception:
            pass
