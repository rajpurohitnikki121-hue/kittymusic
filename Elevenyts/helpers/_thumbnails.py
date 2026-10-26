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
import os
import math
import asyncio
import aiohttp

from PIL import (
    Image,
    ImageDraw,
    ImageEnhance,
    ImageFilter,
    ImageFont,
)

from Elevenyts import config
from Elevenyts.helpers import Track


SIZE = (1280, 720)
SS = 2  # the card is drawn at 2x and scaled down: smooth edges and icons

# ---- colours ----
BORDER = (74, 144, 226, 255)       # blue card border
RED = (255, 59, 59, 255)           # progress (played part)
TRACK_GREY = (95, 95, 95, 255)     # progress (rest)
WHITE = (255, 255, 255, 255)
ARTIST = (222, 222, 228, 255)
GREEN = (46, 204, 113, 255)
YELLOW = (241, 196, 15, 255)
HEART = (255, 59, 59, 255)

_FONT_PATHS = [
    "Elevenyts/helpers/Raleway-Bold.ttf",
    "Elevenyts/helpers/Raleway-BoldItalic.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]


def _load_font(paths, size):
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _fit_text(draw, text, font, max_w):
    """Cut the text with '...' so it fits max_w pixels."""
    text = (text or "").strip()
    if draw.textlength(text, font=font) <= max_w:
        return text
    while text and draw.textlength(text + "...", font=font) > max_w:
        text = text[:-1]
    return text.rstrip() + "..."


def _trim_black_bars(img: Image.Image) -> Image.Image:
    """YouTube thumbnails often have black bars on top/bottom - cut them."""
    try:
        g = img.convert("L")
        w, h = g.size
        px = g.resize((1, h), Image.BILINEAR).load()
        top, bottom = 0, h
        while top < h // 3 and px[0, top] < 12:
            top += 1
        while bottom > h - h // 3 and px[0, bottom - 1] < 12:
            bottom -= 1
        if bottom - top > h // 2:
            return img.crop((0, top, w, bottom))
    except Exception:
        pass
    return img


def _cover_fit(src: Image.Image, size) -> Image.Image:
    sr = src.width / src.height
    dr = size[0] / size[1]
    if sr > dr:
        nh = size[1]
        nw = int(nh * sr)
    else:
        nw = size[0]
        nh = int(nw / sr)
    r = src.resize((nw, nh))
    l = (nw - size[0]) // 2
    t = (nh - size[1]) // 2
    return r.crop((l, t, l + size[0], t + size[1]))


def _soft_blur(img: Image.Image, radius: int = 8) -> Image.Image:
    """Cheap strong blur: shrink, blur, enlarge (fast on small servers)."""
    w, h = img.size
    small = img.resize((max(1, w // 4), max(1, h // 4)), Image.BILINEAR)
    small = small.filter(ImageFilter.GaussianBlur(radius))
    return small.resize((w, h), Image.BILINEAR)


def _rounded_mask(size, radius):
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).rounded_rectangle(
        (0, 0, size[0] - 1, size[1] - 1), radius=radius, fill=255)
    return m


# ---------------- small icon drawers (all coordinates are @2x) -------------
def _arrow_head(d, x, y, dx, dy, s, col):
    # triangle pointing in direction (dx, dy)
    ang = math.atan2(dy, dx)
    p1 = (x + s * math.cos(ang), y + s * math.sin(ang))
    p2 = (x + s * math.cos(ang + 2.5), y + s * math.sin(ang + 2.5))
    p3 = (x + s * math.cos(ang - 2.5), y + s * math.sin(ang - 2.5))
    d.polygon([p1, p2, p3], fill=col)


def _icon_shuffle(d, cx, cy, s, col):
    w = max(3, s // 7)
    d.line([(cx - s, cy - s * 0.55), (cx - s * 0.2, cy - s * 0.55),
            (cx + s * 0.35, cy + s * 0.55), (cx + s * 0.8, cy + s * 0.55)],
           fill=col, width=w, joint="curve")
    d.line([(cx - s, cy + s * 0.55), (cx - s * 0.2, cy + s * 0.55),
            (cx + s * 0.35, cy - s * 0.55), (cx + s * 0.8, cy - s * 0.55)],
           fill=col, width=w, joint="curve")
    _arrow_head(d, cx + s * 1.05, cy + s * 0.55, 1, 0, s * 0.42, col)
    _arrow_head(d, cx + s * 1.05, cy - s * 0.55, 1, 0, s * 0.42, col)


def _icon_repeat(d, cx, cy, s, col):
    w = max(3, s // 7)
    d.arc((cx - s, cy - s * 0.7, cx + s, cy + s * 0.7), 200, 340, fill=col, width=w)
    d.arc((cx - s, cy - s * 0.7, cx + s, cy + s * 0.7), 20, 160, fill=col, width=w)
    _arrow_head(d, cx + s * 0.88, cy - s * 0.38, 1, 0.9, s * 0.42, col)
    _arrow_head(d, cx - s * 0.88, cy + s * 0.38, -1, -0.9, s * 0.42, col)


def _icon_prev(d, cx, cy, s, col):
    d.polygon([(cx + s * 0.7, cy - s), (cx + s * 0.7, cy + s), (cx - s * 0.5, cy)], fill=col)
    d.rectangle((cx - s * 0.95, cy - s, cx - s * 0.6, cy + s), fill=col)


def _icon_next(d, cx, cy, s, col):
    d.polygon([(cx - s * 0.7, cy - s), (cx - s * 0.7, cy + s), (cx + s * 0.5, cy)], fill=col)
    d.rectangle((cx + s * 0.6, cy - s, cx + s * 0.95, cy + s), fill=col)


def _icon_pause(d, cx, cy, s, col):
    d.rectangle((cx - s * 0.8, cy - s, cx - s * 0.2, cy + s), fill=col)
    d.rectangle((cx + s * 0.2, cy - s, cx + s * 0.8, cy + s), fill=col)


def _icon_heart(d, cx, cy, s, col):
    pts = []
    for i in range(0, 360, 4):
        t = math.radians(i)
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((cx + x * s / 16.0, cy - y * s / 16.0 + s * 0.1))
    d.polygon(pts, fill=col)


def _icon_headphones(d, cx, cy, s, col):
    w = max(3, s // 6)
    d.arc((cx - s, cy - s, cx + s, cy + s), 180, 360, fill=col, width=w)
    d.line([(cx - s + w / 2, cy), (cx - s + w / 2, cy + s * 0.2)], fill=col, width=w)
    d.line([(cx + s - w / 2, cy), (cx + s - w / 2, cy + s * 0.2)], fill=col, width=w)
    d.ellipse((cx - s * 1.05, cy + s * 0.05, cx - s * 0.35, cy + s * 0.8), fill=col)
    d.ellipse((cx + s * 0.35, cy + s * 0.05, cx + s * 1.05, cy + s * 0.8), fill=col)


class Thumbnail:

    def __init__(self):
        self.title_font = _load_font(_FONT_PATHS, 44 * SS)
        self.artist_font = _load_font(_FONT_PATHS, 27 * SS)
        self.time_font = _load_font(_FONT_PATHS, 20 * SS)

    async def save_thumb(self, output_path: str, url: str):

        async with aiohttp.ClientSession() as session:

            async with session.get(url) as resp:

                with open(output_path, "wb") as f:
                    f.write(await resp.read())

        return output_path

    async def generate(self, song: Track, size=SIZE) -> str:

        try:

            os.makedirs("cache", exist_ok=True)
            temp = f"cache/temp_{song.id}.jpg"
            output = f"cache/{song.id}_glass.png"

            if os.path.exists(output):
                return output

            await self.save_thumb(temp, song.thumbnail)

            return await asyncio.get_event_loop().run_in_executor(
                None,
                self._generate_sync,
                temp,
                output,
                song,
                size
            )

        except Exception:
            return config.DEFAULT_THUMB

    @staticmethod
    def _artist_of(song) -> str:
        for name in ("channel_name", "channel", "artist", "uploader", "author"):
            v = getattr(song, name, None)
            if isinstance(v, str) and v.strip():
                return v.strip()
        return ""

    def _generate_sync(
        self,
        temp: str,
        output: str,
        song: Track,
        size=SIZE
    ) -> str:

        try:
            W, H = size

            with Image.open(temp) as temp_img:
                src = _trim_black_bars(temp_img.convert("RGB"))

            # ---- blurred full background from the cover ----
            bg = _cover_fit(src, (W, H))
            bg = _soft_blur(bg, 7)
            bg = ImageEnhance.Brightness(bg).enhance(0.92).convert("RGBA")

            # ---- frosted glass card ----
            cx0, cy0, cx1, cy1 = 152, 127, 1128, 593
            cw, ch = cx1 - cx0, cy1 - cy0
            glass = bg.crop((cx0, cy0, cx1, cy1))
            glass = _soft_blur(glass.convert("RGB"), 5).convert("RGBA")
            glass = Image.alpha_composite(
                glass, Image.new("RGBA", glass.size, (255, 255, 255, 40)))
            # light dark tint so the white text stays readable on bright covers
            glass = Image.alpha_composite(
                glass, Image.new("RGBA", glass.size, (0, 0, 0, 48)))
            bg.paste(glass, (cx0, cy0), _rounded_mask((cw, ch), 44))

            # ---- everything else is drawn big (2x) and scaled down ----
            layer = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
            d = ImageDraw.Draw(layer)

            # card border
            d.rounded_rectangle(
                (cx0 * SS, cy0 * SS, cx1 * SS, cy1 * SS),
                radius=44 * SS, outline=BORDER, width=4 * SS)

            # cover (rounded square) with soft shadow
            side = 320
            sx, sy = 216, 190
            square = src
            m = min(square.size)
            l = (square.width - m) // 2
            t = (square.height - m) // 2
            square = square.crop((l, t, l + m, t + m)).resize(
                (side * SS, side * SS), Image.LANCZOS).convert("RGBA")

            shadow = Image.new("RGBA", layer.size, (0, 0, 0, 0))
            ImageDraw.Draw(shadow).rounded_rectangle(
                ((sx + 6) * SS, (sy + 14) * SS,
                 (sx + side + 6) * SS, (sy + side + 14) * SS),
                radius=38 * SS, fill=(0, 0, 0, 110))
            shadow = shadow.filter(ImageFilter.GaussianBlur(14 * SS))
            layer = Image.alpha_composite(layer, shadow)
            layer.paste(square, (sx * SS, sy * SS),
                        _rounded_mask((side * SS, side * SS), 38 * SS))
            d = ImageDraw.Draw(layer)

            # text column
            tx = 596
            max_w = 1097 - tx

            title = _fit_text(d, song.title, self.title_font, max_w * SS)
            d.text((tx * SS, 224 * SS), title, font=self.title_font, fill=WHITE)

            artist = self._artist_of(song)
            if artist:
                artist = _fit_text(d, artist, self.artist_font, max_w * SS)
                d.text((tx * SS, 282 * SS), artist,
                       font=self.artist_font, fill=ARTIST)

            # progress bar
            bar_y = 333
            bx0, bx1 = tx, 1077
            bh = 5
            d.rounded_rectangle(
                (bx0 * SS, (bar_y - bh // 2) * SS, bx1 * SS, (bar_y + bh // 2 + 1) * SS),
                radius=3 * SS, fill=TRACK_GREY)
            r = 9
            d.ellipse(((bx0 - r + 4) * SS, (bar_y - r) * SS,
                       (bx0 + r + 4) * SS, (bar_y + r) * SS), fill=WHITE)

            # times
            d.text((tx * SS, 348 * SS), "00:00", font=self.time_font, fill=WHITE)
            dur = str(getattr(song, "duration", "") or "")
            if dur:
                tw = d.textlength(dur, font=self.time_font)
                d.text((bx1 * SS - tw, 348 * SS), dur,
                       font=self.time_font, fill=WHITE)

            # control icons
            iy = 410 * SS
            s = 15 * SS
            for fn, x, col in (
                (_icon_shuffle, 612, GREEN),
                (_icon_repeat, 660, YELLOW),
                (_icon_prev, 708, WHITE),
                (_icon_pause, 753, WHITE),
                (_icon_next, 798, WHITE),
                (_icon_heart, 844, HEART),
                (_icon_headphones, 890, WHITE),
            ):
                fn(d, x * SS, iy, s if fn is not _icon_heart else s * 1.15, col)

            layer = layer.resize((W, H), Image.LANCZOS)
            out = Image.alpha_composite(bg, layer).convert("RGB")
            out.save(output)

            try:
                os.remove(temp)

            except OSError:
                pass

            return output

        except Exception:
            return config.DEFAULT_THUMB
