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
import asyncio
import aiohttp

from PIL import (
    Image,
    ImageDraw,
    ImageEnhance,
    ImageFont
)

from Elevenyts import config
from Elevenyts.helpers import Track


SIZE = (1280, 720)

BRAND_TEXT = "Kitty X Music !!"
BRAND_X = 45
BRAND_Y = 35


def _load_font(paths, size):

    for p in paths:

        try:
            return ImageFont.truetype(p, size)

        except OSError:
            continue

    return ImageFont.load_default()


class Thumbnail:

    def __init__(self):

        # bold + a slightly condensed look to fake a "stylish" feel
        # since fancy unicode script characters aren't renderable
        # without a dedicated math-symbol font
        self.brand_font = _load_font(
            [
                "Elevenyts/helpers/Raleway-BoldItalic.ttf",
                "Elevenyts/helpers/Raleway-Bold.ttf",
            ],
            26
        )

    async def save_thumb(self, output_path: str, url: str):

        async with aiohttp.ClientSession() as session:

            async with session.get(url) as resp:

                with open(output_path, "wb") as f:
                    f.write(await resp.read())

        return output_path

    async def generate(self, song: Track, size=SIZE) -> str:

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
        size=SIZE
    ) -> str:

        try:

            with Image.open(temp) as temp_img:
                src = temp_img.convert("RGBA")

                # cover-fit crop: fills the full 1280x720 frame,
                # no border/panel, no gradient, no extra UI
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
                ).convert("RGBA")

            draw = ImageDraw.Draw(bg)

            # subtle drop shadow + white text for the bot name
            # (no background box/strip, just a soft text shadow)
            draw.text(
                (BRAND_X + 2, BRAND_Y + 2),
                BRAND_TEXT,
                fill=(0, 0, 0, 160),
                font=self.brand_font
            )
            draw.text(
                (BRAND_X, BRAND_Y),
                BRAND_TEXT,
                fill=(255, 255, 255, 255),
                font=self.brand_font
            )

            bg.convert("RGB").save(output)

            try:
                os.remove(temp)

            except OSError:
                pass

            return output

        except Exception:
            return config.DEFAULT_THUMB
