"""Scheduled event model for delayed consequences."""
from app.extensions import db


class ScheduledEvent(db.Model):
    __tablename__ = "scheduled_events"

    id = db.Column(db.Integer, primary_key=True)
    game_session_id = db.Column(db.String(36), db.ForeignKey("game_sessions.id"))
    event_type = db.Column(db.String(64), nullable=False)
    trigger_tick = db.Column(db.Integer, nullable=False)
    data = db.Column(db.String(4096), default="{}")
    is_processed = db.Column(db.Boolean, default=False)
