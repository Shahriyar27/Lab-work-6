import os
from pathlib import Path

from flask import Flask, jsonify, render_template, request
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import BadRequest

from database import database_manager, db
from factory import NotificationFactory
from models import Notification


def create_app(config=None):
    app = Flask(__name__)
    app.config.update(SQLALCHEMY_DATABASE_URI="sqlite:///notifications.db",
                      SQLALCHEMY_TRACK_MODIFICATIONS=False)
    if config:
        app.config.update(config)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    database_manager.init_app(app)
    # Модель уже импортирована: create_all видит таблицу Notification.
    with app.app_context():
        db.create_all()

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.post("/api/send-notification")
    def send_notification():
        if not request.is_json:
            return jsonify(error="Нужен JSON с Content-Type: application/json."), 400
        try:
            data = request.get_json()
        except BadRequest:
            return jsonify(error="Некорректный JSON."), 400
        if not isinstance(data, dict):
            return jsonify(error="JSON должен быть объектом."), 400
        for field in ("type", "recipient", "message"):
            if field not in data or not isinstance(data[field], str) or not data[field].strip():
                return jsonify(error=f"Поле '{field}' обязательно и должно быть непустой строкой."), 400
        values = {field: data[field].strip() for field in ("type", "recipient", "message")}
        try:
            creator = NotificationFactory.get_creator(values["type"])
        except ValueError as exc:
            return jsonify(error=str(exc)), 400
        status = creator.send(values["recipient"], values["message"])
        notification = Notification(**values, status=status)
        try:
            db.session.add(notification)
            db.session.commit()
            result = notification.to_dict()
        except SQLAlchemyError:
            db.session.rollback()
            app.logger.exception("Ошибка сохранения уведомления")
            return jsonify(error="Не удалось сохранить уведомление в базе данных."), 500
        return jsonify(message="Демонстрационная отправка выполнена.", notification=result), 201

    @app.get("/api/notifications")
    def history():
        records = db.session.execute(db.select(Notification).order_by(
            Notification.created_at.desc(), Notification.id.desc())).scalars().all()
        return jsonify(notifications=[item.to_dict() for item in records])

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")), debug=False)
