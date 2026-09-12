# ==========================================================
# Copyright (c) 2026 ArtistBots
# All Rights Reserved.
#
# Project      : ArtistBots API Telegram Music Bot
# Powered By   : Artist
# Type         : API Based Telegram Music Bot
#
# Bot          : @ArtistApibot
# Channel      : https://telegram.me/artistbots
# GitHub       : https://github.com/elevenyts
#
# ==========================================================

import os
import re
import glob
import time
import yt_dlp
import random
import asyncio
import aiohttp

from dataclasses import replace
from pathlib import Path
from typing import Optional, Union

from pyrogram import enums, types
from py_yt import Playlist, VideosSearch

from Elevenyts import config, logger
from Elevenyts.helpers import Track, utils


class YouTube:
    def __init__(self):
        """Initialize YouTube handler with configuration and caching."""

        self.base = "https://www.youtube.com/watch?v="
        self.cookies = []
        self.checked = False
        self.warned = False

        # ======================================================
        # API CONFIGURATION
        # ======================================================

        self.api_url = config.API_URL
        self.api_key = config.API_KEY
        self.enable_api = config.ENABLE_API
        self.enable_cookies_fallback = config.ENABLE_COOKIES_FALLBACK
        self.api_timeout = config.API_TIMEOUT
        self.api_stream_timeout = config.API_STREAM_TIMEOUT

        # ======================================================
        # YOUTUBE URL REGEX
        # ======================================================

        self.regex = re.compile(
            r"(https?://)?(www\.|m\.|music\.)?"
            r"(youtube\.com/(watch\?v=|shorts/|live/|embed/|playlist\?list=)|youtu\.be/)"
            r"([A-Za-z0-9_-]{11}|PL[A-Za-z0-9_-]+)([&?][^\s]*)?"
        )

        # ======================================================
        # CACHE / SEMAPHORE
        # ======================================================

        self.search_cache = {}
        self._download_semaphore = asyncio.Semaphore(5)
        self._max_video_height = config.VIDEO_MAX_HEIGHT

        # ======================================================
        # STARTUP LOG
        # ======================================================

        logger.info("=" * 55)
        logger.info("📹 YouTube Handler Initialized")

        logger.info(
            f"🎵 API Priority: "
            f"{'ENABLED' if self.enable_api else 'DISABLED'}"
        )

        logger.info(
            f"🔎 [API CONFIG] "
            f"enabled={self.enable_api} "
            f"url_set={bool(self.api_url)} "
            f"key_set={bool(self.api_key)}"
        )

        if self.enable_api:
            if self.api_url:
                logger.info(f"🔗 API URL: {self.api_url}")
            else:
                logger.warning("⚠️ API_URL is not configured!")

            if self.api_key:
                masked_key = (
                    self.api_key[:8] + "..."
                    if len(self.api_key) > 8
                    else "***"
                )
                logger.info(f"🔑 API Key: {masked_key}")
            else:
                logger.warning("⚠️ API_KEY is not configured!")

        logger.info(
            f"🍪 Cookies Fallback: "
            f"{'ENABLED' if self.enable_cookies_fallback else 'DISABLED'}"
        )

        logger.info("=" * 55)

    # ==========================================================
    # FILE FINDER
    # ==========================================================

    def _locate_download_file(
        self,
        video_id: str,
        video: bool = False
    ) -> Optional[str]:

        pattern = f"downloads/{video_id}*"

        candidates = sorted([
            path
            for path in glob.glob(pattern)
            if not path.endswith(
                (".part", ".ytdl", ".info.json", ".temp")
            )
        ])

        video_exts = {
            ".mp4",
            ".mkv",
            ".webm",
            ".mov"
        }

        audio_exts = {
            ".m4a",
            ".webm",
            ".opus",
            ".mp3",
            ".ogg",
            ".wav",
            ".flac"
        }

        if video:
            for path in candidates:
                if os.path.isdir(path):
                    continue

                if Path(path).suffix.lower() in video_exts:
                    return path

        else:
            for path in candidates:
                if os.path.isdir(path):
                    continue

                if Path(path).suffix.lower() in audio_exts:
                    return path

        for path in candidates:
            if os.path.isdir(path):
                continue

            return path

        return None

    # ==========================================================
    # COOKIES
    # ==========================================================

    def get_cookies(self):

        if not self.checked or not self.cookies:

            cookies_dir = "Elevenyts/cookies"
            self.cookies = []

            if os.path.exists(cookies_dir):

                for file in os.listdir(cookies_dir):

                    if file.endswith(".txt"):
                        self.cookies.append(file)

            self.checked = True

        if not self.cookies:

            if not self.warned:
                self.warned = True

                logger.warning(
                    "🍪 Cookies are missing; downloads might fail."
                )

            return None

        cookie_file = (
            f"Elevenyts/cookies/"
            f"{random.choice(self.cookies)}"
        )

        logger.debug(
            f"Using cookie file: {cookie_file}"
        )

        return cookie_file

    async def save_cookies(self, urls: list[str]) -> None:

        logger.info("🍪 Saving cookies from urls...")

        saved_count = 0

        cookies_dir = Path("Elevenyts/cookies")
        cookies_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        for url in urls:

            try:

                path = (
                    cookies_dir /
                    f"cookie{random.randint(10000, 99999)}.txt"
                )

                if "pastebin.com" in url:

                    link = url.replace(
                        "pastebin.com",
                        "pastebin.com/raw"
                    )

                elif "batbin.me" in url:

                    link = url.replace(
                        "batbin.me",
                        "batbin.me/raw"
                    )

                else:
                    link = url

                async with aiohttp.ClientSession() as session:

                    async with session.get(
                        link,
                        timeout=aiohttp.ClientTimeout(
                            total=30
                        )
                    ) as resp:

                        if resp.status != 200:

                            logger.error(
                                f"❌ Cookie download failed: "
                                f"HTTP {resp.status} from {url}"
                            )

                            continue

                        content = await resp.read()

                        if not content or len(content) < 50:

                            logger.error(
                                f"❌ Cookie file empty or invalid "
                                f"from {url}"
                            )

                            continue

                        with open(path, "wb") as fw:
                            fw.write(content)

                        if (
                            path.exists()
                            and path.stat().st_size > 0
                        ):

                            saved_count += 1

                            cookie_filename = path.name

                            if cookie_filename not in self.cookies:
                                self.cookies.append(
                                    cookie_filename
                                )

                            logger.info(
                                f"✅ Saved: "
                                f"{cookie_filename} "
                                f"({len(content)} bytes)"
                            )

            except asyncio.TimeoutError:

                logger.error(
                    f"❌ Cookie download timeout from {url}"
                )

            except Exception as e:

                logger.error(
                    f"❌ Cookie download error from {url}: {e}"
                )

        self.checked = True

        if saved_count > 0:

            logger.info(
                f"✅ Cookies saved successfully! "
                f"({saved_count} file(s))"
            )

        else:

            logger.error(
                "❌ No cookies saved! "
                "Check COOKIE_URL in .env."
            )

    # ==========================================================
    # API REQUEST BUILDER
    # ==========================================================

    def _build_api_request(
        self,
        video_id: str,
        download_type: str
    ):

        host = self.api_url.lower()

        # ------------------------------------------------------
        # ONEGRAB / FALLEN
        # ------------------------------------------------------

        if "onegrab" in host or "fallenapi" in host:

            endpoint = (
                f"{self.api_url}/v1/download"
            )

            params = {
                "url": video_id,
                "type": download_type
            }

            headers = {
                "Authorization":
                    f"Bearer {self.api_key}"
            }

            return endpoint, params, headers

        # ------------------------------------------------------
        # SPARROW
        # ------------------------------------------------------

        if "sparrow" in host:

            endpoint = (
                f"{self.api_url}/download"
            )

            params = {
                "url": video_id,
                "query": video_id,
                "id": video_id,
                "type": download_type,
                "format": download_type,
                "api_key": self.api_key,
                "key": self.api_key,
            }

            headers = {
                "Authorization":
                    f"Bearer {self.api_key}"
            }

            return endpoint, params, headers

        # ------------------------------------------------------
        # GENERIC API
        # ------------------------------------------------------

        endpoint = (
            f"{self.api_url}/download"
        )

        params = {
            "url": video_id,
            "type": download_type,
            "api_key": self.api_key
        }

        headers = {
            "Authorization":
                f"Bearer {self.api_key}"
        }

        return endpoint, params, headers

    # ==========================================================
    # EXTRACT STREAM LINK
    # ==========================================================

    @staticmethod
    def _extract_stream_link(
        payload
    ) -> Optional[str]:

        if not isinstance(payload, dict):
            return None

        keys = (
            "url",
            "download_url",
            "downloadUrl",
            "link",
            "stream_url",
            "streamUrl"
        )

        for key in keys:

            value = payload.get(key)

            if (
                isinstance(value, str)
                and value.startswith("http")
            ):
                return value

        for wrapper in (
            "result",
            "data"
        ):

            nested = payload.get(wrapper)

            if isinstance(nested, dict):

                for key in keys:

                    value = nested.get(key)

                    if (
                        isinstance(value, str)
                        and value.startswith("http")
                    ):
                        return value

        return None

    # ==========================================================
    # SAVE API BINARY
    # ==========================================================

    async def _save_binary_response(
        self,
        response,
        file_path: str,
        download_type: str,
        video_id: str
    ) -> Optional[str]:

        logger.info(
            f"📥 Downloading {download_type} "
            f"via API for {video_id}..."
        )

        content_length = (
            response.headers.get("content-length")
        )

        if content_length:

            file_size_mb = (
                int(content_length)
                / (1024 * 1024)
            )

            logger.info(
                f"📦 File size: "
                f"{file_size_mb:.2f} MB"
            )

        downloaded = 0
        last_log = 0

        with open(file_path, "wb") as f:

            async for chunk in response.content.iter_chunked(
                65536
            ):

                f.write(chunk)
                downloaded += len(chunk)

                if (
                    downloaded - last_log
                    >= 5 * 1024 * 1024
                ):

                    progress_mb = (
                        downloaded
                        / (1024 * 1024)
                    )

                    if content_length:

                        total_mb = (
                            int(content_length)
                            / (1024 * 1024)
                        )

                        percent = (
                            downloaded
                            / int(content_length)
                        ) * 100

                        logger.info(
                            f"📊 Progress: "
                            f"{progress_mb:.1f}/"
                            f"{total_mb:.1f} MB "
                            f"({percent:.1f}%)"
                        )

                    else:

                        logger.info(
                            f"📊 Downloaded: "
                            f"{progress_mb:.1f} MB"
                        )

                    last_log = downloaded

        if (
            os.path.exists(file_path)
            and os.path.getsize(file_path) > 0
        ):

            file_size_mb = (
                os.path.getsize(file_path)
                / (1024 * 1024)
            )

            logger.info(
                f"✅ [API SUCCESS] "
                f"Downloaded: {file_path} "
                f"({file_size_mb:.2f} MB)"
            )

            return file_path

        logger.error(
            "❌ API download failed: "
            "file is empty or not created"
        )

        if os.path.exists(file_path):
            os.remove(file_path)

        return None

    # ==========================================================
    # DOWNLOAD DIRECT STREAM LINK
    # ==========================================================

    async def _download_binary(
        self,
        url: str,
        file_path: str,
        headers: dict,
        download_type: str,
        video_id: str
    ) -> Optional[str]:

        try:

            async with aiohttp.ClientSession() as session:

                async with session.get(
                    url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(
                        total=self.api_stream_timeout
                    )
                ) as response:

                    if response.status != 200:

                        logger.error(
                            f"Stream link returned "
                            f"status {response.status}"
                        )

                        return None

                    return await self._save_binary_response(
                        response,
                        file_path,
                        download_type,
                        video_id
                    )

        except Exception as e:

            logger.error(
                f"❌ Failed to download stream link "
                f"for {video_id}: {e}"
            )

            return None

    # ==========================================================
    # API DOWNLOAD
    # ==========================================================

    async def download_via_api(
        self,
        link: str,
        video: bool = False
    ) -> Optional[str]:

        if not self.enable_api:

            logger.warning(
                "⚠️ [API] API is disabled in config"
            )

            return None

        if not self.api_url:

            logger.error(
                "❌ [API] API_URL is not configured"
            )

            return None

        if not self.api_key:

            logger.error(
                "❌ [API] API_KEY is not configured"
            )

            return None

        # ------------------------------------------------------
        # EXTRACT VIDEO ID
        # ------------------------------------------------------

        if "v=" in link:

            video_id = (
                link.split("v=")[-1]
                .split("&")[0]
            )

        elif "youtu.be" in link:

            video_id = (
                link.split("/")[-1]
                .split("?")[0]
            )

        else:

            video_id = link

        if not video_id or len(video_id) < 3:

            logger.error(
                f"❌ [API] Invalid video ID: {video_id}"
            )

            return None

        download_dir = "downloads"

        os.makedirs(
            download_dir,
            exist_ok=True
        )

        file_ext = (
            ".mp4"
            if video
            else ".mp3"
        )

        file_path = os.path.join(
            download_dir,
            f"{video_id}{file_ext}"
        )

        if os.path.exists(file_path):

            logger.info(
                f"✅ [API] Existing file found: "
                f"{file_path}"
            )

            return file_path

        download_type = (
            "video"
            if video
            else "audio"
        )

        try:

            logger.info(
                f"🚀 [API PRIMARY] Requesting "
                f"{video_id} "
                f"(type: {download_type})"
            )

            endpoint, params, headers = (
                self._build_api_request(
                    video_id,
                    download_type
                )
            )

            logger.info(
                f"🌐 [API] Calling: {endpoint}"
            )

            async with aiohttp.ClientSession() as session:

                async with session.get(
                    endpoint,
                    params=params,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(
                        total=self.api_stream_timeout
                    )
                ) as response:

                    logger.info(
                        f"📡 [API] Response status: "
                        f"{response.status}"
                    )

                    if response.status != 200:

                        try:

                            error_text = (
                                await response.text()
                            )

                            logger.error(
                                f"❌ [API] HTTP "
                                f"{response.status}: "
                                f"{error_text[:500]}"
                            )

                        except Exception:

                            logger.error(
                                f"❌ [API] HTTP "
                                f"{response.status}"
                            )

                        return None

                    content_type = (
                        response.headers.get(
                            "content-type"
                        )
                        or ""
                    ).lower()

                    # --------------------------------------------------
                    # JSON RESPONSE
                    # --------------------------------------------------

                    if "application/json" in content_type:

                        try:

                            payload = await response.json(
                                content_type=None
                            )

                        except Exception as e:

                            logger.error(
                                f"❌ [API] Failed to parse "
                                f"JSON response: {e}"
                            )

                            return None

                        stream_link = (
                            self._extract_stream_link(
                                payload
                            )
                        )

                        if not stream_link:

                            logger.error(
                                "❌ [API] JSON response "
                                "has no download URL"
                            )

                            logger.debug(
                                f"[API] Response: "
                                f"{payload}"
                            )

                            return None

                        logger.info(
                            "🔗 [API] Stream link received"
                        )

                        return await self._download_binary(
                            stream_link,
                            file_path,
                            headers,
                            download_type,
                            video_id
                        )

                    # --------------------------------------------------
                    # RAW BINARY RESPONSE
                    # --------------------------------------------------

                    return await self._save_binary_response(
                        response,
                        file_path,
                        download_type,
                        video_id
                    )

        except asyncio.TimeoutError:

            logger.error(
                f"⏰ [API] Timeout for {video_id} "
                f"after {self.api_stream_timeout}s"
            )

            return None

        except aiohttp.ClientError as e:

            logger.error(
                f"🌐 [API] Client error for "
                f"{video_id}: {e}"
            )

            return None

        except Exception as e:

            logger.error(
                f"❌ [API] Download failed for "
                f"{video_id}: "
                f"{type(e).__name__}: {e}"
            )

            return None

    # ==========================================================
    # COOKIES DOWNLOAD
    # ==========================================================

    async def download_via_cookies(
        self,
        video_id: str,
        video: bool = False
    ) -> Optional[str]:

        if not self.enable_cookies_fallback:

            logger.debug(
                "Cookies fallback is disabled"
            )

            return None

        url = self.base + video_id
        filename_pattern = f"downloads/{video_id}"

        existing_files = [
            f
            for f in glob.glob(
                f"{filename_pattern}.*"
            )
            if not f.endswith(".part")
        ]

        if video:

            video_candidates = [
                f
                for f in existing_files
                if Path(f).suffix.lower()
                in {
                    ".mp4",
                    ".mkv",
                    ".webm",
                    ".mov"
                }
            ]

            if video_candidates:
                return video_candidates[0]

        else:

            audio_candidates = [
                f
                for f in existing_files
                if Path(f).suffix.lower()
                in {
                    ".m4a",
                    ".webm",
                    ".opus",
                    ".mp3",
                    ".ogg",
                    ".wav",
                    ".flac"
                }
            ]

            if audio_candidates:
                return audio_candidates[0]

            container_fallbacks = [
                f
                for f in existing_files
                if Path(f).suffix.lower()
                in {
                    ".mp4",
                    ".mkv",
                    ".mov"
                }
            ]

            if container_fallbacks:
                return container_fallbacks[0]

        downloads_dir = Path("downloads")

        if not downloads_dir.exists():

            try:

                downloads_dir.mkdir(
                    parents=True,
                    exist_ok=True
                )

                logger.info(
                    "📁 Created downloads directory"
                )

            except Exception as e:

                logger.error(
                    f"❌ Cannot create downloads "
                    f"directory: {e}"
                )

                return None

        async with self._download_semaphore:

            cookie = self.get_cookies()

            base_opts = {

                "outtmpl":
                    "downloads/%(id)s.%(ext)s",

                "quiet": False,
                "verbose": True,
                "noplaylist": True,
                "geo_bypass": True,
                "no_warnings": True,
                "overwrites": False,
                "nocheckcertificate": True,
                "continuedl": True,
                "noprogress": True,
                "concurrent_fragment_downloads": 4,
                "http_chunk_size": 524288,
                "socket_timeout": 30,
                "retries": 2,
                "fragment_retries": 2,
                "extractor_retries": 5,
                "sleep_interval_requests": 1,

                "extractor_args": {
                    "youtube": {
                        "player_client": [
                            "mweb",
                            "web"
                        ],
                    },
                    "youtubepot-bgutilscript": {
                        "server_home":
                            "/root/bgutil-ytdlp-pot-provider/server"
                    },
                },
            }

            if video:

                height_filter = ""

                if (
                    self._max_video_height
                    and self._max_video_height > 0
                ):

                    height_filter = (
                        f"[height<="
                        f"{self._max_video_height}]"
                    )

                format_chain = (
                    f"bestvideo[ext=mp4]"
                    f"{height_filter}+"
                    f"bestaudio[ext=m4a]/"
                    f"bestvideo{height_filter}+"
                    f"bestaudio/"
                    f"bestvideo+bestaudio/best"
                )

                ydl_opts = {
                    **base_opts,
                    "format": format_chain,
                    "merge_output_format": "mp4",
                    "postprocessors": [
                        {
                            "key":
                                "FFmpegVideoConvertor",
                            "preferedformat":
                                "mp4",
                        }
                    ],
                }

            else:

                ydl_opts = {
                    **base_opts,
                    "format":
                        "bestaudio[ext=m4a]/"
                        "bestaudio[ext=webm]/"
                        "bestaudio/best",
                    "postprocessors": [],
                }

            ydl_opts_cookie = {
                **ydl_opts,
                "cookiefile": cookie,
            }

            def _download(
                ydl_runtime_opts
            ):

                ydl_instance = None

                try:

                    ydl_instance = (
                        yt_dlp.YoutubeDL(
                            ydl_runtime_opts
                        )
                    )

                    info = (
                        ydl_instance.extract_info(
                            url,
                            download=True
                        )
                    )

                    if not info:

                        logger.error(
                            f"❌ Failed to extract "
                            f"info for {video_id}"
                        )

                        return None

                    time.sleep(0.5)

                    located = (
                        self._locate_download_file(
                            video_id,
                            video=video
                        )
                    )

                    if located:

                        logger.info(
                            f"✅ Download completed: "
                            f"{located}"
                        )

                        return located

                    logger.error(
                        f"❌ Download completed but "
                        f"file not found for: {video_id}"
                    )

                    return None

                except Exception as ex:

                    logger.warning(
                        f"⚠️ Download error for "
                        f"{video_id}: {ex}"
                    )

                    recovered = (
                        self._locate_download_file(
                            video_id,
                            video=video
                        )
                    )

                    if recovered:

                        logger.info(
                            f"✅ Recovered existing "
                            f"file: {recovered}"
                        )

                        return recovered

                    return None

                finally:

                    if ydl_instance:

                        try:
                            ydl_instance.close()
                        except Exception:
                            pass

            logger.info(
                f"🍪 [COOKIES FALLBACK] "
                f"Downloading {video_id} "
                f"with cookies..."
            )

            result = await asyncio.to_thread(
                _download,
                ydl_opts_cookie
            )

            if result:

                logger.info(
                    f"✅ [COOKIES SUCCESS] "
                    f"Downloaded: {result}"
                )

            else:

                logger.warning(
                    f"⚠️ [COOKIES FAILED] "
                    f"Could not download {video_id}"
                )

            return result

    # ==========================================================
    # URL VALIDATION
    # ==========================================================

    def valid(self, url: str) -> bool:

        return bool(
            re.match(
                self.regex,
                url
            )
        )

    # ==========================================================
    # URL EXTRACTOR
    # ==========================================================

    def url(
        self,
        message_1: types.Message
    ) -> Union[str, None]:

        messages = [message_1]
        link = None

        if message_1.reply_to_message:
            messages.append(
                message_1.reply_to_message
            )

        for message in messages:

            text = (
                message.text
                or message.caption
                or ""
            )

            if message.entities:

                for entity in message.entities:

                    if (
                        entity.type
                        == enums.MessageEntityType.URL
                    ):

                        link = text[
                            entity.offset:
                            entity.offset + entity.length
                        ]

                        break

            if message.caption_entities:

                for entity in message.caption_entities:

                    if (
                        entity.type
                        == enums.MessageEntityType.TEXT_LINK
                    ):

                        link = entity.url
                        break

        if link:

            return (
                link
                .split("&si")[0]
                .split("?si")[0]
            )

        return None

    # ==========================================================
    # SEARCH
    # ==========================================================

    async def search(
        self,
        query: str,
        m_id: int
    ) -> Track | None:

        cache_key = query

        current_time = (
            asyncio.get_running_loop().time()
        )

        if cache_key in self.search_cache:

            cached_result, cache_timestamp = (
                self.search_cache[cache_key]
            )

            if (
                current_time - cache_timestamp
                < 600
            ):

                fresh = replace(
                    cached_result
                )

                fresh.message_id = m_id
                fresh.file_path = None
                fresh.user = None
                fresh.time = 0
                fresh.video = False

                return fresh

        try:

            _search = VideosSearch(
                query,
                limit=1
            )

            results = await _search.next()

        except Exception as e:

            logger.warning(
                f"⚠️ YouTube search failed "
                f"for '{query}': {e}"
            )

            return None

        if results and results["result"]:

            data = results["result"][0]

            duration = data.get("duration")

            is_live = (
                duration is None
                or duration == "LIVE"
            )

            track = Track(
                id=data.get("id"),
                channel_name=data.get(
                    "channel",
                    {}
                ).get("name"),
                duration=(
                    duration
                    if not is_live
                    else "LIVE"
                ),
                duration_sec=(
                    0
                    if is_live
                    else utils.to_seconds(
                        duration
                    )
                ),
                message_id=m_id,
                title=data.get(
                    "title"
                )[:25],
                thumbnail=data.get(
                    "thumbnails",
                    [{}]
                )[-1].get(
                    "url"
                ).split("?")[0],
                url=data.get("link"),
                view_count=data.get(
                    "viewCount",
                    {}
                ).get("short"),
                is_live=is_live,
            )

            self.search_cache[cache_key] = (
                track,
                current_time
            )

            if len(self.search_cache) > 100:

                oldest_key = min(
                    self.search_cache.keys(),
                    key=lambda k:
                        self.search_cache[k][1]
                )

                del self.search_cache[
                    oldest_key
                ]

            return replace(track)

        return None

    # ==========================================================
    # PLAYLIST
    # ==========================================================

    async def playlist(
        self,
        limit: int,
        user: str,
        url: str
    ) -> list[Track]:

        try:

            plist = await Playlist.get(url)

            tracks = []

            if (
                not plist
                or "videos" not in plist
                or not plist["videos"]
            ):

                return []

            for data in plist["videos"][:limit]:

                try:

                    thumbnails = data.get(
                        "thumbnails",
                        []
                    )

                    thumbnail_url = ""

                    if thumbnails:

                        thumbnail_url = (
                            thumbnails[-1]
                            .get("url", "")
                            .split("?")[0]
                        )

                    link = data.get(
                        "link",
                        ""
                    )

                    if "&list=" in link:

                        link = link.split(
                            "&list="
                        )[0]

                    track = Track(
                        id=data.get(
                            "id",
                            ""
                        ),
                        channel_name=data.get(
                            "channel",
                            {}
                        ).get(
                            "name",
                            ""
                        ),
                        duration=data.get(
                            "duration",
                            "0:00"
                        ),
                        duration_sec=utils.to_seconds(
                            data.get(
                                "duration",
                                "0:00"
                            )
                        ),
                        title=(
                            data.get(
                                "title",
                                "Unknown"
                            )[:25]
                        ),
                        thumbnail=thumbnail_url,
                        url=link,
                        user=user,
                        view_count="",
                    )

                    tracks.append(track)

                except Exception as e:

                    logger.warning(
                        f"Failed to parse "
                        f"playlist item: {e}"
                    )

                    continue

            return tracks

        except KeyError:

            raise Exception(
                "Failed to parse playlist. "
                "YouTube may have changed "
                "their structure."
            )

        except Exception as e:

            logger.error(
                f"Playlist extraction error: {e}"
            )

            raise

    # ==========================================================
    # MAIN DOWNLOAD
    # ==========================================================

    async def download(
        self,
        video_id: str,
        is_live: bool = False,
        video: bool = False
    ) -> Optional[str]:

        # ======================================================
        # LIVE STREAM
        # ======================================================

        if is_live:

            logger.info(
                f"🔴 Live stream detected for "
                f"{video_id}, using cookies method..."
            )

            cookie = self.get_cookies()

            ydl_opts = {

                "quiet": True,
                "no_warnings": True,
                "cookiefile": cookie,
                "format": "bestaudio/best",
                "noplaylist": True,
                "socket_timeout": 20,
                "extractor_retries": 5,
                "sleep_interval_requests": 1,

                "extractor_args": {
                    "youtube": {
                        "player_client": [
                            "mweb",
                            "web"
                        ],
                    },
                    "youtubepot-bgutilscript": {
                        "server_home":
                            "/root/bgutil-ytdlp-pot-provider/server"
                    },
                },
            }

            def _extract_url():

                with yt_dlp.YoutubeDL(
                    ydl_opts
                ) as ydl:

                    try:

                        info = ydl.extract_info(
                            self.base + video_id,
                            download=False
                        )

                        if not info:
                            return None

                        direct = info.get("url")

                        if direct:
                            return direct

                        for fmt in info.get(
                            "formats",
                            []
                        ):

                            if (
                                fmt.get("acodec")
                                != "none"
                                and fmt.get("url")
                            ):

                                return fmt["url"]

                        return info.get(
                            "manifest_url"
                        )

                    except Exception as ex:

                        logger.error(
                            f"Live stream extraction "
                            f"failed: {ex}"
                        )

                        return None

            try:

                stream_url = await asyncio.wait_for(
                    asyncio.to_thread(
                        _extract_url
                    ),
                    timeout=35
                )

                if stream_url:

                    logger.info(
                        f"✅ Live stream URL "
                        f"extracted for {video_id}"
                    )

                return stream_url

            except asyncio.TimeoutError:

                logger.error(
                    f"Live stream URL extraction "
                    f"timed out for {video_id}"
                )

                return None

        # ======================================================
        # NORMAL DOWNLOAD
        # API FIRST
        # ======================================================

        logger.info(
            f"🔎 [API CHECK] "
            f"enabled={self.enable_api} "
            f"url_set={bool(self.api_url)} "
            f"key_set={bool(self.api_key)} "
            f"is_live={is_live}"
        )

        # ------------------------------------------------------
        # ALWAYS ENTER API HANDLER
        # ------------------------------------------------------

        logger.info(
            f"🎯 [PRIORITY 1] Trying API "
            f"download for {video_id}"
        )

        result = await self.download_via_api(
            self.base + video_id,
            video=video
        )

        if result:

            logger.info(
                f"✅ [SUCCESS] Downloaded "
                f"via API: {video_id}"
            )

            return result

        logger.warning(
            f"⚠️ [API FAILED] {video_id}, "
            f"trying cookies fallback..."
        )

        # ======================================================
        # COOKIES FALLBACK
        # ======================================================

                if self.enable_cookies_fallback:

            logger.info(
                f"🍪 [PRIORITY 2] Trying cookies "
                f"download for {video_id}"
            )

            result = await self.download_via_cookies(
                video_id,
                video=video
            )

            if result:
                logger.info(
                    f"✅ [SUCCESS] Downloaded "
                    f"via cookies: {video_id}"
                )

                return result

            logger.error(
                f"❌ [COOKIES FAILED] "
                f"Could not download {video_id}"
            )

        # ======================================================
        # EVERYTHING FAILED
        # ======================================================

        logger.error(
            f"❌ [FAILED] All download methods "
            f"failed for {video_id}"
        )

        return None
