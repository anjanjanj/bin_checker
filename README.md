## Bin Checker
A small Python app to check upcoming North Hertfordshire (UK) bin collections for a given address via the Cloud9 Technologies API and send a message to a Telegram group with details.

Because I always forget when bin day is and which bins it is.

*(North Herts addresses only!)*

![example](https://raw.githubusercontent.com/anjanjanj/bin_checker/master/.github/message.png)

### Deploy (via Docker)
Build image: `docker build -t bins .`

For ARM64 (e.g. Raspberry Pi): `docker build --platform linux/arm64 -t bins .`

Image export/import:
```
docker save bins > bins.tar
docker load < bins.tar
```

Create bot with Telegram: https://core.telegram.org/bots

Copy `docker-compose.example.yml` to `docker-compose.yml` and replace the example
environment values in both services. Environment variables required:
* *TELEGRAM_TOKEN*: Telegram bot access token
* *TELEGRAM_CHAT_ID*: Telegram chat group ID (bot must have been invited to this chat already)
* *HOUSE_NUMBER*: House number to check bins for
* *HOUSE_POSTCODE*: Postcode to check bins for

Start (in directory): `docker-compose -p bins up -d`

### Query upcoming collections

Send `/bins` in the configured Telegram chat to see the next collection date for
each bin type. In a group, use `/bins@YourBotUsername` to address the bot explicitly.
Each request fetches fresh council data, includes collections due today in
Europe/London, and lists one line per bin type in date order.

The `bins-listener` service runs continuously alongside the existing `bins`
reminder service, using the same image and dependencies. It uses long polling,
so no public endpoint or exposed port is needed. Keep the four environment values
the same in both services and run only one listener per bot token.

For an existing deployment, rebuild the `bins` image and add `bins-listener` from
the example Compose file before running the start command again. The existing
service continues checking for reminders every eight hours; queries do not change
the one-day notice or its saved reminder state.

The listener answers only in `TELEGRAM_CHAT_ID`. Requests queued while it is
offline are discarded on startup; send `/bins` again after it restarts.

### Tests

With `requirements.txt` installed, run `python -m unittest discover -s tests`.
The tests mock council and Telegram calls and do not send real messages.

### Future Todos
* Support multiple addresses/bots/chats
* Support email or other notification methods
