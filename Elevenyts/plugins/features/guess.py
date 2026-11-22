# Song Guess game.
#   /guess      - start a round (bot shows movie + singer + hidden title)
#   /endguess   - end the round early (admins/sudo; members must wait for the timer)
#   /guesstop   - leaderboard of this group
# Tough mode: at the start the SINGER, the MOVIE and the blanks of the title
# are shown. The "Hint" button (max 2 hints) reveals more letters:
#   hint 1 -> first & last letter of every word
#   hint 2 -> a few more letters (a word is NEVER shown fully)
# A song is not repeated in the same group on the same day.
# The first person to type the correct song name wins:
#   5 points (no hint) / 3 points (1 hint) / 1 point (2 hints)
import asyncio
import difflib
import html
import random
import re
import time
from datetime import datetime, timedelta, timezone

from pyrogram import filters, types
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from Elevenyts import app, db

# (song title, movie / album, singer)
SONGS = [
    ("Tum Hi Ho", "Aashiqui 2", "Arijit Singh"),
    ("Kal Ho Naa Ho", "Kal Ho Naa Ho", "Sonu Nigam"),
    ("Channa Mereya", "Ae Dil Hai Mushkil", "Arijit Singh"),
    ("Kesariya", "Brahmastra", "Arijit Singh"),
    ("Apna Bana Le", "Bhediya", "Arijit Singh"),
    ("Tera Yaar Hoon Main", "Sonu Ke Titu Ki Sweety", "Arijit Singh"),
    ("Ilahi", "Yeh Jawaani Hai Deewani", "Arijit Singh"),
    ("Kabira", "Yeh Jawaani Hai Deewani", "Tochi Raina"),
    ("Badtameez Dil", "Yeh Jawaani Hai Deewani", "Benny Dayal"),
    ("Pehla Nasha", "Jo Jeeta Wohi Sikandar", "Udit Narayan"),
    ("Tujhe Dekha To", "Dilwale Dulhania Le Jayenge", "Kumar Sanu"),
    ("Chaiyya Chaiyya", "Dil Se", "Sukhwinder Singh"),
    ("Kuch Kuch Hota Hai", "Kuch Kuch Hota Hai", "Alka Yagnik"),
    ("Tum Se Hi", "Jab We Met", "Mohit Chauhan"),
    ("Agar Tum Saath Ho", "Tamasha", "Alka Yagnik"),
    ("Humsafar", "Badrinath Ki Dulhania", "Akhil Sachdeva"),
    ("Bol Do Na Zara", "Azhar", "Armaan Malik"),
    ("Soch Na Sake", "Airlift", "Arijit Singh"),
    ("Gerua", "Dilwale", "Arijit Singh"),
    ("Senorita", "Zindagi Na Milegi Dobara", "Farhan Akhtar"),
    ("Zinda", "Bhaag Milkha Bhaag", "Siddharth Mahadevan"),
    ("Samjhawan", "Humpty Sharma Ki Dulhania", "Arijit Singh"),
    ("Kaun Tujhe", "M.S. Dhoni", "Palak Muchhal"),
    ("Phir Bhi Tumko Chaahunga", "Half Girlfriend", "Arijit Singh"),
    ("Tera Ban Jaunga", "Kabir Singh", "Akhil Sachdeva"),
    ("Bekhayali", "Kabir Singh", "Sachet Tandon"),
    ("Hawayein", "Jab Harry Met Sejal", "Arijit Singh"),
    ("Mere Samne Wali Khidki Mein", "Padosan", "Kishore Kumar"),
    ("Lag Ja Gale", "Woh Kaun Thi", "Lata Mangeshkar"),
    ("Pal Pal Dil Ke Paas", "Blackmail", "Kishore Kumar"),
    ("Tujh Mein Rab Dikhta Hai", "Rab Ne Bana Di Jodi", "Roop Kumar Rathod"),
    ("Tum Mile", "Tum Mile", "Neeraj Shridhar"),
    ("Dil Diyan Gallan", "Tiger Zinda Hai", "Atif Aslam"),
    ("Jeena Jeena", "Badlapur", "Atif Aslam"),
    ("Tera Hone Laga Hoon", "Ajab Prem Ki Ghazab Kahani", "Atif Aslam"),
    ("Tadap Tadap", "Hum Dil De Chuke Sanam", "KK"),
    ("Pehli Nazar Mein", "Race", "Atif Aslam"),
    ("Moh Moh Ke Dhaage", "Dum Laga Ke Haisha", "Papon"),
    ("Mast Magan", "2 States", "Arijit Singh"),
    ("Muskurane Ki Wajah", "Citylights", "Arijit Singh"),
    ("Khairiyat", "Chhichhore", "Arijit Singh"),
    ("Raataan Lambiyan", "Shershaah", "Jubin Nautiyal"),
    ("Chaleya", "Jawan", "Arijit Singh"),
    ("Jhoome Jo Pathaan", "Pathaan", "Arijit Singh"),
    ("Deewani Mastani", "Bajirao Mastani", "Shreya Ghoshal"),
    ("Ghoomar", "Padmaavat", "Shreya Ghoshal"),
    ("Malhari", "Bajirao Mastani", "Vishal Dadlani"),
    ("Kar Gayi Chull", "Kapoor & Sons", "Badshah"),
    ("Pasoori", "Coke Studio", "Ali Sethi"),
    ("Jai Ho", "Slumdog Millionaire", "A. R. Rahman"),
    ("Kun Faya Kun", "Rockstar", "A. R. Rahman"),
    ("Tum Ho", "Rockstar", "Mohit Chauhan"),
    ("Saadda Haq", "Rockstar", "Mohit Chauhan"),
    ("Ae Watan", "Raazi", "Arijit Singh"),
    ("Dhoom Machale", "Dhoom", "Sunidhi Chauhan"),
    ("Kajra Re", "Bunty Aur Babli", "Alisha Chinai"),
    ("Munni Badnaam Hui", "Dabangg", "Mamta Sharma"),
    ("Sheila Ki Jawani", "Tees Maar Khan", "Sunidhi Chauhan"),
    ("Chikni Chameli", "Agneepath", "Shreya Ghoshal"),
    ("Desi Girl", "Dostana", "Vishal Dadlani"),
    ("Ghungroo", "War", "Arijit Singh"),
    ("Kala Chashma", "Baar Baar Dekho", "Badshah"),
    ("Lungi Dance", "Chennai Express", "Honey Singh"),
    ("Titli", "Chennai Express", "Chinmayi"),
    ("London Thumakda", "Queen", "Labh Janjua"),
    ("Nagada Sang Dhol", "Goliyon Ki Raasleela Ram-Leela", "Shreya Ghoshal"),
    ("Param Sundari", "Mimi", "Shreya Ghoshal"),
    ("Kaise Hua", "Kabir Singh", "Vishal Mishra"),
    ("Pee Loon", "Once Upon A Time In Mumbaai", "Mohit Chauhan"),
    ("Zaroorat", "Ek Villain", "Mustafa Zahid"),
    ("Galliyan", "Ek Villain", "Ankit Tiwari"),
    ("Banjaara", "Ek Villain", "Mohammad Irfan"),
    ("Sunn Raha Hai", "Aashiqui 2", "Ankit Tiwari"),
    ("Chahun Main Ya Naa", "Aashiqui 2", "Arijit Singh"),
    ("Piya Aaye Na", "Aashiqui 2", "KK"),
    ("Bulleya", "Ae Dil Hai Mushkil", "Amit Mishra"),
    ("Tere Naam", "Tere Naam", "Udit Narayan"),
    ("Dola Re Dola", "Devdas", "Kavita Krishnamurti"),
    ("Ghar More Pardesiya", "Kalank", "Shreya Ghoshal"),
    ("Dil Chahta Hai", "Dil Chahta Hai", "Shankar Mahadevan"),
    ("Suraj Hua Maddham", "Kabhi Khushi Kabhie Gham", "Sonu Nigam"),
    ("Jashn-e-Bahara", "Jodhaa Akbar", "Javed Ali"),
    ("Ek Ladki Ko Dekha Toh Aisa Laga", "1942: A Love Story", "Kumar Sanu"),
    ("Ek Do Teen", "Tezaab", "Alka Yagnik"),
    ("Chura Liya Hai Tumne", "Yaadon Ki Baaraat", "Asha Bhosle"),
    ("Yeh Shaam Mastani", "Kati Patang", "Kishore Kumar"),
    ("Roop Tera Mastana", "Aradhana", "Kishore Kumar"),
    ("Dum Maaro Dum", "Hare Rama Hare Krishna", "Asha Bhosle"),
    ("Taal Se Taal", "Taal", "Alka Yagnik"),
    ("Kar Har Maidan Fateh", "Sanju", "Sukhwinder Singh"),
    ("Bolna", "Kapoor & Sons", "Arijit Singh"),
    ("Balam Pichkari", "Yeh Jawaani Hai Deewani", "Vishal Dadlani"),
    ("Ainvayi Ainvayi", "Band Baaja Baaraat", "Salim Merchant"),
    ("Jag Ghoomeya", "Sultan", "Rahat Fateh Ali Khan"),
    ("Ranjha", "Shershaah", "B Praak"),
    ("Ve Maahi", "Kesari", "Arijit Singh"),
    ("Teri Mitti", "Kesari", "B Praak"),
    ("Qaafirana", "Kedarnath", "Arijit Singh"),
    ("Besabriyaan", "M.S. Dhoni", "Armaan Malik"),
    ("Aaoge Jab Tum", "Jab We Met", "Ustad Rashid Khan"),
]

