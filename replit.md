# Get_Chat_ID_Bot

A Telegram bot that helps users retrieve the ID of any Telegram chat (users, groups, channels, etc.). It supports forwarding messages to get IDs, searching by username, getting IDs from contacts, stories, and business connections.

## Tech Stack

- **Language:** Python 3.12
- **Telegram Framework:** Kurigram (Pyrogram fork)
- **Database:** SQLite via aiosqlite + SQLAlchemy 2.0 (async)
- **Configuration:** Pydantic Settings (reads from environment variables)
- **Task Scheduling:** schedule library

## Project Structure

- `main.py` — Entry point, starts the bot clients and scheduled jobs
- `tg/` — Telegram bot logic (handlers, filters, utilities, get_ids, stats)
- `db/` — Database layer (SQLAlchemy models, repository/CRUD)
- `data/` — Configuration, Pyrogram client initialization, cache
- `locales/` — Internationalization/translation support

## Required Environment Secrets

All set as Replit Secrets:

- `TELEGRAM_API_ID` — Telegram app API ID (from my.telegram.org)
- `TELEGRAM_API_HASH` — Telegram app API Hash (from my.telegram.org)
- `TELEGRAM_BOT_TOKEN` — Primary bot token (from @BotFather)
- `TELEGRAM_BOT_TOKEN_2` — Secondary bot token (from @BotFather)
- `ADMINS` — List or single Telegram user ID(s) for admins (e.g. `[123456789]`)
- `LIMIT_SPAM` — Max requests before spam limiting (e.g. `20`)
- `ADMIN_TO_UPDATE_OF_PAYMENT` — Telegram user ID to notify about payments

## Running

The bot runs as a console workflow: `python main.py`

It does not have a web frontend — it connects directly to the Telegram API.

## Notes

- The `ADMINS` config accepts either a JSON list `[id1, id2]` or a single integer — a validator in `data/config.py` handles both formats.
- Session files (`my_bot.session`, `my_bot_2.session`) are created locally when the bot first connects.
