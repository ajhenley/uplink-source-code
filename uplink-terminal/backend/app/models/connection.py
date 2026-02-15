"""Connection (active network connection) model."""

import json

from ..extensions import db


class Connection(db.Model):
    __tablename__ = "connections"

    id = db.Column(db.Integer, primary_key=True)
    game_session_id = db.Column(
        db.String(36), db.ForeignKey("game_sessions.id"), nullable=False, unique=True
    )
    target_ip = db.Column(db.String(32), nullable=True)
    is_active = db.Column(db.Boolean, default=False, nullable=False)
    trace_in_progress = db.Column(db.Boolean, default=False, nullable=False)
    trace_progress = db.Column(db.Float, default=0.0)
    trace_start_tick = db.Column(db.Integer, default=0)
    bounce_route_json = db.Column(db.Text, default="[]")

    @property
    def bounce_route(self):
        try:
            return json.loads(self.bounce_route_json) if self.bounce_route_json else []
        except (json.JSONDecodeError, TypeError):
            return []

    @bounce_route.setter
    def bounce_route(self, value):
        self.bounce_route_json = json.dumps(value)

    def __repr__(self):
        return f"<Connection target={self.target_ip} active={self.is_active}>"
