"""Running task model (active hacking tools)."""
from app.extensions import db


class RunningTask(db.Model):
    __tablename__ = "running_tasks"

    id = db.Column(db.Integer, primary_key=True)
    game_session_id = db.Column(db.String(36), db.ForeignKey("game_sessions.id"))
    player_id = db.Column(db.Integer, db.ForeignKey("players.id"))
    tool_name = db.Column(db.String(64), nullable=False)
    tool_version = db.Column(db.Integer, default=1)
    target_ip = db.Column(db.String(32), nullable=True)
    target_data = db.Column(db.String(4096), nullable=True)
    progress = db.Column(db.Float, default=0.0)
    ticks_remaining = db.Column(db.Float, default=0.0)
    is_active = db.Column(db.Boolean, default=True)
