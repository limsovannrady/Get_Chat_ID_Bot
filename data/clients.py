import logging
import os
from pyrogram import Client

from data import config

_logger = logging.getLogger(__name__)

settings = config.get_settings()

_VERCEL = os.getenv("VERCEL")
_WORKDIR = "/tmp" if _VERCEL else "."

_BOT1_SESSION = os.getenv("BOT_1_SESSION_STRING")
_BOT2_SESSION = os.getenv("BOT_2_SESSION_STRING")

if _VERCEL and _BOT1_SESSION:
    bot_1 = Client(
        name="my_bot",
        api_id=settings.telegram_api_id,
        api_hash=settings.telegram_api_hash,
        bot_token=settings.telegram_bot_token,
        session_string=_BOT1_SESSION,
    )
else:
    bot_1 = Client(
        name="my_bot",
        api_id=settings.telegram_api_id,
        api_hash=settings.telegram_api_hash,
        bot_token=settings.telegram_bot_token,
        workdir=_WORKDIR,
    )

if _VERCEL and _BOT2_SESSION:
    bot_2 = Client(
        name="my_bot_2",
        api_id=settings.telegram_api_id,
        api_hash=settings.telegram_api_hash,
        bot_token=settings.telegram_bot_token_2,
        session_string=_BOT2_SESSION,
    )
else:
    bot_2 = Client(
        name="my_bot_2",
        api_id=settings.telegram_api_id,
        api_hash=settings.telegram_api_hash,
        bot_token=settings.telegram_bot_token_2,
        workdir=_WORKDIR,
    )