ROUND_TIME = 90      # seconds before the round ends by itself
RESULT_TTL = 30      # seconds the result message stays before it is deleted
POINTS = (5, 3, 1)   # points for 0 / 1 / 2 hints used
MAX_HINTS = 2

games: dict = {}     # chat_id -> round info
_recent: dict = {}   # chat_id -> (day, [titles already used that day])
_IST = timezone(timedelta(hours=5, minutes=30))


def _norm(t: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (t or "").lower())


def _mask(title: str, level: int) -> str:
    """Hidden title: one blank per letter.
    level 1: first + last letter of each word; level 2: a few more.
    A word is never shown completely (at least one letter stays hidden)."""
    words = []
    for w in title.split():
        idx = [i for i, ch in enumerate(w) if ch.isalnum()]
        n = len(idx)
        show = set()
        if level >= 1 and n:
            show.add(0)
            if n >= 3:
                show.add(n - 1)
        if level >= 2 and n >= 4:
            show.update(range(0, n, 2))
        if n >= 2 and len(show) >= n:      # never reveal the whole word
            show.discard(n // 2)
        pos = {idx[k]: k for k in range(n)}
        out = []
        for i, ch in enumerate(w):
            if i not in pos or pos[i] in show:
                out.append(ch)
            else:
                out.append("_")
        words.append(" ".join(out))
    return "   ".join(words)


def _markup(g: dict):
    if g["level"] >= MAX_HINTS:
        return None
    left = MAX_HINTS - g["level"]
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(f"💡 ʜɪɴᴛ ({left} ʟᴇꜰᴛ)", callback_data=f"gmhint {g['chat_id']}")
    ]])


