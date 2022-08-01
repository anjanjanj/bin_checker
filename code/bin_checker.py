import logging
from datetime import datetime, timedelta
from os import getenv
from north_herts_bins import get_north_herts_bins
from telegram_client import TelegramClient

logger = logging.getLogger()


class BinChecker:
    def __init__(self, days_from_now: int) -> None:
        """
        days_from_now : int
            the number of days in advance (from today) that we
            should send out notifications for
        """
        self.last_update = datetime.min
        self.days_from_now = days_from_now

        # create Telegram client
        self.telegram = TelegramClient(api_token=getenv('TELEGRAM_TOKEN'))

        self.telegram_chat_id = getenv('TELEGRAM_CHAT_ID')

    def run(self) -> None:
        house_number = getenv('HOUSE_NUMBER')
        house_postcode = getenv('HOUSE_POSTCODE')
        logging.info('Getting bin data [%s, %s]', house_number, house_postcode)
        data = get_north_herts_bins(house_number, house_postcode)

        # get the next date in the list
        dates = [e[0] for e in data]
        min_date = min(dates)
        logging.info('Next date found: %s', min_date)

        now = datetime.now()

        # send a notification if:
        # 1. the next collection date hasn't already been sent out previously
        # 2. the next collection date is within our notification days threshold
        if ((min_date > self.last_update) and
                (now <= min_date <= now + timedelta(days=self.days_from_now))):

            logger.info('New collections found within time range, ' +
                        'sending update')

            # get relevant collections
            collection_list = [e[1] for e in list(
                filter(lambda c: c[0] == min_date, data))]

            # build notification message: date followed by list of collections
            message = f"🗑️ {min_date.strftime('%d %B')} is BIN DAY! 🗑️"
            for c in collection_list:
                message += f"\n{c}"

            self.telegram.send_message(chat_id=self.telegram_chat_id,
                                       text=message)

            # update last collection sent time so this date won't be sent again
            self.last_update = min_date
        else:
            logger.info('No new collections found within time range')
