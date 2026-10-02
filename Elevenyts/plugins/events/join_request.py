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
from pyrogram.types import ChatJoinRequest, InlineKeyboardButton, InlineKeyboardMarkup

from Elevenyts import app


@app.on_chat_join_request()
async def handle_join_request(_, request: ChatJoinRequest) -> None:
    """When someone requests to join a group, DM them a Verify button
    that deep-links back into the bot. Requires the bot to be a group
    admin with the "Invite Users" permission — Telegram then allows the
    bot to message the requester directly even if they've never started
    the bot before (Bot API 5.5+)."""
    user = request.from_user
    chat = request.chat
    if not user:
        return

    payload = f"verify_{chat.id}"
    deep_link = f"https://t.me/{app.username}?start={payload}"

    markup = InlineKeyboardMarkup(
        [[InlineKeyboardButton(text="Verify", url=deep_link)]]
    )

    try:
        target_chat_id = getattr(request, "user_chat_id", None) or user.id
        await app.send_message(
            target_chat_id,
            "<u>Click on the button below to verify yourself.</u>\n\n"
            f"Your request to join <b>{chat.title}</b> will be approved shortly.",
            reply_markup=markup,
        )
    except Exception:
        pass
