"""Connection and bounce chain models."""
from app.extensions import db


class Connection(db.Model):
    __tablename__ = "connections"

    id = db.Column(db.Integer, primary_key=True)
    game_session_id = db.Column(db.String(36), db.ForeignKey("game_sessions.id"))
    player_id = db.Column(db.Integer, db.ForeignKey("players.id"))
    target_ip = db.Column(db.String(32), nullable=True)
    is_active = db.Column(db.Boolean, default=False)
    trace_progress = db.Column(db.Float, default=0.0)
    trace_active = db.Column(db.Boolean, default=False)


class ConnectionNode(db.Model):
    __tablename__ = "connection_nodes"

    id = db.Column(db.Integer, primary_key=True)
    connection_id = db.Column(db.Integer, db.ForeignKey("connections.id"))
    position = db.Column(db.Integer, nullable=False)
    ip = db.Column(db.String(32), nullable=False)
    is_traced = db.Column(db.Boolean, default=False)
