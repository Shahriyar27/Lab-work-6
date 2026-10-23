import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sqlalchemy.exc import SQLAlchemyError

from app import create_app
from database import DatabaseManager, database_manager, db
from factory import (NotificationFactory, EmailNotificationService,
                     SMSNotificationService, PushNotificationService)


class NotificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.config = {"TESTING": True, "SQLALCHEMY_DATABASE_URI":
                       "sqlite:///" + (Path(self.temp.name) / "test.db").as_posix()}
        self.app = create_app(self.config)
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.engine.dispose()
        self.temp.cleanup()

    def payload(self, channel="email"):
        return {"type": channel, "recipient": "demo@example.test", "message": "Привет <script>"}

    def test_channels_history_and_order(self):
        for channel in ("email", "sms", "push"):
            response = self.client.post("/api/send-notification", json=self.payload(channel))
            self.assertEqual(response.status_code, 201)
            record = response.json["notification"]
            self.assertEqual(record["type"], channel)
            self.assertEqual(record["status"], "simulated")
            self.assertTrue(record["created_at"].endswith("Z"))
        records = self.client.get("/api/notifications").json["notifications"]
        self.assertEqual([item["type"] for item in records], ["push", "sms", "email"])
        self.assertEqual(records[0]["message"], "Привет <script>")

    def test_persistence_after_recreation(self):
        self.client.post("/api/send-notification", json=self.payload())
        with self.app.app_context():
            db.session.remove()
            db.engine.dispose()
        second = create_app(self.config)
        try:
            records = second.test_client().get("/api/notifications").json["notifications"]
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["recipient"], "demo@example.test")
        finally:
            with second.app_context():
                db.session.remove()
                db.engine.dispose()

    def test_missing_empty_and_wrong_fields(self):
        for field in ("type", "recipient", "message"):
            missing = self.payload()
            del missing[field]
            with self.subTest(field=field, missing=True):
                self.assertEqual(self.client.post("/api/send-notification", json=missing).status_code, 400)
            for value in ("", "  \n", None, 5, False, [], {}):
                payload = self.payload()
                payload[field] = value
                with self.subTest(field=field, value=value):
                    self.assertEqual(self.client.post("/api/send-notification", json=payload).status_code, 400)
        self.assertEqual(self.client.get("/api/notifications").json, {"notifications": []})

    def test_json_object_and_malformed_json(self):
        for raw in ('[]', 'null', '42', '"text"', '{broken'):
            with self.subTest(raw=raw):
                response = self.client.post("/api/send-notification", data=raw, content_type="application/json")
                self.assertEqual(response.status_code, 400)
                self.assertIn("error", response.json)
        self.assertEqual(self.client.post("/api/send-notification", data="text").status_code, 400)

    def test_unknown_channel(self):
        response = self.client.post("/api/send-notification", json=self.payload("fax"))
        self.assertEqual(response.status_code, 400)
        self.assertIn("Неизвестный", response.json["error"])

    def test_singleton_and_repeated_init(self):
        self.assertIs(DatabaseManager(), database_manager)
        self.assertIs(DatabaseManager().db, db)
        database_manager.init_app(self.app)

    def test_factory(self):
        for channel, expected in (("email", EmailNotificationService),
                                  ("sms", SMSNotificationService), ("push", PushNotificationService)):
            with self.subTest(channel=channel):
                self.assertIsInstance(NotificationFactory.create_service(channel), expected)
                self.assertEqual(NotificationFactory.get_creator(channel).send("a", "b"), "simulated")
        with self.assertRaises(ValueError):
            NotificationFactory.get_creator("fax")

    def test_rollback_and_recovery(self):
        with self.app.app_context():
            with patch.object(db.session, "commit", side_effect=SQLAlchemyError("test")), \
                    patch.object(db.session, "rollback", wraps=db.session.rollback) as rollback:
                response = self.client.post("/api/send-notification", json=self.payload())
                self.assertEqual(response.status_code, 500)
                rollback.assert_called_once()
        self.assertEqual(self.client.get("/api/notifications").json["notifications"], [])
        self.assertEqual(self.client.post("/api/send-notification", json=self.payload()).status_code, 201)

    def test_page(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Демонстрационная отправка", response.get_data(as_text=True))
        self.assertIn("cell.textContent", response.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
