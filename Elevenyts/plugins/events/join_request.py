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

from pyrogram.types import (
    ChatJoinRequest,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from Elevenyts import app


@app.on_chat_join_request()
async def handle_join_request(_, request: ChatJoinRequest) -> None:
    """Send a verification message when a user sends a join request."""

    user = request.from_user
    if not user:
        return

    deep_link = f"https://t.me/{app.username}?start=verify"

    markup = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text="🔐 𝐕𝐄𝐑𝐈𝐅𝐘 𝐌𝐘𝐒𝐄𝐋𝐅",
                    url=deep_link,
                )
            ]
        ]
    )

    group_name = request.chat.title or "This Group"

    text = (
        "🔐 𝐕𝐄𝐑𝐈𝐅𝐈𝐂𝐀𝐓𝐈𝐎𝐍\n\n"
        f"📌 𝐆𝐫𝐨𝐮𝐩: {group_name}\n\n"
        "Your request has been sent successfully. ♡\n\n"
        "⚠️ 𝐏𝐥𝐞𝐚𝐬𝐞 𝐯𝐞𝐫𝐢𝐟𝐲 𝐲𝐨𝐮𝐫𝐬𝐞𝐥𝐟 "
        "𝐛𝐞𝐟𝐨𝐫𝐞 𝐚𝐝𝐦𝐢𝐧 𝐚𝐩𝐩𝐫𝐨𝐯𝐚𝐥.\n\n"
        "✅ 𝐕𝐞𝐫𝐢𝐟𝐲 𝐘𝐨𝐮𝐫𝐬𝐞𝐥𝐟"
    )

    try:
        target_chat_id = getattr(request, "user_chat_id", None) or user.id

        await app.send_message(
            target_chat_id,
            text,
            reply_markup=markup,
        )

    except Exception:
        pass
