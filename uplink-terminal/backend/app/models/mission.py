"""Mission model."""

import json

from ..extensions import db


class Mission(db.Model):
    __tablename__ = "missions"

    id = db.Column(db.Integer, primary_key=True)
    game_session_id = db.Column(
        db.String(36), db.ForeignKey("game_sessions.id"), nullable=False, index=True
    )
    mission_type = db.Column(db.String(32), nullable=False)
    employer = db.Column(db.String(128), nullable=False, default="")
    contact = db.Column(db.String(128), nullable=False, default="")
    description = db.Column(db.String(256), nullable=False, default="")
    details = db.Column(db.Text, nullable=False, default="")
    full_details = db.Column(db.Text, nullable=False, default="")
    target_ip = db.Column(db.String(32), nullable=False, default="")
    target_filename = db.Column(db.String(128), nullable=True)
    target_data_json = db.Column(db.Text, default="{}")
    payment = db.Column(db.Integer, default=0)
    difficulty = db.Column(db.Integer, default=1)
    min_rating = db.Column(db.Integer, default=0)
    status = db.Column(db.String(32), default="AVAILABLE", nullable=False)
    accepted_at_tick = db.Column(db.Integer, nullable=True)
    completed_at_tick = db.Column(db.Integer, nullable=True)
    created_at_tick = db.Column(db.Integer, default=0)

    @property
    def target_data(self):
        try:
            return json.loads(self.target_data_json) if self.target_data_json else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    @target_data.setter
    def target_data(self, value):
        self.target_data_json = json.dumps(value)

    def __repr__(self):
        return f"<Mission {self.mission_type} '{self.description}' [{self.status}]>"
