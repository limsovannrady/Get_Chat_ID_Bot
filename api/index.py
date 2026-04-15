"""
Webhook handler for Vercel serverless deployment.

Receives Bot API JSON updates from Telegram and dispatches them
to the existing Pyrogram handlers.

Setup:
  1. Deploy to Vercel
  2. Call: https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://<your-vercel-domain>/api/webhook
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import datetime
import logging
from typing import Optional

from fastapi import FastAPI, Request, Response
from pyrogram import types, enums, Client
from pyrogram.handlers import (
    MessageHandler,
    CallbackQueryHandler,
    InlineQueryHandler,
    BusinessMessageHandler,
    BusinessConnectionHandler,
    ChatMemberUpdatedHandler,
    RawUpdateHandler,
    PreCheckoutQueryHandler,
)
from pyrogram import ContinuePropagation, StopPropagation

from data import config

config.setup_logging()
logger = logging.getLogger(__name__)
settings = config.get_settings()

app = FastAPI()

# ---------------------------------------------------------------------------
# Singleton bot clients — reused across warm invocations
# ---------------------------------------------------------------------------

_bot1: Optional[Client] = None
_bot2: Optional[Client] = None
_initialized = False
_init_lock = asyncio.Lock()


async def _init_bots():
    global _bot1, _bot2, _initialized
    async with _init_lock:
        if _initialized:
            return

        from data import clients
        from tg import handlers as tg_handlers
        from db import repository

        _bot1 = clients.bot_1
        _bot2 = clients.bot_2

        for h in tg_handlers.HANDLERS:
            _bot1.add_handler(h)

        await _bot1.start()
        await _bot2.start()

        for admin_id in settings.admins:
            if not await repository.get_user(tg_id=admin_id):
                await repository.create_user(
                    tg_id=admin_id, name="admin", admin=True, language_code="he"
                )

        _initialized = True


# ---------------------------------------------------------------------------
# Bot API JSON → Pyrogram type converters
# ---------------------------------------------------------------------------


def _parse_user(data: dict) -> Optional[types.User]:
    if not data:
        return None
    return types.User(
        id=data["id"],
        is_bot=data.get("is_bot", False),
        first_name=data.get("first_name", ""),
        last_name=data.get("last_name"),
        username=data.get("username"),
        language_code=data.get("language_code"),
        is_deleted=False,
    )


def _parse_chat(data: dict) -> Optional[types.Chat]:
    if not data:
        return None
    chat_type_map = {
        "private": enums.ChatType.PRIVATE,
        "group": enums.ChatType.GROUP,
        "supergroup": enums.ChatType.SUPERGROUP,
        "channel": enums.ChatType.CHANNEL,
    }
    return types.Chat(
        id=data["id"],
        type=chat_type_map.get(data.get("type", "private"), enums.ChatType.PRIVATE),
        title=data.get("title"),
        username=data.get("username"),
        first_name=data.get("first_name"),
        last_name=data.get("last_name"),
    )


def _parse_forward_origin(data: dict) -> Optional[object]:
    if not data:
        return None
    origin_type = data.get("type")
    date = datetime.datetime.fromtimestamp(data.get("date", 0))
    if origin_type == "user":
        return types.MessageOriginUser(
            date=date,
            sender_user=_parse_user(data.get("sender_user", {})),
        )
    elif origin_type == "hidden_user":
        return types.MessageOriginHiddenUser(
            date=date,
            sender_user_name=data.get("sender_user_name", ""),
        )
    elif origin_type == "chat":
        return types.MessageOriginChat(
            date=date,
            sender_chat=_parse_chat(data.get("sender_chat", {})),
            author_signature=data.get("author_signature"),
        )
    elif origin_type == "channel":
        return types.MessageOriginChannel(
            date=date,
            chat=_parse_chat(data.get("chat", {})),
            message_id=data.get("message_id", 0),
            author_signature=data.get("author_signature"),
        )
    return None


def _parse_message(client: Client, data: dict) -> types.Message:
    msg = types.Message(
        id=data["message_id"],
        date=datetime.datetime.fromtimestamp(data.get("date", 0)),
        chat=_parse_chat(data.get("chat", {})),
        from_user=_parse_user(data.get("from")) if "from" in data else None,
        text=data.get("text"),
        caption=data.get("caption"),
        forward_origin=_parse_forward_origin(data.get("forward_origin")),
        media_group_id=data.get("media_group_id"),
        contact=types.Contact(
            phone_number=data["contact"]["phone_number"],
            first_name=data["contact"].get("first_name", ""),
            last_name=data["contact"].get("last_name"),
            user_id=data["contact"].get("user_id"),
        )
        if "contact" in data
        else None,
    )
    msg._client = client
    return msg


def _parse_callback_query(client: Client, data: dict) -> types.CallbackQuery:
    cq = types.CallbackQuery(
        id=data["id"],
        from_user=_parse_user(data.get("from", {})),
        message=_parse_message(client, data["message"]) if "message" in data else None,
        data=data.get("data", ""),
    )
    cq._client = client
    return cq


def _parse_inline_query(client: Client, data: dict) -> types.InlineQuery:
    iq = types.InlineQuery(
        id=data["id"],
        from_user=_parse_user(data.get("from", {})),
        query=data.get("query", ""),
        offset=data.get("offset", ""),
    )
    iq._client = client
    return iq


# ---------------------------------------------------------------------------
# Handler dispatch
# ---------------------------------------------------------------------------

_HANDLER_TYPE_MAP = {
    "message": MessageHandler,
    "callback_query": CallbackQueryHandler,
    "inline_query": InlineQueryHandler,
}


async def _run_handlers(client: Client, update_obj, update_type: str):
    from tg import handlers as tg_handlers

    expected_cls = _HANDLER_TYPE_MAP.get(update_type)
    if not expected_cls:
        return

    for handler in tg_handlers.HANDLERS:
        if not isinstance(handler, expected_cls):
            continue
        try:
            if await handler.check(client, update_obj):
                await handler.callback(client, update_obj)
                break
        except ContinuePropagation:
            continue
        except StopPropagation:
            break
        except Exception as exc:
            logger.error(f"Handler {handler.callback.__name__} error: {exc}", exc_info=True)
            break


async def _dispatch(client: Client, update: dict):
    if "message" in update:
        msg = _parse_message(client, update["message"])
        await _run_handlers(client, msg, "message")

    elif "edited_message" in update:
        msg = _parse_message(client, update["edited_message"])
        await _run_handlers(client, msg, "message")

    elif "callback_query" in update:
        cq = _parse_callback_query(client, update["callback_query"])
        await _run_handlers(client, cq, "callback_query")

    elif "inline_query" in update:
        iq = _parse_inline_query(client, update["inline_query"])
        await _run_handlers(client, iq, "inline_query")

    else:
        logger.debug(f"Unhandled update type: {list(update.keys())}")


# ---------------------------------------------------------------------------
# FastAPI endpoints
# ---------------------------------------------------------------------------


@app.on_event("startup")
async def on_startup():
    await _init_bots()


@app.post("/api/webhook")
async def webhook(request: Request):
    try:
        update = await request.json()
        logger.debug(f"Received update: {update.get('update_id')}")
        await _init_bots()
        await _dispatch(_bot1, update)
    except Exception as exc:
        logger.error(f"Webhook error: {exc}", exc_info=True)
    return Response(content="OK", status_code=200)


@app.get("/api/webhook")
async def webhook_health():
    return {"status": "ok", "bot": "GetChatID_Bot"}
