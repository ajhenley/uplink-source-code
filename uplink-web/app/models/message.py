"""Player message/email model."""
from app.extensions import db


class Message(db.Model):
    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)
    game_session_id = db.Column(db.String(36), db.ForeignKey("game_sessions.id"))
    player_id = db.Column(db.Integer, db.ForeignKey("players.id"))
    from_name = db.Column(db.String(128), nullable=False)
    subject = db.Column(db.String(256), nullable=False)
    body = db.Column(db.String(4096), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at_tick = db.Column(db.Integer, default=0)
