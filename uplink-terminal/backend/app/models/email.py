"""Email model."""

from ..extensions import db


class Email(db.Model):
    __tablename__ = "emails"

    id = db.Column(db.Integer, primary_key=True)
    game_session_id = db.Column(
        db.String(36), db.ForeignKey("game_sessions.id"), nullable=False, index=True
    )
    subject = db.Column(db.String(256), nullable=False, default="")
    body = db.Column(db.Text, nullable=False, default="")
    from_addr = db.Column(db.String(128), nullable=False, default="")
    to_addr = db.Column(db.String(128), nullable=False, default="")
    game_tick_sent = db.Column(db.Integer, default=0)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    attachment_filename = db.Column(db.String(128), nullable=True)
    attachment_data = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f"<Email '{self.subject}'>"
