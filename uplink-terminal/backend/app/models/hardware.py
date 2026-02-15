"""Hardware model — gateway hardware owned by the player."""

from ..extensions import db


class Hardware(db.Model):
    __tablename__ = "hardware"

    id = db.Column(db.Integer, primary_key=True)
    game_session_id = db.Column(
        db.String(36), db.ForeignKey("game_sessions.id"), nullable=False, index=True
    )
    hardware_type = db.Column(db.String(16), nullable=False)  # CPU, MODEM, MEMORY
    name = db.Column(db.String(128), nullable=False)
    value = db.Column(db.Integer, nullable=False)  # GHz, GQ/s, GQ
    cost = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f"<Hardware {self.name} ({self.hardware_type}={self.value})>"
