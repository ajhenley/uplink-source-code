"""Virtual location model (IP to world map coordinates)."""
from app.extensions import db


class VLocation(db.Model):
    __tablename__ = "vlocations"

    id = db.Column(db.Integer, primary_key=True)
    game_session_id = db.Column(db.String(36), db.ForeignKey("game_sessions.id"))
    ip = db.Column(db.String(32), index=True, nullable=False)
    x = db.Column(db.Integer, nullable=False)
    y = db.Column(db.Integer, nullable=False)
    listed = db.Column(db.Boolean, default=True)
    computer_id = db.Column(db.Integer, db.ForeignKey("computers.id"), nullable=True)
