"""
Run this script once locally to export session strings for Vercel.
The output values must be added to Vercel Environment Variables as:
  BOT_1_SESSION_STRING
  BOT_2_SESSION_STRING
"""

import asyncio
from pyrogram import Client
from data import config

settings = config.get_settings()


async def export():
    print("Exporting session strings from local session files...\n")

    async with Client(
        name="my_bot",
        api_id=settings.telegram_api_id,
        api_hash=settings.telegram_api_hash,
        bot_token=settings.telegram_bot_token,
        workdir=".",
    ) as bot1:
        s1 = await bot1.export_session_string()
        print(f"BOT_1_SESSION_STRING={s1}\n")

    async with Client(
        name="my_bot_2",
        api_id=settings.telegram_api_id,
        api_hash=settings.telegram_api_hash,
        bot_token=settings.telegram_bot_token_2,
        workdir=".",
    ) as bot2:
        s2 = await bot2.export_session_string()
        print(f"BOT_2_SESSION_STRING={s2}\n")

    print("Done! Add these two values to Vercel → Project Settings → Environment Variables.")


if __name__ == "__main__":
    asyncio.run(export())
