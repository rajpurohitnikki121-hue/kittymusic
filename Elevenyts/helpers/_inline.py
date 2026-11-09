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
from pyrogram import types
from pyrogram.enums import ButtonStyle

from Elevenyts import app, config, lang
from Elevenyts.helpers import _autoplay as autoplay


# ----------------------------------------------------------
# FONT
# Every button label goes through _f(). It turns normal English
# letters/digits into bold sans-serif letters (clear and readable).
# To change the font for ALL buttons, only edit this one function.
# ----------------------------------------------------------
def _build_font_map() -> dict:
    mapping = {}
    for i in range(26):
        mapping[chr(65 + i)] = chr(0x1D5D4 + i)  # A-Z
        mapping[chr(97 + i)] = chr(0x1D5EE + i)  # a-z
    for i in range(10):
        mapping[chr(48 + i)] = chr(0x1D7EC + i)  # 0-9
    return mapping


_FONT = _build_font_map()


# Light sans-serif font used for the bracket-style buttons: 𝖠𝗎𝗍𝗈 𝖢𝗅𝗈𝗌𝖾
def _build_light_map() -> dict:
    mapping = {}
    for i in range(26):
        mapping[chr(65 + i)] = chr(0x1D5A0 + i)  # A-Z
        mapping[chr(97 + i)] = chr(0x1D5BA + i)  # a-z
    for i in range(10):
        mapping[chr(48 + i)] = chr(0x1D7E2 + i)  # 0-9
    return mapping


_LIGHT = _build_light_map()


def _g(text: str) -> str:
    return "".join(_LIGHT.get(ch, ch) for ch in text)


def _b(text: str) -> str:
    """Bracket style label:  \u231C 𝖮𝗐𝗇𝖾𝗋 \u231F"""
    return f"\u231C {_g(text)} \u231F"


def _f(text: str) -> str:
    return "".join(_FONT.get(ch, ch) for ch in text)


# ----------------------------------------------------------
# SYMBOLS (plain text symbols, not emoji)
# ----------------------------------------------------------
S_GEM = "\u27E1"      # ⟡
S_STAR = "\u2726"     # ✦
S_DIAMOND = "\u2756"  # ❖
S_FLOWER = "\u2740"   # ❀
S_MOON = "\u263E"     # ☾
S_ON = "\u25C9"       # ◉
S_OFF = "\u25CB"      # ○
S_PLAY = "\u25B7"     # ▷
S_DOT = "\u00B7"      # ·
S_BACK = "\u00AB"     # «

# Player button labels (exact Ishq Music style)
BTN_AUTOPLAY_ON = _g("Auto") + " " + _b("On")
BTN_AUTOPLAY_OFF = _g("Auto") + " " + _b("Off")
BTN_CLOSE = "\u2A2F " + _g("Close")


# ----------------------------------------------------------
# PREMIUM (custom) EMOJI for the DM start buttons.
# Paste the custom emoji ID (a long number) between the quotes.
# Left empty "" = a normal symbol is shown instead.
# NOTE: Telegram only shows these if the BOT OWNER has Telegram Premium.
# ----------------------------------------------------------
START_ICONS = {
    "commands": "",
    "support": "",
    "channel": "",
    "owner": "",
    "addme": "",
}