def _card(g: dict) -> str:
    movie = f"🎬 ᴍᴏᴠɪᴇ  ›  <b>{html.escape(g['movie'])}</b>\n"
    return (
        "<blockquote>❖ <b>ɢᴜᴇss ᴛʜᴇ sᴏɴɢ</b></blockquote>\n"
        f"<blockquote>🎤 sɪɴɢᴇʀ  ›  <b>{html.escape(g['singer'])}</b>\n"
        f"{movie}"
        f"🎧 ᴛɪᴛʟᴇ   ›  <code>{_mask(g['title'], g['level'])}</code></blockquote>\n"
        f"⭐ ᴡɪɴ <b>{POINTS[g['level']]}</b> ᴘᴏɪɴᴛs  ·  ⏳ {ROUND_TIME}s\n"
        "✍️ <i>ᴛʏᴘᴇ ᴛʜᴇ sᴏɴɢ ɴᴀᴍᴇ ɪɴ ᴄʜᴀᴛ!</i>"
    )


async def _edit(msg, text: str, markup=None) -> None:
    try:
        await msg.edit_text(text, reply_markup=markup)
    except Exception:
        pass


async def _del(msg) -> None:
    try:
        await msg.delete()
    except Exception:
        pass


async def _del_later(msg, delay: int) -> None:
    await asyncio.sleep(delay)
    await _del(msg)


async def _finish(chat_id: int, g: dict, send) -> None:
    """Round is over: delete the round card, post the result and delete the
    result after RESULT_TTL seconds. `send` is a coroutine function that
    sends the result text and returns the sent message."""
    await _del(g["msg"])
    res = await send()
    if res:
        asyncio.get_event_loop().create_task(_del_later(res, RESULT_TTL))


