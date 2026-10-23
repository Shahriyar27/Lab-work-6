from datetime import datetime, timezone

from database import db


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(20), nullable=False)
    recipient = db.Column(db.Text, nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(30), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False,
                           default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    def to_dict(self):
        return {"id": self.id, "type": self.type, "recipient": self.recipient,
                "message": self.message, "status": self.status,
                "created_at": self.created_at.isoformat(timespec="microseconds") + "Z"}
