# /playstats - OWNER and SUDO users only. Shows how many songs the bot has played, and how
# many each sudo user (and the owner) requested.
import asyncio
import re

from pyrogram import filters, types

from Elevenyts import app, config, db
from Elevenyts.helpers import _autoplay as autoplay

_UID = re.compile(r"tg://user\?id=(\d+)")


def _count_play(chat_id: int, media) -> None:
    """Runs every time a song starts playing (called from _autoplay)."""
    who = str(getattr(media, "user", "") or "")
    m = _UID.search(who)
    uid = int(m.group(1)) if m else None   # None -> autoplay / unknown
    asyncio.get_event_loop().create_task(_save(uid))


async def _save(uid) -> None:
    try:
        await db.add_play_stat(uid)
    except Exception:
        pass


autoplay.play_hook = _count_play


async def _name(uid: int) -> str:
    try:
        u = await app.get_users(uid)
        return u.mention
    except Exception:
        return f"<code>{uid}</code>"


@app.on_message(filters.command(["playstats", "songstats"]) & app.sudo_filter)
async def playstats_cmd(_, m: types.Message):
    stats = await db.get_play_stats()
    users = {int(k): v for k, v in (stats.get("users") or {}).items()}
    total = stats.get("total", 0)

    sudo_ids = set(await db.get_sudoers()) | {config.OWNER_ID}
    lines = ""
    for uid in sorted(sudo_ids, key=lambda u: users.get(u, 0), reverse=True):
        tag = " (owner)" if uid == config.OWNER_ID else ""
        lines += f"\n• {await _name(uid)}{tag}: <b>{users.get(uid, 0)}</b>"

    others = sum(v for k, v in users.items() if k not in sudo_ids)
    text = (
        "<blockquote>📊 <b>Song Stats</b>\n\n"
        f"🎵 Total songs played: <b>{total}</b>\n"
        f"🤖 Autoplay songs: <b>{stats.get('autoplay', 0)}</b>\n"
        f"👥 Other users: <b>{others}</b></blockquote>\n"
        f"<blockquote><b>Sudo users:</b>{lines or ' none'}</blockquote>"
    )
    await m.reply_text(text)
