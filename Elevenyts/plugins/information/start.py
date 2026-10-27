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

import logging

from pyrogram import enums, errors, filters, types

from Elevenyts import app, config, db, lang
from Elevenyts.helpers import buttons, utils

logger = logging.getLogger(__name__)

# Hosted backup welcome image (used if the main image can't be sent)
BACKUP_START_IMG = "https://files.catbox.moe/vnl0a4.jpg"


# url -> Telegram file_id of the already-sent image (instant re-send), and
# links Telegram could not fetch itself (skip straight to upload next time).
_photo_ids: dict = {}
_link_bad: set = set()


async def _photo_reply(message, url: str, caption: str, key):
    """Send a photo from a link, as fast as possible.
    1) reuse the Telegram file_id from an earlier send (instant);
    2) send the link; 3) if Telegram can't fetch it, download the image and
    upload it directly. Returns True when a photo was sent."""
    def _remember(sent):
        try:
            _photo_ids[url] = sent.photo.file_id
        except Exception:
            pass

    fid = _photo_ids.get(url)
    if fid:
        try:
            await message.reply_photo(photo=fid, caption=caption, reply_markup=key)
            return True
        except errors.ChatSendPhotosForbidden:
            raise
        except Exception as e:
            _photo_ids.pop(url, None)
            logger.warning(f"Cached photo failed ({url}): {e}")

    if url not in _link_bad:
        try:
            sent = await message.reply_photo(
                photo=url, caption=caption, reply_markup=key)
            _remember(sent)
            return True
        except errors.ChatSendPhotosForbidden:
            raise
        except Exception as e:
            _link_bad.add(url)
            logger.warning(f"Photo by link failed ({url}): {e}")

    if not str(url).lower().startswith("http"):
        return False
    try:
        import io
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"HTTP {resp.status}")
                data = await resp.read()
        if len(data) < 1000 or len(data) > 9_000_000:
            raise RuntimeError(f"bad image size {len(data)}")
        bio = io.BytesIO(data)
        bio.name = "start.jpg"
        sent = await message.reply_photo(
            photo=bio, caption=caption, reply_markup=key)
        _remember(sent)
        return True
    except errors.ChatSendPhotosForbidden:
        raise
    except Exception as e:
        logger.warning(f"Photo upload failed ({url}): {e}")
        return False


@app.on_message(filters.command(["help"]) & filters.private & ~app.bl_users)
@lang.language()
async def _help(_, m: types.Message):
    """Handle /help command in private chats - shows help menu with image."""
    # Auto-delete command message
    try:
        await m.delete()
    except Exception:
        pass
    
    try:
        _ok = False
        for _p in (config.START_IMG, BACKUP_START_IMG):
            if await _photo_reply(
                m, _p, m.lang["help_menu"], buttons.help_markup(m.lang)
            ):
                _ok = True
                break
        if _ok:
            return
        raise RuntimeError("no photo sent")
    except Exception:
        # Fallback to text if photo fails
        await m.reply_text(
            text=m.lang["help_menu"],
            reply_markup=buttons.help_markup(m.lang),
        )


@app.on_message(filters.command(["start"]))
@lang.language()
async def start(_, message: types.Message):
    """
    Handle /start command - welcome message for users.

    - In private chat: Shows welcome message with inline buttons
    - In group chat: Shows short welcome message
    - Adds new users to database
    - Sends log to logger group for new users
    """
    # Auto-delete command message in group chats
    if message.chat.type != enums.ChatType.PRIVATE:
        try:
            await message.delete()
        except Exception:
            pass
    
    # Skip if message from channel or anonymous admin
    if not message.from_user:
        return

    # Check if user is blacklisted
    if message.from_user.id in app.bl_users and message.from_user.id not in db.notified:
        return await message.reply_text(message.lang["bl_user_notify"])

    # If /start help, show help menu
    if len(message.command) > 1 and message.command[1] == "help":
        return await _help(_, message)

    # Determine if chat is private or group
    private = message.chat.type == enums.ChatType.PRIVATE

    # Choose appropriate welcome message
    _text = (
        message.lang["start_pm"].format(message.from_user.first_name, app.name)
        if private
        else message.lang["start_gp"].format(app.name)
    )

    # The owner's own /start tells us the username for the Owner button
    # (the Owner button is shown once app.owner_url is a t.me link)
    if (
        message.from_user.id == config.OWNER_ID
        and message.from_user.username
    ):
        app.owner_url = f"https://t.me/{message.from_user.username}"

    key = buttons.start_key(message.lang, private)
    # Try the configured image, then the hosted backup image, then plain
    # text, so /start always answers even if an image can't be processed.
    sent = False
    for photo in (config.START_IMG, BACKUP_START_IMG):
        try:
            if await _photo_reply(message, photo, _text, key):
                sent = True
                break
        except errors.ChatSendPhotosForbidden:
            break
        except Exception:
            continue
    if not sent:
        await message.reply_text(
            text=_text,
            reply_markup=key,
        )

    # For private chats, add user to database if new
    if private:
        if await db.is_user(message.from_user.id):
            return  # User already exists, no need to add
        # Log new user to logger group
        await utils.send_log(message)
        # Add user to database
        return await db.add_user(message.from_user.id)


@app.on_message(filters.command(["playmode", "settings"]) & filters.group & ~app.bl_users)
@lang.language()
async def settings(_, message: types.Message):
    """
    Handle /playmode or /settings command - show group settings.

    Displays:
    - Play mode (everyone or admin only)
    - Current language
    - Options to change settings
    """
    # Auto-delete command message
    try:
        await message.delete()
    except Exception:
        pass
    
    admin_only = await db.get_play_mode(message.chat.id)  # Get play mode setting
    _language = "en"
    await utils.safe_text(
        message,
        message.lang["start_settings"].format(message.chat.title),
        reply_markup=buttons.settings_markup(
            message.lang, admin_only, _language, message.chat.id
        ),
        quote=True,
    )


@app.on_message(filters.new_chat_members, group=7)
@lang.language()
async def _new_member(_, message: types.Message):
    """
    Handle new member events - detect when bot is added to groups.

    - Leaves non-supergroup chats
    - Adds new groups to database
    """
    # Only work in supergroups (not basic groups)
    if message.chat.type != enums.ChatType.SUPERGROUP:
        return await message.chat.leave()

    # Check each new member
    for member in message.new_chat_members:
        if member.id == app.id:  # Bot itself was added
            if await db.is_chat(message.chat.id):
                return  # Chat already in database
            # Add chat to database (log is sent from new_chat.py with photo)
            await db.add_chat(message.chat.id)
