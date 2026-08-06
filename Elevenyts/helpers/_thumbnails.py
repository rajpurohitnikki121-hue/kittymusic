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
import re
import asyncio
import aiohttp
import base64

from PIL import (
    Image,
    ImageDraw,
    ImageEnhance,
    ImageFilter,
    ImageFont
)

from Elevenyts import config
from Elevenyts.helpers import Track


# ---- Full-screen layout (no panel/frame) ----
MARGIN_X = 60

TITLE_Y = 470

META_Y = TITLE_Y + 60

BAR_X = MARGIN_X
BAR_Y = META_Y + 58
BAR_TOTAL_LEN = 1280 - (2 * MARGIN_X)
BAR_RED_LEN = int(BAR_TOTAL_LEN * 0.38)

ICONS_W, ICONS_H = 520, 58
ICONS_X = (1280 - ICONS_W) // 2
ICONS_Y = BAR_Y + 48

MAX_TITLE_WIDTH = 1280 - (2 * MARGIN_X)

GRADIENT_TOP = 360  # y where the bottom gradient starts fading in

_f = "QXJ0aXN0Ym90cw=="


def _decode_f():
    decoded = base64.b64decode(_f).decode("utf-8")
    return f"✦ {decoded} ✦"


def trim_to_width(text: str, font, max_w: int) -> str:

    ellipsis = "…"

    if font.getlength(text) <= max_w:
        return text

    for i in range(len(text) - 1, 0, -1):

        if font.getlength(text[:i] + ellipsis) <= max_w:
            return text[:i] + ellipsis

    return ellipsis


class Thumbnail:

    def __init__(self):

        try:

            self.title_font = ImageFont.truetype(
                "Elevenyts/helpers/Raleway-Bold.ttf",
                54
            )

            self.regular_font = ImageFont.truetype(
                "Elevenyts/helpers/Inter-Light.ttf",
                28
            )

            self.signature_font = ImageFont.truetype(
                "Elevenyts/helpers/Raleway-Bold.ttf",
                34
            )

        except OSError:

            self.title_font = ImageFont.load_default()
            self.regular_font = ImageFont.load_default()
            self.signature_font = ImageFont.load_default()

    async def save_thumb(self, output_path: str, url: str):

        async with aiohttp.ClientSession() as session:

            async with session.get(url) as resp:

                with open(output_path, "wb") as f:
                    f.write(await resp.read())

        return output_path

    async def generate(self, song: Track, size=(1280, 720)) -> str:

        try:

            temp = f"cache/temp_{song.id}.jpg"
            output = f"cache/{song.id}_ultra.png"

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

    def _generate_sync(
        self,
        temp: str,
        output: str,
        song: Track,
        size=(1280, 720)
    ) -> str:

        try:

            with Image.open(temp) as temp_img:
                src = temp_img.convert("RGBA")

                # cover-fit crop so the image fills the full 1280x720
                # frame with no borders/panel, cropping any excess
                src_ratio = src.width / src.height
                dst_ratio = size[0] / size[1]

                if src_ratio > dst_ratio:
                    new_h = size[1]
                    new_w = int(new_h * src_ratio)
                else:
                    new_w = size[0]
                    new_h = int(new_w / src_ratio)

                resized = src.resize((new_w, new_h))

                left = (new_w - size[0]) // 2
                top = (new_h - size[1]) // 2

                bg = resized.crop(
                    (left, top, left + size[0], top + size[1])
                )

            # subtle overall darken/contrast so white text stays readable
            bg = ImageEnhance.Brightness(bg).enhance(0.92)
            bg = ImageEnhance.Contrast(bg).enhance(1.08)

            # bottom gradient so title/bar/icons stay legible over the photo
            gradient = Image.new("RGBA", size, (0, 0, 0, 0))
            grad_draw = ImageDraw.Draw(gradient)

            for y in range(GRADIENT_TOP, size[1]):
                progress = (y - GRADIENT_TOP) / (size[1] - GRADIENT_TOP)
                alpha = int(215 * progress)
                grad_draw.line(
                    [(0, y), (size[0], y)],
                    fill=(0, 0, 0, alpha)
                )

            bg = Image.alpha_composite(bg, gradient)

            # top shadow strip so the signature text stays legible too
            top_shadow = Image.new("RGBA", size, (0, 0, 0, 0))
            ts_draw = ImageDraw.Draw(top_shadow)

            for y in range(0, 110):
                alpha = int(150 * (1 - y / 110))
                ts_draw.line(
                    [(0, y), (size[0], y)],
                    fill=(0, 0, 0, alpha)
                )

            bg = Image.alpha_composite(bg, top_shadow)

            draw = ImageDraw.Draw(bg)

            draw.text(
                (58, 24),
                "Kitty Music",
                fill=(255, 255, 255, 235),
                font=self.signature_font
            )

            clean_title = re.sub(
                r"\W+",
                " ",
                song.title
            ).title()

            final_title = trim_to_width(
                clean_title,
                self.title_font,
                MAX_TITLE_WIDTH
            )

            draw.text(
                (MARGIN_X + 2, TITLE_Y + 2),
                final_title,
                fill=(15, 15, 15),
                font=self.title_font
            )

            draw.text(
                (MARGIN_X + 8, TITLE_Y),
                final_title,
                fill=(255, 255, 255),
                font=self.title_font
            )

            meta_text = (
                f"Now Playing • Kitty Music • "
                f"{song.view_count or 'Unknown Views'}"
            )

            draw.text(
                (MARGIN_X + 8, META_Y),
                meta_text,
                fill=(210, 210, 210),
                font=self.regular_font
            )

            draw.rounded_rectangle(
                (
                    BAR_X,
                    BAR_Y - 5,
                    BAR_X + BAR_TOTAL_LEN,
                    BAR_Y + 5
                ),
                radius=7,
                fill=(70, 70, 70)
            )

            draw.rounded_rectangle(
                (
                    BAR_X,
                    BAR_Y - 5,
                    BAR_X + BAR_RED_LEN,
                    BAR_Y + 5
                ),
                radius=7,
                fill=(255, 35, 35)
            )

            draw.ellipse(
                (
                    BAR_X + BAR_RED_LEN - 9,
                    BAR_Y - 9,
                    BAR_X + BAR_RED_LEN + 9,
                    BAR_Y + 9
                ),
                fill=(255, 35, 35)
            )

            draw.text(
                (BAR_X, BAR_Y + 18),
                "00:00",
                fill=(235, 235, 235),
                font=self.regular_font
            )

            is_live = getattr(song, "is_live", False)

            end_text = "LIVE" if is_live else song.duration

            draw.text(
                (BAR_X + BAR_TOTAL_LEN - 80, BAR_Y + 18),
                end_text,
                fill=(0, 255, 255) if is_live else (235, 235, 235),
                font=self.regular_font
            )

            icons_path = "Elevenyts/helpers/play_icons.png"

            if os.path.isfile(icons_path):

                with Image.open(icons_path) as icons_img:

                    ic = icons_img.resize(
                        (ICONS_W, ICONS_H)
                    ).convert("RGBA")

                    r, g, b, a = ic.split()

                    cyan_ic = Image.merge(
                        "RGBA",
                        (
                            r.point(lambda _: 0),
                            g.point(lambda _: 255),
                            b.point(lambda _: 255),
                            a
                        )
                    )

                    bg.paste(
                        cyan_ic,
                        (ICONS_X, ICONS_Y),
                        cyan_ic
                    )

            bg.save(output)

            try:
                os.remove(temp)

            except OSError:
                pass

            return output

        except Exception:
            return config.DEFAULT_THUMB
