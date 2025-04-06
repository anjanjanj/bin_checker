import logging
import telegram

logger = logging.getLogger()


class TelegramClient:
    """
    Used to send Telegram messages via a specified bot token and chat id.
    """

    def __init__(self, api_token: str) -> None:
        self.token = api_token
        self.bot = None

    async def create(self) -> telegram.User:
        self.bot = telegram.Bot(token=self.token)
        user = await self.bot.get_me()
        logger.info(f"Telegram bot connection: {user}")
        return user

    async def send_message(self, chat_id: str, text: str) -> telegram.Message:
        if self.bot is None:
            raise RuntimeError("Bot has not been initialised via create()")

        msg = await self.bot.send_message(chat_id=chat_id, text=text)
        logger.debug(f"Sent Telegram to {chat_id}: {text}")
        return msg
