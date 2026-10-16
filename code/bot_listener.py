"""Answer on-demand collection queries independently of scheduled reminders."""

import asyncio
import logging
from datetime import date, datetime
from os import getenv
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, filters

from north_herts_bins import get_north_herts_bins

logger = logging.getLogger(__name__)
LONDON = ZoneInfo("Europe/London")


def format_collections(collections: list[tuple[datetime, str]], today: date) -> str:
    """Show the next collection on or after today for each bin type."""
    next_dates: dict[str, date] = {}
    for collection, bin_type in collections:
        collection_date = collection.date()
        if collection_date < today:
            continue
        if bin_type not in next_dates or collection_date < next_dates[bin_type]:
            next_dates[bin_type] = collection_date

    if not next_dates:
        return "No upcoming bin collections were returned by the council."

    lines = ["🗑️ Next bin collections:"]
    for bin_type, collection_date in sorted(
        next_dates.items(), key=lambda item: (item[1], item[0])
    ):
        lines.append(f"{bin_type}: {collection_date:%A %d %B %Y}")
    return "\n".join(lines)


async def bins_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message is None:
        return

    try:
        collections = await asyncio.to_thread(get_north_herts_bins)
    except Exception:
        logger.exception("Could not fetch bin collections")
        await message.reply_text(
            "Collection details are temporarily unavailable. Please try /bins again later."
        )
        return

    today = datetime.now(LONDON).date()
    await message.reply_text(format_collections(collections, today))


async def log_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Telegram listener error", exc_info=context.error)


def create_application() -> Application:
    token = getenv("TELEGRAM_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_TOKEN environment variable is not set.")
    try:
        chat_id = int(getenv("TELEGRAM_CHAT_ID", ""))
    except ValueError as exc:
        raise ValueError("TELEGRAM_CHAT_ID must be a numeric Telegram chat ID.") from exc

    application = Application.builder().token(token).build()
    application.add_handler(
        CommandHandler("bins", bins_command, filters=filters.Chat(chat_id=chat_id))
    )
    application.add_error_handler(log_error)
    return application


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)-12s %(levelname)-8s %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    create_application().run_polling(
        allowed_updates=["message"], drop_pending_updates=True
    )


if __name__ == "__main__":
    main()
