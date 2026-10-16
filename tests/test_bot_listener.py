import asyncio
import json
import sys
import threading
import unittest
from contextlib import chdir
from datetime import date, datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))

import bot_listener
from bin_checker import BinChecker
from telegram import Message, Update


CHAT_ID = -123456789
BOT_USERNAME = "BinsTestBot"
TODAY = date(2026, 10, 16)


class FormatCollectionsTests(unittest.TestCase):
    def test_selects_earliest_per_type_and_sorts_unsorted_duplicates(self):
        collections = [
            (datetime(2026, 10, 30), "Food"),
            (datetime(2026, 10, 20), "Recycling"),
            (datetime(2026, 10, 18), "General waste"),
            (datetime(2026, 10, 17), "Food"),
            (datetime(2026, 10, 17), "Food"),
        ]
        self.assertEqual(
            bot_listener.format_collections(collections, TODAY),
            "🗑️ Next bin collections:\n"
            "Food: Saturday 17 October 2026\n"
            "General waste: Sunday 18 October 2026\n"
            "Recycling: Tuesday 20 October 2026",
        )

    def test_keeps_different_bin_types_on_the_same_day(self):
        collections = [
            (datetime(2026, 10, 17), "Recycling"),
            (datetime(2026, 10, 17), "Food"),
        ]
        self.assertEqual(
            bot_listener.format_collections(collections, TODAY),
            "🗑️ Next bin collections:\n"
            "Food: Saturday 17 October 2026\n"
            "Recycling: Saturday 17 October 2026",
        )

    def test_includes_today_and_excludes_past_dates(self):
        collections = [
            (datetime(2026, 10, 15), "Food"),
            (datetime(2026, 10, 16), "Food"),
            (datetime(2026, 10, 17), "Food"),
            (datetime(2026, 10, 14), "Recycling"),
        ]
        self.assertEqual(
            bot_listener.format_collections(collections, TODAY),
            "🗑️ Next bin collections:\nFood: Friday 16 October 2026",
        )

    def test_no_upcoming_collections(self):
        for collections in ([], [(datetime(2026, 10, 15), "Food")]):
            with self.subTest(collections=collections):
                self.assertEqual(
                    bot_listener.format_collections(collections, TODAY),
                    "No upcoming bin collections were returned by the council.",
                )


class ListenerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.enterContext(patch.dict("os.environ", {
            "TELEGRAM_TOKEN": "123456:test-token",
            "TELEGRAM_CHAT_ID": str(CHAT_ID),
        }))
        self.clock = self.enterContext(patch("bot_listener.datetime", wraps=datetime))
        self.clock.now.return_value = datetime(2026, 10, 16, 12, tzinfo=bot_listener.LONDON)
        self.fetch = self.enterContext(patch(
            "bot_listener.get_north_herts_bins",
            return_value=[(datetime(2026, 10, 17), "Food")],
        ))
        self.reply = self.enterContext(patch.object(Message, "reply_text", new_callable=AsyncMock))
        self.pending_updates = []
        self.request = self.enterContext(patch(
            "telegram.request.HTTPXRequest.do_request", new_callable=AsyncMock,
        ))
        self.request.side_effect = self.telegram_response
        self.application = bot_listener.create_application()
        await self.application.initialize()
        self.addAsyncCleanup(self.application.shutdown)

    async def telegram_response(self, url, **kwargs):
        endpoint = url.rsplit("/", 1)[-1]
        if endpoint == "getMe":
            result = {
                "id": 123456, "is_bot": True,
                "first_name": "Bins", "username": BOT_USERNAME,
            }
        elif endpoint == "deleteWebhook":
            result = True
        elif endpoint == "getUpdates":
            await asyncio.sleep(0.01)
            result, self.pending_updates = self.pending_updates, []
        else:
            raise AssertionError(f"Unexpected Telegram request: {endpoint}")
        return 200, json.dumps({"ok": True, "result": result}).encode()

    def update_payload(self, text="/bins", chat_id=CHAT_ID, update_id=1):
        return {
            "update_id": update_id,
            "message": {
                "message_id": update_id,
                "date": 1792148400,
                "chat": {"id": chat_id, "type": "supergroup"},
                "from": {"id": 42, "is_bot": False, "first_name": "Tester"},
                "text": text,
                "entities": [{
                    "type": "bot_command", "offset": 0,
                    "length": len(text.split()[0]),
                }],
            },
        }

    async def dispatch(self, text="/bins", chat_id=CHAT_ID):
        update = Update.de_json(self.update_payload(text, chat_id), self.application.bot)
        await self.application.process_update(update)

    async def test_bins_command(self):
        await self.dispatch()
        self.fetch.assert_called_once_with()
        self.reply.assert_awaited_once_with(
            "🗑️ Next bin collections:\nFood: Saturday 17 October 2026"
        )

    async def test_bot_qualified_command(self):
        await self.dispatch(f"/bins@{BOT_USERNAME}")
        self.fetch.assert_called_once_with()
        self.reply.assert_awaited_once()

    async def test_other_chats_are_ignored_before_lookup(self):
        await self.dispatch(chat_id=-999)
        self.fetch.assert_not_called()
        self.reply.assert_not_awaited()

    async def test_other_bots_and_commands_are_ignored(self):
        for text in ("/bins@AnotherBot", "/other"):
            with self.subTest(text=text):
                await self.dispatch(text)
        self.fetch.assert_not_called()
        self.reply.assert_not_awaited()

    async def test_each_request_fetches_fresh_data(self):
        self.fetch.side_effect = [
            [(datetime(2026, 10, 17), "Food")],
            [(datetime(2026, 10, 18), "Food")],
        ]
        await self.dispatch()
        await self.dispatch()
        self.assertEqual(self.fetch.call_count, 2)
        self.assertEqual(
            [call.args[0] for call in self.reply.await_args_list],
            [
                "🗑️ Next bin collections:\nFood: Saturday 17 October 2026",
                "🗑️ Next bin collections:\nFood: Sunday 18 October 2026",
            ],
        )

    async def test_lookup_runs_outside_the_event_loop_thread(self):
        worker_threads = []
        self.fetch.side_effect = lambda: worker_threads.append(threading.get_ident()) or []
        await self.dispatch()
        self.assertEqual(len(worker_threads), 1)
        self.assertNotEqual(worker_threads[0], threading.get_ident())

    async def test_empty_results(self):
        self.fetch.return_value = []
        await self.dispatch()
        self.reply.assert_awaited_once_with(
            "No upcoming bin collections were returned by the council."
        )

    async def test_lookup_failure_is_logged_and_next_request_can_succeed(self):
        self.fetch.side_effect = RuntimeError("Council unavailable")
        with self.assertLogs("bot_listener", level="ERROR") as logs:
            await self.dispatch()
        self.assertIn("Council unavailable", "\n".join(logs.output))
        self.reply.assert_awaited_once_with(
            "Collection details are temporarily unavailable. Please try /bins again later."
        )
        self.fetch.side_effect = None
        await self.dispatch()
        self.assertEqual(self.reply.await_count, 2)
        self.assertIn("Food: Saturday 17 October 2026", self.reply.await_args.args[0])

    async def test_telegram_error_is_logged_and_next_request_can_succeed(self):
        self.reply.side_effect = RuntimeError("Telegram unavailable")
        with self.assertLogs("bot_listener", level="ERROR") as logs:
            await self.dispatch()
        self.assertIn("Telegram unavailable", "\n".join(logs.output))
        self.reply.side_effect = None
        await self.dispatch()
        self.assertEqual(self.reply.await_count, 2)

    async def test_today_uses_london_date_in_summer_and_winter(self):
        cases = [
            (datetime(2026, 7, 5, 23, 30, tzinfo=timezone.utc),
             [datetime(2026, 7, 5), datetime(2026, 7, 6)], "Monday 06 July 2026"),
            (datetime(2026, 1, 15, 23, 30, tzinfo=timezone.utc),
             [datetime(2026, 1, 15), datetime(2026, 1, 16)], "Thursday 15 January 2026"),
        ]
        for instant, dates, expected_date in cases:
            with self.subTest(instant=instant):
                self.clock.now.side_effect = (
                    lambda tz=None: instant.astimezone(tz) if tz else instant.replace(tzinfo=None)
                )
                self.fetch.return_value = [(dt, "Food") for dt in dates]
                self.reply.reset_mock()
                await self.dispatch()
                self.reply.assert_awaited_once_with(
                    f"🗑️ Next bin collections:\nFood: {expected_date}"
                )

    async def test_polling_handles_both_commands_and_keeps_running(self):
        self.pending_updates = [
            self.update_payload(update_id=1),
            self.update_payload(f"/bins@{BOT_USERNAME}", update_id=2),
        ]
        both_replied = asyncio.Event()

        async def record_reply(*args, **kwargs):
            if self.reply.await_count == 2:
                both_replied.set()

        self.reply.side_effect = record_reply
        await self.application.start()
        self.addAsyncCleanup(self.application.stop)
        await self.application.updater.start_polling(
            allowed_updates=["message"], drop_pending_updates=True,
        )
        self.addAsyncCleanup(self.application.updater.stop)
        await asyncio.wait_for(both_replied.wait(), timeout=2)
        await asyncio.sleep(0.05)
        self.assertTrue(self.application.running)
        self.assertTrue(self.application.updater.running)
        self.assertEqual(self.fetch.call_count, 2)

    async def test_queries_preserve_reminder_state_and_duplicate_suppression(self):
        class ReminderClock(datetime):
            @classmethod
            def now(cls):
                return datetime(2026, 10, 16, 12)

        client = SimpleNamespace(send_message=AsyncMock())
        with TemporaryDirectory() as directory, chdir(directory), patch(
            "bin_checker.datetime", ReminderClock,
        ), patch("bin_checker.get_north_herts_bins", return_value=[
            (datetime(2026, 10, 17), "Food"),
        ]):
            checker = BinChecker(days_from_now=1)
            checker.telegram, checker.telegram_chat_id = client, str(CHAT_ID)
            await checker.run()
            client.send_message.assert_awaited_once()
            state = Path("data.pkl").read_bytes()

            await self.dispatch()
            self.assertEqual(Path("data.pkl").read_bytes(), state)

            checker = BinChecker(days_from_now=1)
            checker.telegram, checker.telegram_chat_id = client, str(CHAT_ID)
            await checker.run()
            client.send_message.assert_awaited_once()


class ConfigurationTests(unittest.TestCase):
    def test_requires_token(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(ValueError, "TELEGRAM_TOKEN"):
                bot_listener.create_application()

    def test_requires_numeric_chat_id(self):
        for chat_id in ("", "not-a-chat-id"):
            with self.subTest(chat_id=chat_id), patch.dict("os.environ", {
                "TELEGRAM_TOKEN": "123456:test-token", "TELEGRAM_CHAT_ID": chat_id,
            }, clear=True):
                with self.assertRaisesRegex(ValueError, "TELEGRAM_CHAT_ID"):
                    bot_listener.create_application()


if __name__ == "__main__":
    unittest.main()
