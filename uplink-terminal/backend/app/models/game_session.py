import uuid
from datetime import datetime, timezone

from ..extensions import db


class GameSession(db.Model):
    __tablename__ = "game_sessions"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.Integer, db.ForeignKey("user_accounts.id"), nullable=False)
    name = db.Column(db.String(128), nullable=False, default="Untitled")
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    game_time_ticks = db.Column(db.Integer, default=0, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    speed_multiplier = db.Column(db.Integer, default=1, nullable=False)
    balance = db.Column(db.Integer, default=3000, nullable=False)
    gateway_ip = db.Column(db.String(32), nullable=True)

    user = db.relationship("UserAccount", back_populates="sessions")

    @property
    def play_time_hours(self):
        """Convert ticks to hours (5 ticks/sec)."""
        return self.game_time_ticks / (5 * 3600)

    def __repr__(self):
        return f"<GameSession {self.name} ({self.id[:8]})>"
