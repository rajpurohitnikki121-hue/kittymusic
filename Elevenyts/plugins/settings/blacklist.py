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
from pyrogram import StopPropagation, filters, types

from Elevenyts import app, db, lang


async def _leave_everywhere(chat_id: int) -> tuple[str, str]:
    """Make the assistant and the bot leave `chat_id`.
    Returns (bot_status, assistant_status) as short texts."""
    asst = "skipped"
    try:
        client = await db.get_client(chat_id)
        await client.leave_chat(chat_id)
        asst = "left ✅"
    except Exception as e:
        asst = f"not in chat / failed ({type(e).__name__})"
    try:
        await app.leave_chat(chat_id)
        bot = "left ✅"
    except Exception as e:
        bot = f"failed ({type(e).__name__}) - will leave on its first message"
    return bot, asst


@app.on_message(filters.group, group=-2)
async def _blacklisted_chat_guard(_, m: types.Message):
    """Any message in a blacklisted chat -> bot and assistant leave at once."""
    if m.chat and m.chat.id in db.blacklisted:
        await _leave_everywhere(m.chat.id)
        raise StopPropagation


#  ============== CHAT BLACKLIST COMMANDS ==============

@app.on_message(filters.command(["blacklistchat"]) & app.sudo_filter)
@lang.language()
async def _blacklist_chat(_, m: types.Message):
    """Add chat to blacklist."""
    # Auto-delete command message
    try:
        await m.delete()
    except Exception:
        pass
    
    if len(m.command) < 2:
        return await m.reply_text(
            "<blockquote><b>ᴜꜱᴀɢᴇ:</b>\n"
            "<code>/blacklistchat [chat_id]</code></blockquote>"
        )

    try:
        chat_id = int(m.command[1])
    except ValueError:
        return await m.reply_text("<blockquote>❌ Invalid chat ID</blockquote>")

    # The title is only for display. Even if the bot cannot look the chat up
    # (not a member / unknown to its session) the chat is still blacklisted.
    try:
        title = (await app.get_chat(chat_id)).title
    except Exception:
        title = f"Chat {chat_id}"

    already = chat_id in db.blacklisted
    if not already:
        await db.add_blacklist(chat_id)

    bot_st, asst_st = await _leave_everywhere(chat_id)

    await m.reply_text(
        f"<blockquote><u><b>{'⚠️ ᴀʟʀᴇᴀᴅʏ ʙʟᴀᴄᴋʟɪꜱᴛᴇᴅ' if already else '✅ ᴄʜᴀᴛ ʙʟᴀᴄᴋʟɪꜱᴛᴇᴅ'}</b></u>\n\n"
        f"<b>ᴄʜᴀᴛ:</b> {title}\n"
        f"<b>ɪᴅ:</b> <code>{chat_id}</code>\n"
        f"<b>ʙᴏᴛ:</b> {bot_st}\n"
        f"<b>ᴀꜱꜱɪꜱᴛᴀɴᴛ:</b> {asst_st}</blockquote>"
    )


@app.on_message(filters.command(["whitelistchat", "unblacklistchat"]) & app.sudo_filter)
@lang.language()
async def _whitelist_chat(_, m: types.Message):
    """Remove chat from blacklist."""
    # Auto-delete command message
    try:
        await m.delete()
    except Exception:
        pass
    
    if len(m.command) < 2:
        return await m.reply_text(
            "<blockquote><b>ᴜꜱᴀɢᴇ:</b>\n"
            "<code>/whitelistchat [chat_id]</code></blockquote>"
        )

    try:
        chat_id = int(m.command[1])
        try:
            chat = await app.get_chat(chat_id)
            chat_name = chat.title
        except:
            chat_name = f"Chat {chat_id}"
    except ValueError:
        return await m.reply_text("<blockquote>❌ Invalid chat ID</blockquote>")

    if chat_id not in db.blacklisted:
        return await m.reply_text(
            f"<blockquote>⚠️ {chat_name} is not blacklisted</blockquote>"
        )

    await db.del_blacklist(chat_id)
    await m.reply_text(
        f"<blockquote><u><b>✅ ᴄʜᴀᴛ ᴡʜɪᴛᴇʟɪꜱᴛᴇᴅ</b></u>\n\n"
        f"<b>ᴄʜᴀᴛ:</b> {chat_name}\n"
        f"<b>ɪᴅ:</b> <code>{chat_id}</code></blockquote>"
    )


@app.on_message(filters.command(["blacklistedchat", "blchats"]) & app.sudo_filter)
@lang.language()
async def _blacklisted_chats(_, m: types.Message):
    """Show all blacklisted chats."""
    # Auto-delete command message
    try:
        await m.delete()
    except Exception:
        pass
    
    sent = await m.reply_text("📋 Fetching blacklisted chats...")
    
    blacklisted = await db.get_blacklisted(chat=True)
    
    # Filter only chats (negative IDs)
    chats_list = [chat_id for chat_id in blacklisted if chat_id < 0]
    
    if not chats_list:
        return await sent.edit_text("<blockquote>✅ No chats are blacklisted</blockquote>")
    
    text = "<u><b>🚫 ʙʟᴀᴄᴋʟɪꜱᴛᴇᴅ ᴄʜᴀᴛꜱ:</b></u>\n<blockquote>"
    
    for chat_id in chats_list:
        try:
            chat = await app.get_chat(chat_id)
            text += f"\n- {chat.title} ({chat_id})"
        except:
            text += f"\n- Unknown Chat ({chat_id})"
    
    text += "\n\n</blockquote>"
    await sent.edit_text(text)


