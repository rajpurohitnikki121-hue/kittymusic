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


@app.on_message(
    filters.group & filters.regex(r"(?i)(^|\s)(\.|@|\/)admins?\b"),
    group=7,
)
async def mention_admins(_, message: types.Message):
    """
    Mention all group admins when someone types @admin, .admin, or /admin
    """
    try:
        # Extract the message without the trigger
        message_text = message.text or message.caption or ""
        cleaned_text = html.escape(
            TRIGGER_PATTERN.sub(" ", message_text).strip())

        # Get user info (handle anonymous admins)
        sender = message.from_user
        if sender:
            user_display = html.escape(f"{sender.first_name}")
            if sender.username:
                user_display += f" (@{sender.username})"
        else:
            # Anonymous admin or channel
            user_display = "ᴀɴᴏɴʏᴍᴏᴜꜱ ᴀᴅᴍɪɴ"

        # Build formatted reply message
        if cleaned_text:
            reply_msg = (
                f"<blockquote><b><i>\"{cleaned_text}\"</i></b>\n"
                f"ʀᴇᴘᴏʀᴛᴇᴅ ʙʏ: {user_display} 🔔</blockquote>\n\n"
            )
        else:
            reply_msg = (
                f"<blockquote>ʀᴇᴘᴏʀᴛᴇᴅ ʙʏ: {user_display} 🔔</blockquote>\n\n"
            )

        # Get all administrators
        mentions = []
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

                # Skip admins who have "Remain Anonymous" enabled
                if getattr(admin, "privileges", None):
                    if getattr(admin.privileges, "is_anonymous", False):
                        continue

                # Skip usernames in the excluded list
                if user.username and user.username.lower() in excluded:
                    continue

                # Add mention
                if user.username:
                    mentions.append(f"@{user.username}")
                else:
                    # Use HTML link format to mention users without username
                    mentions.append(
                        f"<a href='tg://user?id={user.id}'>"
                        f"{html.escape(user.first_name or 'Admin')}</a>")
        except Exception as e:
            logger.warning(f"@admin: could not fetch admins: {e}")
            await message.reply_text(
                "<blockquote>❌ Failed to fetch administrators. Make sure the bot has proper permissions.</blockquote>"
            )
            return

        if mentions:
            reply_msg += ", ".join(mentions)
        else:
            reply_msg += "<i>No visible human admins found to mention.</i>"

        # Send the reply
        try:
            await message.reply_text(reply_msg)
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
