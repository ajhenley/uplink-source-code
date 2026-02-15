"""Software model — tools owned by the player."""

from ..extensions import db


class Software(db.Model):
    __tablename__ = "software"

    id = db.Column(db.Integer, primary_key=True)
    game_session_id = db.Column(
        db.String(36), db.ForeignKey("game_sessions.id"), nullable=False, index=True
    )
    name = db.Column(db.String(128), nullable=False)
    version = db.Column(db.String(16), default="1.0")
    software_type = db.Column(db.String(32), nullable=False)
    size = db.Column(db.Integer, default=1)
    cost = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f"<Software {self.name} v{self.version}>"
