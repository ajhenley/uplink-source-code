"""ConnectionHistory model."""

from ..extensions import db


class ConnectionHistory(db.Model):
    __tablename__ = "connection_history"

    id = db.Column(db.Integer, primary_key=True)
    game_session_id = db.Column(db.Integer, db.ForeignKey("game_sessions.id"), nullable=False)
    ip = db.Column(db.String(32), nullable=False)
    computer_name = db.Column(db.String(128), default="")
    connected_at_tick = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f"<ConnectionHistory {self.ip}>"
