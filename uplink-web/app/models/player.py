"""Player (agent) model."""
from app.extensions import db


class Player(db.Model):
    __tablename__ = "players"

    id = db.Column(db.Integer, primary_key=True)
    game_session_id = db.Column(db.String(36), db.ForeignKey("game_sessions.id"), unique=True)
    name = db.Column(db.String(128), nullable=False)
    handle = db.Column(db.String(64), nullable=False)
    balance = db.Column(db.Integer, default=3000)
    uplink_rating = db.Column(db.Integer, default=0)
    neuromancer_rating = db.Column(db.Integer, default=5)
    credit_rating = db.Column(db.Integer, default=10)
    gateway_id = db.Column(db.Integer, db.ForeignKey("gateways.id"), nullable=True)
    localhost_ip = db.Column(db.String(32), nullable=True)
