# /playstats - OWNER and SUDO users only.
# Shows how many songs the bot played today and in total.
import asyncio
import re
from datetime import datetime, timedelta, timezone

from pyrogram import filters, types

from Elevenyts import app, db
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


@app.on_message(filters.command(["playstats", "songstats"]) & app.sudo_filter)
async def playstats_cmd(_, m: types.Message):
    stats = await db.get_play_stats()
    today = datetime.now(timezone(timedelta(hours=5, minutes=30))).strftime("%Y-%m-%d")
    today_count = (stats.get("days") or {}).get(today, 0)
    total = stats.get("total", 0)

    await m.reply_text(
        "<blockquote>\U0001F4CA <b>\u0455\u1d0f\u0273\u0262 \u0455\u1d1b\u1d00\u1d1b\u0455</b></blockquote>\n"
        f"<blockquote>\U0001F4C5 Today: <b>{today_count}</b> songs\n"
        f"\U0001F3B5 Total: <b>{total}</b> songs</blockquote>"
    )