async def _run(chat_id: int, g: dict) -> None:
    """Timer: the round ends by itself after ROUND_TIME seconds."""
    try:
        await asyncio.sleep(ROUND_TIME)
        if games.get(chat_id) is g:
            games.pop(chat_id, None)
            await _finish(chat_id, g, lambda: app.send_message(
                chat_id,
                "<blockquote>⏰ <b>ᴛɪᴍᴇ ᴜᴘ!</b></blockquote>\n"
                f"<blockquote>🎵 ᴀɴsᴡᴇʀ  ›  <b>{html.escape(g['title'])}</b>\n"
                f"🎤 sɪɴɢᴇʀ  ›  {html.escape(g['singer'])}\n"
                f"🎬 ᴍᴏᴠɪᴇ  ›  {html.escape(g['movie'])}</blockquote>\n"
                "🔁 ɴᴇxᴛ ʀᴏᴜɴᴅ: /guess",
            ))
    except asyncio.CancelledError:
        pass
    except Exception:
        pass


@app.on_message(filters.command(["guess", "songguess"]) & filters.group & ~app.bl_users)
async def guess_start(_, m: types.Message):
    chat_id = m.chat.id
    if chat_id in games:
        warn = await m.reply_text("⚠️ <i>ᴀ ʀᴏᴜɴᴅ ɪs ᴀʟʀᴇᴀᴅʏ ʀᴜɴɴɪɴɢ. ɢᴜᴇss ɪᴛ ꜰɪʀsᴛ!</i>")
        asyncio.get_event_loop().create_task(_del_later(warn, 8))
        asyncio.get_event_loop().create_task(_del_later(m, 8))
        return

    today = datetime.now(_IST).strftime("%Y-%m-%d")
    day, used = _recent.get(chat_id, (today, []))
    if day != today:
        used = []                      # new day -> fresh list
    pool = [x for x in SONGS if x[0] not in used]
    if not pool:                       # all 100 songs used today: start over
        used = []
        pool = list(SONGS)
    _recent[chat_id] = (today, used)
    title, movie, singer = random.choice(pool)
    used.append(title)

    g = {"title": title, "movie": movie, "singer": singer, "level": 0, "chat_id": chat_id, "t0": time.time()}
    games[chat_id] = g
    g["msg"] = await m.reply_text(_card(g), reply_markup=_markup(g))
    await _del(m)   # remove the /guess command message
    g["task"] = asyncio.get_event_loop().create_task(_run(chat_id, g))


@app.on_message(filters.text & filters.group & ~app.bl_users, group=11)
async def guess_answer(_, m: types.Message):
    g = games.get(m.chat.id)
    if not g or not m.from_user or not m.text or m.text.startswith(("/", "!")):
        return
    guess, answer = _norm(m.text), _norm(g["title"])
    if not guess:
        return
    ok = guess == answer or (
        len(guess) >= 4
        and difflib.SequenceMatcher(None, guess, answer).ratio() >= 0.88
    )
    if not ok:
        return
    # first correct answer wins
    if games.pop(m.chat.id, None) is not g:
        return
    try:
        g["task"].cancel()
    except Exception:
        pass
    pts = POINTS[g["level"]]
    name = m.from_user.first_name or "User"
    try:
        await db.guess_add(m.chat.id, m.from_user.id, name, pts)
    except Exception:
        pass
    await _finish(m.chat.id, g, lambda: m.reply_text(
        "<blockquote>🎉 <b>ᴄᴏʀʀᴇᴄᴛ ᴀɴsᴡᴇʀ!</b></blockquote>\n"
        f"<blockquote>👑 ᴡɪɴɴᴇʀ  ›  {m.from_user.mention}\n"
        f"🎵 sᴏɴɢ  ›  <b>{html.escape(g['title'])}</b>\n"
        f"🎤 sɪɴɢᴇʀ  ›  {html.escape(g['singer'])}\n"
        f"⭐ ᴘᴏɪɴᴛs  ›  <b>+{pts}</b></blockquote>\n"
        "🔁 ɴᴇxᴛ ʀᴏᴜɴᴅ: /guess"
    ))


