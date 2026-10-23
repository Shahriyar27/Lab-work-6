from abc import ABC, abstractmethod


class BaseNotificationService(ABC):
    @abstractmethod
    def send(self, recipient, message):
        """Вернуть результат демонстрационной отправки."""


class EmailNotificationService(BaseNotificationService):
    def send(self, recipient, message):
        return "simulated"


class SMSNotificationService(BaseNotificationService):
    def send(self, recipient, message):
        return "simulated"


class PushNotificationService(BaseNotificationService):
    def send(self, recipient, message):
        return "simulated"


class Creator(ABC):
    @abstractmethod
    def create_service(self):
        """Factory Method: конкретный создатель определяет продукт."""

    def send(self, recipient, message):
        return self.create_service().send(recipient, message)


class EmailCreator(Creator):
    def create_service(self):
        return EmailNotificationService()


class SMSCreator(Creator):
    def create_service(self):
        return SMSNotificationService()


class PushCreator(Creator):
    def create_service(self):
        return PushNotificationService()


class NotificationFactory:
    creators = {"email": EmailCreator, "sms": SMSCreator, "push": PushCreator}

    @classmethod
    def get_creator(cls, notification_type):
        try:
            return cls.creators[notification_type]()
        except KeyError:
            raise ValueError("Неизвестный канал. Выберите email, sms или push.") from None

    @classmethod
    def create_service(cls, notification_type):
        return cls.get_creator(notification_type).create_service()
