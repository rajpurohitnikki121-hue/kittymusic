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
import asyncio

from pyrogram import filters
from pyrogram.enums import ChatMemberStatus
from pyrogram.errors import FloodWait
from pyrogram.types import Message

from Elevenyts import app

# Cute animal / flower emoji only — cycled through for each tagged member.
TAG_EMOJIS = [
    "🌸", "🌷", "🌹", "🌺", "🌻", "🌼", "💐",
    "🌱", "🌿", "🍃", "🐼", "🐰", "🐇", "🦋",
    "🐥", "🐤", "🦚", "🦢", "🐨",,"⚘","🐁",
"🐣","🐤","🐥","🦭","🐬","💮","🌾","☘","🍁",
"🍂","🐧","🐨","🐹","🐭","🦨"
]

# How many mentions to put in a single message before starting a new one,
# to stay well under Telegram's message-length limit.
MENTIONS_PER_MESSAGE = 25


async def _is_group_admin(message: Message) -> bool:
    """Return True if the message sender is an admin/creator of this chat."""
    try:
        member = await app.get_chat_member(message.chat.id, message.from_user.id)
    except Exception:
        return False
    return member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)


@app.on_message(
    filters.command(["tagall"])
    & filters.group
    & ~app.bl_users
)
async def tagall_command(_, m: Message) -> None:
    """Tag every member of the group, admin-only. Each mention is shown
    as a cute emoji you can tap to open that member's profile."""

    if not m.from_user:
        return

    if not await _is_group_admin(m):
        return await m.reply_text(
            "❌ Only group admins can use this command."
        )

    custom_text = ""
    if len(m.command) > 1:
        custom_text = m.text.split(None, 1)[1]

    await m.reply_text("🌸 Tagging everyone, please wait...")

    mentions = []
    emoji_index = 0

    try:
        async for member in app.get_chat_members(m.chat.id):
            user = member.user
            if not user or user.is_bot or user.is_deleted:
                continue

            emoji = TAG_EMOJIS[emoji_index % len(TAG_EMOJIS)]
            emoji_index += 1

            mentions.append(f'<a href="tg://user?id={user.id}">{emoji}</a>')
    except Exception as e:
        return await m.reply_text(f"❌ Could not fetch member list: {e}")

    if not mentions:
        return await m.reply_text("❌ No members found to tag.")

    for i in range(0, len(mentions), MENTIONS_PER_MESSAGE):
        chunk = mentions[i:i + MENTIONS_PER_MESSAGE]
        text = " ".join(chunk)
        if custom_text and i == 0:
            text = f"{custom_text}\n\n{text}"

        while True:
            try:
                await m.reply_text(text, disable_web_page_preview=True)
                break
            except FloodWait as e:
                await asyncio.sleep(e.value)

        await asyncio.sleep(1)
