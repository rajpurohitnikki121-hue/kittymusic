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

from pyrogram import enums, errors, filters, types

from Elevenyts import app, config, db, lang
from Elevenyts.helpers import buttons, utils

START_IMG   = "https://files.catbox.moe/vnl0a4.jpg"
START_TEXT  = (
    "👋🏻 𝐇𝐞𝐲, {mention} ♡\n\n"
    "🎵 𐙚 𝐈𝐒𝐇𝐐 ✘ 𝐌𝐮𝐬𝐢𝐜 ᥫ᭡\n\n"
    "🥀 𝐒𝐦𝐨𝐨𝐭𝐡 𝐚𝐧𝐝 𝐥𝐚𝐠-𝐟𝐫𝐞𝐞 𝐦𝐮𝐬𝐢𝐜 𝐛𝐨𝐭 𝐰𝐢𝐭𝐡 𝐞𝐚𝐬𝐲 𝐪𝐮𝐞𝐮𝐞 "
    "𝐦𝐚𝐧𝐚𝐠𝐞𝐦𝐞𝐧𝐭 𝐚𝐧𝐝 𝐮𝐬𝐞𝐟𝐮𝐥 𝐟𝐞𝐚𝐭𝐮𝐫𝐞𝐬.\n\n"
    "𝐂𝐥𝐢𝐜𝐤 𝐨𝐧 𝐭𝐡𝐞 𝐇𝐞𝐥𝐩 𝐛𝐮𝐭𝐭𝐨𝐧 𝐟𝐨𝐫 𝐦𝐨𝐫𝐞 𝐢𝐧𝐟𝐨 ✦"
)


@app.on_message(filters.command(["help"]) & filters.private & ~app.bl_users)
@lang.language()
async def _help(_, m: types.Message):
    """Handle /help command in private chats - shows help menu with image."""
    try:
        await m.delete()
    except Exception:
        pass

    try:
        await m.reply_photo(
            photo=START_IMG,
            caption=m.lang["help_menu"],
            reply_markup=buttons.help_markup(m.lang),
            quote=True,
        )
    except Exception:
        await m.reply_text(
            text=m.lang["help_menu"],
            reply_markup=buttons.help_markup(m.lang),
            quote=True,
        )


@app.on_message(filters.command(["start"]))
@lang.language()
async def start(_, message: types.Message):
    """Handle /start command."""
    if message.chat.type != enums.ChatType.PRIVATE:
        try:
            await message.delete()
        except Exception:
            pass

    if not message.from_user:
        return

    if message.from_user.id in app.bl_users and message.from_user.id not in db.notified:
        return await message.reply_text(message.lang["bl_user_notify"])

    if len(message.command) > 1 and message.command[1] == "help":
        return await _help(_, message)

    private = message.chat.type == enums.ChatType.PRIVATE

    if private:
        # Private: custom Ishq welcome, NO buttons
        _text = START_TEXT.format(mention=message.from_user.mention)
        try:
            await message.reply_photo(
                photo=START_IMG,
                caption=_text,
                quote=False,
            )
        except errors.ChatSendPhotosForbidden:
            await message.reply_text(text=_text)

        if await db.is_user(message.from_user.id):
            return
        await utils.send_log(message)
        return await db.add_user(message.from_user.id)

    else:
        # Group: short message with existing lang string
        _text = message.lang["start_gp"].format(app.name)
        key = buttons.start_key(message.lang, private)
        try:
            await message.reply_photo(
                photo=START_IMG,
                caption=_text,
                reply_markup=key,
                quote=True,
            )
        except errors.ChatSendPhotosForbidden:
            await message.reply_text(
                text=_text,
                reply_markup=key,
                quote=True,
            )


@app.on_message(filters.command(["playmode", "settings"]) & filters.group & ~app.bl_users)
@lang.language()
async def settings(_, message: types.Message):
    """Handle /playmode or /settings command."""
    try:
        await message.delete()
    except Exception:
        pass

    admin_only = await db.get_play_mode(message.chat.id)
    _language = "en"
    await utils.safe_text(
        message,
        message.lang["start_settings"].format(message.chat.title),
        reply_markup=buttons.settings_markup(
            message.lang, admin_only, _language, message.chat.id
        ),
        quote=True,
    )
