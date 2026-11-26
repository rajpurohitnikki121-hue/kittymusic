# Render usage watcher.
#   * every 6 hours checks Render bandwidth (month so far) and the bot's disk
#   * if bandwidth is >= 80% of the limit, or is expected to hit the limit
#     within ~1 day, a message is sent to the LOGGER group and the OWNER is tagged
#   * /renderusage (owner / sudo) shows the numbers right now
#
# Env variables (all optional):
#   RENDER_API_KEY       Render dashboard -> Account Settings -> API Keys
#                        (without it only the disk check works)
#   RENDER_SERVICE_ID    srv-xxxx  (Render sets this automatically)
#   BANDWIDTH_LIMIT_GB   monthly bandwidth limit to compare with (default 100)
#   DISK_WARN_PERCENT    warn when the disk is this full (default 85)
#   ALERT_TAG            who to tag in the alert (default @pixieiii)
import asyncio
import html
import os
import shutil
import time
from datetime import datetime, timedelta, timezone

import aiohttp
from pyrogram import filters, types

from Elevenyts import app, config, db, logger

CHECK_EVERY = 6 * 3600      # seconds between checks
ALERT_GAP = 24 * 3600       # same alert at most once per day
API = "https://api.render.com/v1/metrics/bandwidth"


def _cfg():
    return (
        os.getenv("RENDER_API_KEY", "").strip(),
        os.getenv("RENDER_SERVICE_ID", "").strip(),
        float(os.getenv("BANDWIDTH_LIMIT_GB", "100") or 100),
        float(os.getenv("DISK_WARN_PERCENT", "85") or 85),
    )


def _walk(o, acc):
    """Sum every numeric "value" in the Render metrics response."""
    if isinstance(o, dict):
        if isinstance(o.get("unit"), str):
            acc["unit"] = o["unit"]
        v = o.get("value")
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            acc["total"] += v
        for k, x in o.items():
            if k != "value":
                _walk(x, acc)
    elif isinstance(o, list):
        for x in o:
            _walk(x, acc)


def _to_gb(total: float, unit) -> tuple[float, str]:
    u = (unit or "").lower()
    if u in ("b", "byte", "bytes"):
        return total / 1e9, "bytes"
    if u in ("kb", "kib"):
        return total / 1e6, "KB"
    if u in ("gb", "gib"):
        return total, "GB"
    if u in ("mb", "mib"):
        return total / 1e3, "MB"
    return total / 1e3, f"{unit or 'unknown'} (assumed MB)"


async def _bandwidth_gb(key: str, service: str, start: datetime, end: datetime):
    """Returns (gb_used, unit_text, raw_preview) or raises."""
    params = {
        "resource": service,
        "startTime": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "endTime": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    headers = {"Authorization": f"Bearer {key}", "Accept": "application/json"}
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as s:
        async with s.get(API, params=params, headers=headers) as r:
            text = await r.text()
            if r.status != 200:
                raise RuntimeError(f"Render API {r.status}: {text[:200]}")
            data = await r.json(content_type=None)
    acc = {"total": 0.0, "unit": None}
    _walk(data, acc)
    gb, unit = _to_gb(acc["total"], acc["unit"])
    return gb, unit, text[:300]


def _disk():
    du = shutil.disk_usage("/")
    return du.used / 1e9, du.total / 1e9, du.used * 100 / du.total


async def _usage() -> dict:
    key, service, limit, _ = _cfg()
    out = {"limit": limit}
    now = datetime.now(timezone.utc)
    if key and service:
        try:
            month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            out["used"], out["unit"], out["raw"] = await _bandwidth_gb(key, service, month, now)
            out["day"], _, _ = await _bandwidth_gb(key, service, now - timedelta(hours=24), now)
        except Exception as e:
            out["error"] = str(e)
    else:
        out["error"] = "RENDER_API_KEY / RENDER_SERVICE_ID not set"
    out["disk"] = _disk()
    return out


def _owner_tag() -> str:
    """Who gets tagged in the alert. Default @pixieiii; change with ALERT_TAG."""
    tag = os.getenv("ALERT_TAG", "@pixieiii").strip() or "@pixieiii"
    return html.escape(tag if tag.startswith("@") else f"@{tag}")


async def _send(text: str) -> None:
    try:
        if not app.logger or not await db.is_logger():
            return
        await app.send_message(chat_id=app.logger, text=text)
    except Exception as e:
        logger.warning(f"renderwatch: could not send alert: {e}")


async def _may_alert(kind: str) -> bool:
    """True if this alert was not sent in the last 24 h (kept in the database)."""
    try:
        doc = await db.cache.find_one({"_id": "renderwatch"}) or {}
        last = (doc.get("last") or {}).get(kind, 0)
        if time.time() - last < ALERT_GAP:
            return False
        await db.cache.update_one(
            {"_id": "renderwatch"}, {"$set": {f"last.{kind}": time.time()}}, upsert=True
        )
        return True
    except Exception:
        return True


async def _check() -> None:
    u = await _usage()
    _, _, _, disk_warn = _cfg()

    used_gb, total_gb, pct = u["disk"]
    if pct >= disk_warn and await _may_alert("disk"):
        await _send(
            f"{_owner_tag()} ⚠️ <b>Disk almost full</b>\n"
            f"<blockquote>{used_gb:.1f} GB / {total_gb:.1f} GB used ({pct:.0f}%)</blockquote>"
        )

    if "used" in u:
        used, limit, day = u["used"], u["limit"], u.get("day", 0)
        if used + day >= limit and await _may_alert("bw_day"):
            await _send(
                f"{_owner_tag()} 🚨 <b>Render bandwidth will end within ~1 day</b>\n"
                f"<blockquote>Used this month: {used:.1f} GB / {limit:.0f} GB\n"
                f"Last 24h: {day:.1f} GB</blockquote>\n"
                "Free services stop when the monthly limit is over."
            )
        elif used >= 0.8 * limit and await _may_alert("bw_80"):
            await _send(
                f"{_owner_tag()} ⚠️ <b>Render bandwidth 80% used</b>\n"
                f"<blockquote>{used:.1f} GB / {limit:.0f} GB ({used * 100 / limit:.0f}%)\n"
                f"Last 24h: {day:.1f} GB</blockquote>"
            )


async def _loop() -> None:
    await asyncio.sleep(120)
    while True:
        try:
            await _check()
        except Exception as e:
            logger.warning(f"renderwatch error: {e}")
        await asyncio.sleep(CHECK_EVERY)


asyncio.create_task(_loop())


@app.on_message(filters.command(["renderusage"]) & app.sudo_filter)
async def renderusage_cmd(_, m: types.Message):
    u = await _usage()
    d_used, d_total, d_pct = u["disk"]
    text = (
        "<blockquote>📊 <b>Render usage</b></blockquote>\n"
        f"<blockquote>💾 Disk: {d_used:.1f} / {d_total:.1f} GB ({d_pct:.0f}%)\n"
    )
    if "used" in u:
        text += (
            f"🌐 Bandwidth (this month): <b>{u['used']:.2f} GB</b> / {u['limit']:.0f} GB\n"
            f"🕐 Last 24h: {u.get('day', 0):.2f} GB\n"
            f"📏 Unit read as: {html.escape(u['unit'])}</blockquote>\n"
            f"<code>{html.escape(u['raw'])}</code>"
        )
    else:
        text += f"🌐 Bandwidth: ❌ {html.escape(u['error'])}</blockquote>"
    await m.reply_text(text)