class Inline:
    def __init__(self):
        self.ikm = types.InlineKeyboardMarkup
        self.ikb = types.InlineKeyboardButton

    def cancel_dl(self, text) -> types.InlineKeyboardMarkup:
        return self.ikm([[self.ikb(text=text, callback_data=f"cancel_dl", style=ButtonStyle.PRIMARY)]])

    def _autoplay_button(self, chat_id: int) -> types.InlineKeyboardButton:
        # Label shows ON/OFF in words. No colour.
        on = autoplay.is_enabled(chat_id)
        return self.ikb(
            text=BTN_AUTOPLAY_ON if on else BTN_AUTOPLAY_OFF,
            callback_data=f"controls autoplay {chat_id}",
        )

    def controls(
        self,
        chat_id: int,
        status: str = None,
        timer: str = None,
        remove: bool = False,
    ) -> types.InlineKeyboardMarkup:
        keyboard = []
        if status:
            keyboard.append(
                [self.ikb(
                    text=status, callback_data=f"controls status {chat_id}",
                    style=ButtonStyle.PRIMARY)]
            )
        elif timer:
            keyboard.append(
                [self.ikb(
                    text=timer, callback_data=f"controls status {chat_id}",
                    style=ButtonStyle.PRIMARY)]
            )

        if not remove:
            # Row 1: Play | Pause | Skip | Repeat (same callbacks as before)
            keyboard.append(
                [
                    self.ikb(
                        text="\u25B7", callback_data=f"controls resume {chat_id}"),
                    self.ikb(
                        text="\u2161", callback_data=f"controls pause {chat_id}"),
                    self.ikb(
                        text="\u00BB", callback_data=f"controls skip {chat_id}"),
                    self.ikb(
                        text="\u27F3", callback_data=f"controls replay {chat_id}"),
                ]
            )
            # Row 2: Autoplay (left) | Close (right), side by side
            keyboard.append(
                [
                    self._autoplay_button(chat_id),
                    self.ikb(
                        text=BTN_CLOSE,
                        callback_data=f"controls close {chat_id}",
                    ),
                ]
            )
        return self.ikm(keyboard)

    def help_markup(
        self, _lang: dict, back: bool = False
    ) -> types.InlineKeyboardMarkup:
        """Create help menu with categorized buttons."""
        if back:
            rows = [
                [
                    self.ikb(text=_b("Back"), callback_data="help_main", style=ButtonStyle.PRIMARY),
                ]
            ]
        else:
            # Help menu with categorized buttons (3 per row)
            rows = [
                [
                    self.ikb(text=_b("Admins"), callback_data="help_admins", style=ButtonStyle.PRIMARY),
                    self.ikb(text=_b("Auth"), callback_data="help_auth", style=ButtonStyle.PRIMARY),
                    self.ikb(text=_b("Broadcast"), callback_data="help_broadcast", style=ButtonStyle.PRIMARY),
                ],
                [
                    self.ikb(text=_b("BL-Chat"), callback_data="help_blchat", style=ButtonStyle.PRIMARY),
                    self.ikb(text=_b("BL-User"), callback_data="help_bluser", style=ButtonStyle.PRIMARY),
                    self.ikb(text=_b("G-Ban"), callback_data="help_gban", style=ButtonStyle.PRIMARY),
                ],
                [
                    self.ikb(text=_b("Loop"), callback_data="help_loop", style=ButtonStyle.PRIMARY),
                    self.ikb(text=_b("Play"), callback_data="help_play", style=ButtonStyle.PRIMARY),
                    self.ikb(text=_b("Queue"), callback_data="help_queue", style=ButtonStyle.PRIMARY),
                ],
                [
                    self.ikb(text=_b("Seek"), callback_data="help_seek", style=ButtonStyle.PRIMARY),
                    self.ikb(text=_b("Shuffle"), callback_data="help_shuffle", style=ButtonStyle.PRIMARY),
                    self.ikb(text=_b("Ping"), callback_data="help_ping", style=ButtonStyle.PRIMARY),
                ],
                [
                    self.ikb(text=_b("Stats"), callback_data="help_stats", style=ButtonStyle.PRIMARY),
                    self.ikb(text=_b("Sudo"), callback_data="help_sudo", style=ButtonStyle.PRIMARY),
                    self.ikb(text=_b("Maintenance"), callback_data="help_maintenance", style=ButtonStyle.PRIMARY),
                ],
                [
                    self.ikb(text=_b("Tag All"), callback_data="tagall_info", style=ButtonStyle.PRIMARY),
                    self.ikb(text=_b("Autoplay"), callback_data="autoplay_info", style=ButtonStyle.PRIMARY),
                ],
                [
                    self.ikb(text=_b("Back"), callback_data="start", style=ButtonStyle.PRIMARY),
                ]
            ]
        return self.ikm(rows)

    def ping_markup(self, text: str) -> types.InlineKeyboardMarkup:
        return self.ikm([
            [
                self.ikb(text=f"{S_FLOWER} {_f('Channel')}", url=config.UPDATE_CHANNEL),
                self.ikb(text=f"{S_STAR} {_f('Support')}", url=config.SUPPORT_CHANNEL),
            ],
            [
                self.ikb(
                    text=f"{S_GEM} {_f('Add Me To Your Group')} {S_GEM}",
                    url=f"https://t.me/{app.username}?startgroup=true",
                ),
            ]
        ])

    def play_queued(
        self, chat_id: int, item_id: str, _text: str
    ) -> types.InlineKeyboardMarkup:
        # Under "Added to queue": only one blue Play Now button.
        return self.ikm(
            [
                [
                    self.ikb(
                        text=f"{S_PLAY} {_f('Play Now')}",
                        callback_data=f"controls force {chat_id} {item_id}",
                        style=ButtonStyle.PRIMARY,
                    )
                ]
            ]
        )

    def queue_markup(
        self,
        chat_id: int,
        _text: str = "",
        playing: bool = True,
        upcoming: list = None,
    ):
        """Buttons under /queue.

        When `upcoming` (list of queued songs) is given, one "Play Now"
        button is made per song and nothing else. Without it, the old
        single pause/resume button is returned (kept for compatibility).
        """
        if upcoming is not None:
            buttons = []
            for idx, item in enumerate(upcoming, start=1):
                item_id = getattr(item, "id", None)
                if not item_id:
                    continue
                data = f"controls force {chat_id} {item_id}"
                if len(data.encode()) > 64:  # Telegram callback_data limit
                    continue
                buttons.append(
                    self.ikb(
                        text=f"{S_PLAY} {_f('Play Now')} {_f(str(idx))}",
                        callback_data=data,
                        style=ButtonStyle.PRIMARY,
                    )
                )
            if not buttons:
                return None
            rows = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
            return self.ikm(rows)

        _action = "pause" if playing else "resume"
        return self.ikm(
            [[self.ikb(
                text=_text, callback_data=f"controls {_action} {chat_id} q", style=ButtonStyle.SUCCESS)]]
        )

    def settings_markup(
        self, lang: dict, admin_only: bool, language: str, chat_id: int
    ) -> types.InlineKeyboardMarkup:
        return self.ikm(
            [
                [
                    self.ikb(
                        text=lang["play_mode"] + " ➜",
                        callback_data=f"controls status {chat_id}",
                        style=ButtonStyle.PRIMARY,
                    ),
                    self.ikb(text=admin_only, callback_data="playmode", style=ButtonStyle.SUCCESS),
                ],
            ]
        )

    def _start_btn(self, label: str, symbol: str, key: str, **kw):
        """Button with a premium emoji if its ID is set (and the installed
        pyrogram supports it), otherwise with a plain symbol."""
        icon = START_ICONS.get(key)
        if icon:
            try:
                return self.ikb(text=label, icon_custom_emoji_id=icon, **kw)
            except TypeError:
                pass  # old pyrogram without custom-emoji buttons
        return self.ikb(text=f"{symbol} {label}" if symbol else label, **kw)

    def start_key(
        self, lang: dict, private: bool = False
    ) -> types.InlineKeyboardMarkup:
        # Layout + bold serif font + blue buttons, like the reference bot.
        P = ButtonStyle.PRIMARY
        # Telegram rejects tg://user?id= links on buttons unless the bot has
        # already met that user (the whole /start then fails). So the Owner
        # button is shown only when a normal https://t.me/<username> link
        # is known.
        owner_url = getattr(app, "owner_url", "") or ""
        second_row = [
            self._start_btn(_b("Channel"), "", "channel",
                            url=config.UPDATE_CHANNEL, style=P),
        ]
        if owner_url.startswith("https://"):
            second_row.append(
                self._start_btn(_b("Owner"), "", "owner",
                                url=owner_url, style=P))
        rows = [
            [
                self._start_btn(_b("Commands"), "", "commands",
                                callback_data="help", style=P),
                self._start_btn(_b("Support"), "", "support",
                                url=config.SUPPORT_CHANNEL, style=P),
            ],
            second_row,
            [
                self._start_btn(_b("Add Me"), "", "addme",
                                url=f"https://t.me/{app.username}?startgroup=true",
                                style=P),
            ],
        ]
        return self.ikm(rows)

    def yt_key(self, link: str) -> types.InlineKeyboardMarkup:
        return self.ikm(
            [
                [
                    self.ikb(text=f"{S_DIAMOND} {_f('Copy Link')}", copy_text=link),
                    self.ikb(text=f"{S_PLAY} {_f('Open In YouTube')}", url=link),
                ],
            ]
        )