GAME_INFO_TEXT = (
    "<u><b>❖ ɢᴜᴇss ᴛʜᴇ sᴏɴɢ</b></u>\n\n"
    "<b>How to play</b>\n"
    "1. Type /guess in the group.\n"
    "2. The bot shows the singer, the movie and the hidden song name.\n"
    "3. Type the correct song name in chat. First one wins!\n"
    "4. Stuck? Tap 💡 Hint (2 hints) to reveal letters.\n\n"
    f"<b>Points:</b> {POINTS[0]} (no hint), {POINTS[1]} (1 hint), {POINTS[2]} (2 hints)\n"
    f"<b>Time:</b> {ROUND_TIME} seconds per round\n\n"
    "<b>Commands</b>\n"
    "/guess - start a round\n"
    "/guesstop - leaderboard\n"
    "/endguess - end early (admins; others wait for the timer)"
)


@app.on_callback_query(filters.regex("^guess_info$"))
async def guess_info_cb(_, cq: CallbackQuery):
    """Shown when the Game button in the help menu is tapped."""
    back = InlineKeyboardMarkup(
        [[InlineKeyboardButton(text="\u00ab Back", callback_data="help_main")]]
    )
    try:
        if cq.message.photo:
            await cq.message.edit_caption(GAME_INFO_TEXT, reply_markup=back)
        else:
            await cq.message.edit_text(GAME_INFO_TEXT, reply_markup=back)
    except Exception:
        pass
    await cq.answer()


@app.on_callback_query(filters.regex(r"^gmhint "))
async def guess_hint(_, q):
    try:
        chat_id = int(q.data.split()[1])
    except Exception:
        return await q.answer()
    g = games.get(chat_id)
    if not g:
        return await q.answer("This round is over.", show_alert=True)
    if g["level"] >= MAX_HINTS:
        return await q.answer("No hints left!", show_alert=True)
    g["level"] += 1
    await q.answer("💡 Hint revealed!")
    await _edit(g["msg"], _card(g), _markup(g))


@app.on_message(filters.command(["endguess"]) & filters.group & ~app.bl_users)
async def guess_end(_, m: types.Message):
    g = games.get(m.chat.id)
    if not g:
        info = await m.reply_text("No round is running. Start one with /guess")
        asyncio.get_event_loop().create_task(_del_later(info, 8))
        return await _del(m)
    # The answer is only shown after the full round time. Before that only
    # admins / sudo users can end the round early.
    left = int(ROUND_TIME - (time.time() - g["t0"]))
    uid = m.from_user.id if m.from_user else 0
    if left > 0 and uid not in app.sudoers and uid not in await db.get_admins(m.chat.id):
        wait = await m.reply_text(f"⏳ <i>ᴡᴀɪᴛ {left}s — ᴛʜᴇ ᴀɴsᴡᴇʀ ᴄᴏᴍᴇs ᴀꜰᴛᴇʀ {ROUND_TIME} sᴇᴄᴏɴᴅs.</i>")
        asyncio.get_event_loop().create_task(_del_later(wait, 6))
        return await _del(m)
    games.pop(m.chat.id, None)
    try:
        g["task"].cancel()
    except Exception:
        pass
    await _finish(m.chat.id, g, lambda: m.reply_text(
        f"<blockquote>🛑 <b>ʀᴏᴜɴᴅ ᴇɴᴅᴇᴅ</b>\n🎵 ᴀɴsᴡᴇʀ  ›  <b>{html.escape(g['title'])}</b></blockquote>"
    ))
    await _del(m)   # remove the /endguess command message


@app.on_message(filters.command(["guesstop"]) & filters.group & ~app.bl_users)
async def guess_top(_, m: types.Message):
    rows = await db.guess_top(m.chat.id)
    if not rows:
        return await m.reply_text("No scores yet. Play with /guess!")
    medals = ["🥇", "🥈", "🥉"]
    lines = ""
    for i, r in enumerate(rows):
        lines += (
            f"\n{medals[i] if i < 3 else str(i + 1) + '.'} "
            f"{html.escape(r.get('name', 'User'))} — "
            f"<b>{r.get('pts', 0)}</b> pts ({r.get('wins', 0)} wins)"
        )
    await m.reply_text(f"<blockquote>🏆 <b>ɢᴜᴇss ʟᴇᴀᴅᴇʀʙᴏᴀʀᴅ</b>\n{lines}</blockquote>")
