## Bin Checker
A small Python app to poll the North Hertfordshire (UK) bin collection website for a given address and send a message to a Telegram group with details of any upcoming bin collections.

Because I always forget when bin day is and which bins it is.

*(North Herts addresses only!)*

![example](https://raw.githubusercontent.com/anjanjanj/bin_checker/master/.github/message.png)

### Deploy (via Docker)
Build image: `docker build -t bins .`

Image export/import:
```
docker save bins > bins.tar
docker load < bins.tar
```

Create bot with Telegram: https://core.telegram.org/bots

Example `docker-compose.yml` file in repo. Environment variables required:
* *TELEGRAM_TOKEN*: Telegram bot access token
* *TELEGRAM_CHAT_ID*: Telegram chat group ID (bot must have been invited to this chat already)
* *HOUSE_NUMBER*: House number to check bins for
* *HOUSE_POSTCODE*: Postcode to check bins for

Start (in directory): `docker-compose -p bins up -d`

### Future Todos
* Support multiple addresses/bots/chats
* Support email or other notification methods
* Tests