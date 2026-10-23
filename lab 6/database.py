from threading import Lock

from flask_sqlalchemy import SQLAlchemy


class DatabaseManager:
    """Один менеджер и ORM на процесс; соединениями управляет SQLAlchemy."""

    _instance = None
    _lock = Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                instance = super().__new__(cls)
                instance.db = SQLAlchemy()
                cls._instance = instance
        return cls._instance

    def init_app(self, app):
        # Инициализация приложения отделена от создания Singleton.
        if "sqlalchemy" not in app.extensions:
            self.db.init_app(app)


database_manager = DatabaseManager()
db = database_manager.db
