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

Example `docker-compose.yml` file in repo. Environment variables required:
* *TELEGRAM_TOKEN*: Telegram bot access token
* *TELEGRAM_CHAT_ID*: Telegram chat group ID (bot must have been invited to this chat already)
* *HOUSE_NUMBER*: House number to check bins for
* *HOUSE_POSTCODE*: Postcode to check bins for
* *JSON_OUTPUT_PATH* (optional): File path to write collection data as JSON. If set, a JSON file with all future collection dates is written after each run. Useful for sharing data with other apps via a Docker volume. If unset, no JSON file is written.

Start (in directory): `docker-compose -p bins up -d`

### JSON Output
When `JSON_OUTPUT_PATH` is set, the app writes a JSON file after each run containing all future bin collection dates. The example `docker-compose.yml` uses a named volume (`bin-data`) mounted at `/data/output` for this purpose. To consume from another container, mount the same volume:
```yaml
volumes:
  bin-data:
    external: true

services:
  my-app:
    volumes:
      - bin-data:/path/in/my/container:ro
```

### Future Todos
* Support multiple addresses/bots/chats
* Support email or other notification methods
* Tests