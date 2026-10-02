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
from pyrogram import filters
from pyrogram.types import Message

from Elevenyts import app


@app.on_message(filters.command(["start"]), group=-1)
async def verify_start(_, m: Message) -> None:
    """Intercepts /start when it carries a "verify_<chat_id>" deep-link
    payload (sent via the Verify button from join_request.py) and
    approves the user's pending join request for that group. Runs in
    group=-1 so it fires before the normal /start handler — it does
    NOT stop propagation, so the regular welcome menu still shows
    afterwards."""
    if len(m.command) < 2 or not m.command[1].startswith("verify_"):
        return  # not a verify deep link — let the normal /start handler run

    chat_id_str = m.command[1].removeprefix("verify_")
    try:
        target_chat_id = int(chat_id_str)
    except ValueError:
        return

    if not m.from_user:
        return

    try:
        await app.approve_chat_join_request(target_chat_id, m.from_user.id)
        await m.reply_text(
            "Your request to join the group will be approved shortly."
        )
    except Exception as e:
        await m.reply_text(f"Could not verify you: {e}")
