"""Game session model."""
import uuid
from datetime import datetime
from app.extensions import db


class GameSession(db.Model):
    __tablename__ = "game_sessions"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.Integer, db.ForeignKey("user_accounts.id"), nullable=False)
    name = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    game_time_ticks = db.Column(db.Integer, default=0)
    last_saved_at = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
