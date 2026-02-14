"""Mission model."""
from app.extensions import db


class Mission(db.Model):
    __tablename__ = "missions"

    id = db.Column(db.Integer, primary_key=True)
    game_session_id = db.Column(db.String(36), db.ForeignKey("game_sessions.id"))
    mission_type = db.Column(db.Integer, nullable=False)
    description = db.Column(db.String(1024), nullable=False)
    employer_name = db.Column(db.String(128), nullable=False)
    payment = db.Column(db.Integer, nullable=False)
    difficulty = db.Column(db.Integer, nullable=False)
    min_rating = db.Column(db.Integer, default=0)
    target_computer_ip = db.Column(db.String(32), nullable=True)
    target_data = db.Column(db.String(4096), nullable=True)
    is_accepted = db.Column(db.Boolean, default=False)
    is_completed = db.Column(db.Boolean, default=False)
    accepted_by = db.Column(db.String(64), nullable=True)
    created_at_tick = db.Column(db.Integer, default=0)
    due_at_tick = db.Column(db.Integer, nullable=True)
