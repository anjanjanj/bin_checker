import logging
import telegram

logger = logging.getLogger()

class TelegramClient:
    def __init__(self, api_token: str) -> None:
        self.token = api_token
        self.bot = telegram.Bot(token=self.token)
        logger.info(f"Telegram bot connection: {self.bot.get_me()}")

    def send_message(self, chat_id: str, text: str) -> None:
        self.bot.send_message(chat_id=chat_id, text=text)
        logger.debug(f"Sent Telegram to {chat_id}: {text}")