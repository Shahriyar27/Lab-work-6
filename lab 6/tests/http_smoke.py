"""Проверка настоящих HTTP-запросов без изменения пользовательской базы."""
import json
import tempfile
from pathlib import Path
from threading import Thread
from urllib.request import Request, urlopen

from werkzeug.serving import make_server

from app import create_app
from database import db


def main():
    with tempfile.TemporaryDirectory() as directory:
        app = create_app({"SQLALCHEMY_DATABASE_URI": "sqlite:///" +
                          (Path(directory) / "http.db").as_posix()})
        server = make_server("127.0.0.1", 0, app)
        worker = Thread(target=server.serve_forever, daemon=True)
        worker.start()
        base = f"http://127.0.0.1:{server.server_port}"
        try:
            with urlopen(base + "/", timeout=5) as response:
                assert response.status == 200
                assert "Демонстрационная отправка" in response.read().decode("utf-8")
            for channel in ("email", "sms", "push"):
                payload = json.dumps({"type": channel, "recipient": "demo", "message": "HTTP smoke"}).encode()
                request = Request(base + "/api/send-notification", data=payload,
                                  headers={"Content-Type": "application/json"})
                with urlopen(request, timeout=5) as response:
                    assert response.status == 201
                    assert json.load(response)["notification"]["type"] == channel
            with urlopen(base + "/api/notifications", timeout=5) as response:
                assert len(json.load(response)["notifications"]) == 3
            print("HTTP smoke OK: page, three channels, history")
        finally:
            server.shutdown()
            worker.join(timeout=5)
            server.server_close()
            with app.app_context():
                db.session.remove()
                db.engine.dispose()


if __name__ == "__main__":
    main()