# ============== USER BLACKLIST COMMANDS ==============

@app.on_message(filters.command(["block"]) & app.sudo_filter)
@lang.language()
async def _block_user(_, m: types.Message):
    """Block a user from using the bot."""
    # Auto-delete command message
    try:
        await m.delete()
    except Exception:
        pass
    
    # Extract user from command or reply
    user_id = None
    
    if m.reply_to_message and m.reply_to_message.from_user:
        user_id = m.reply_to_message.from_user.id
        user_mention = m.reply_to_message.from_user.mention
    elif len(m.command) > 1:
        try:
            user_id = int(m.command[1])
            user = await app.get_users(user_id)
            user_mention = user.mention
        except ValueError:
            return await m.reply_text("<blockquote>❌ Invalid user ID</blockquote>")
        except Exception:
            return await m.reply_text("<blockquote>❌ User not found</blockquote>")
    else:
        return await m.reply_text(
            "<blockquote><b>ᴜꜱᴀɢᴇ:</b>\n"
            "<code>/block [user_id]</code>\n"
            "ᴏʀ ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴜꜱᴇʀ</blockquote>"
        )
    
    # Don't allow blocking sudo users
    if user_id in app.sudoers:
        return await m.reply_text("<blockquote>❌ Cannot block sudo users</blockquote>")
    
    if user_id in app.bl_users:
        return await m.reply_text(
            f"<blockquote>⚠️ {user_mention} is already blocked</blockquote>"
        )

    app.bl_users.add(user_id)
    await db.add_blacklist(user_id)
    await m.reply_text(
        f"<blockquote><u><b>✅ ᴜꜱᴇʀ ʙʟᴏᴄᴋᴇᴅ</b></u>\n\n"
        f"<b>ᴜꜱᴇʀ:</b> {user_mention}\n"
        f"<b>ɪᴅ:</b> <code>{user_id}</code></blockquote>"
    )


@app.on_message(filters.command(["unblock"]) & app.sudo_filter)
@lang.language()
async def _unblock_user(_, m: types.Message):
    """Unblock a user."""
    # Auto-delete command message
    try:
        await m.delete()
    except Exception:
        pass
    
    # Extract user from command or reply
    user_id = None
    
    if m.reply_to_message and m.reply_to_message.from_user:
        user_id = m.reply_to_message.from_user.id
        user_mention = m.reply_to_message.from_user.mention
    elif len(m.command) > 1:
        try:
            user_id = int(m.command[1])
            user = await app.get_users(user_id)
            user_mention = user.mention
        except ValueError:
            return await m.reply_text("<blockquote>❌ Invalid user ID</blockquote>")
        except Exception:
            user_mention = f"User {user_id}"
    else:
        return await m.reply_text(
            "<blockquote><b>ᴜꜱᴀɢᴇ:</b>\n"
            "<code>/unblock [user_id]</code>\n"
            "ᴏʀ ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴜꜱᴇʀ</blockquote>"
        )
    
    if user_id not in app.bl_users:
        return await m.reply_text(
            f"<blockquote>⚠️ {user_mention} is not blocked</blockquote>"
        )

    app.bl_users.discard(user_id)
    await db.del_blacklist(user_id)
    await m.reply_text(
        f"<blockquote><u><b>✅ ᴜꜱᴇʀ ᴜɴʙʟᴏᴄᴋᴇᴅ</b></u>\n\n"
        f"<b>ᴜꜱᴇʀ:</b> {user_mention}\n"
        f"<b>ɪᴅ:</b> <code>{user_id}</code></blockquote>"
    )


@app.on_message(filters.command(["blockedusers", "blusers"]) & app.sudo_filter)
@lang.language()
async def _blocked_users(_, m: types.Message):
    """Show all blocked users."""
    # Auto-delete command message
    try:
        await m.delete()
    except Exception:
        pass
    
    sent = await m.reply_text("📋 Fetching blocked users...")
    
    blacklisted = await db.get_blacklisted()
    
    if not blacklisted:
        return await sent.edit_text("<blockquote>✅ No users are blocked</blockquote>")
    
    text = "<u><b>🚫 ʙʟᴏᴄᴋᴇᴅ ᴜꜱᴇʀꜱ:</b></u>\n<blockquote>"
    
    for user_id in blacklisted:
        try:
            user = await app.get_users(user_id)
            text += f"\n- {user.mention} ({user_id})"
        except:
            text += f"\n- Deleted Account ({user_id})"
    
    text += "\n\n</blockquote>"
    await sent.edit_text(text)
