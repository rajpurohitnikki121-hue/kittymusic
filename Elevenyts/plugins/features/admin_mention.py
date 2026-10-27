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
import re
from pyrogram import filters, types, enums

from Elevenyts import app, config

logger = logging.getLogger(__name__)

# Pattern to detect admin triggers: @admin, .admin, /admin (also "admins").
# The trigger must stand alone (start of text or after a space) so words
# like "@administrator" or "x@admin.com" do not call the admins.
TRIGGER_PATTERN = re.compile(r"(?i)(^|\s)(\.|@|\/)admins?\b")

# Invisible character: a tag made of it notifies the admin, but the message
# stays short and clean (the same way Rose reports to admins).
_HIDDEN = "⁣"


@app.on_message(
    filters.group & filters.regex(r"(?i)(^|\s)(\.|@|\/)admins?\b"),
    group=7,
)
async def mention_admins(_, message: types.Message):
    """
    Notify all group admins when someone types @admin, .admin, or /admin.
    The bot replies "Reported to admins" to the message and quietly tags
    every human admin, so each of them gets a notification.
    """
    try:
        # Get user info (handle anonymous admins)
        sender = message.from_user
        if sender:
            user_display = html.escape(f"{sender.first_name}")
            if sender.username:
                user_display += f" (@{sender.username})"
        else:
            # Anonymous admin or channel
            user_display = "ᴀɴᴏɴʏᴍᴏᴜꜱ ᴀᴅᴍɪɴ"

        # Collect all human administrators
        ids = []
        excluded = [u.lower() for u in config.EXCLUDED_USERNAMES]
        try:
            async for admin in app.get_chat_members(
                message.chat.id,
                filter=enums.ChatMembersFilter.ADMINISTRATORS
            ):
                user = admin.user
                if not user:
                    continue

                # Skip bots and deleted accounts
                if user.is_bot or user.is_deleted:
                    continue

                # Skip the person who reported
                if sender and user.id == sender.id:
                    continue

                # Skip usernames in the excluded list
                if user.username and user.username.lower() in excluded:
                    continue

                ids.append(user.id)
        except Exception as e:
            logger.warning(f"@admin: could not fetch admins: {e}")
            await message.reply_text(
                "<blockquote>❌ Failed to fetch administrators. Make sure the bot has proper permissions.</blockquote>"
            )
            return

        if not ids:
            await message.reply_text(
                "<blockquote><i>No visible human admins found to mention.</i></blockquote>"
            )
            return

        header = (
            f"<blockquote>ʀᴇᴘᴏʀᴛᴇᴅ ᴛᴏ ᴀᴅᴍɪɴꜱ 🔔\n"
            f"ʀᴇᴘᴏʀᴛᴇᴅ ʙʏ: {user_display}</blockquote>"
        )

        # One single message for all admins (up to 50 tags)
        tags = "".join(
            f"<a href='tg://user?id={uid}'>{_HIDDEN}</a>" for uid in ids[:50]
        )
        try:
            await message.reply_text(header + tags)
        except Exception as e:
            logger.warning(f"@admin: failed to send admin notification: {e}")
            await message.reply_text(
                "<blockquote>❌ Failed to send admin notification.</blockquote>"
            )
    except Exception as e:
        logger.warning(f"@admin: error while processing admin mention: {e}")
        # Catch all exceptions to prevent bot crashes
        try:
            await message.reply_text("<blockquote>❌ An error occurred while processing admin mention.</blockquote>")
        except Exception:
            pass  # Silent failure if reply fails
