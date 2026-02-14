"""Player gateway hardware model."""
from app.extensions import db


class Gateway(db.Model):
    __tablename__ = "gateways"

    id = db.Column(db.Integer, primary_key=True)
    game_session_id = db.Column(db.String(36), db.ForeignKey("game_sessions.id"))
    name = db.Column(db.String(64), default="Gateway ALPHA")
    cpu_speed = db.Column(db.Integer, default=60)
    modem_speed = db.Column(db.Integer, default=1)
    memory_size = db.Column(db.Integer, default=24)
    has_self_destruct = db.Column(db.Boolean, default=False)
    has_motion_sensor = db.Column(db.Boolean, default=False)
