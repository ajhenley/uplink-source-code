"""VLocation (virtual location) model."""

from ..extensions import db


class VLocation(db.Model):
    __tablename__ = "vlocations"

    id = db.Column(db.Integer, primary_key=True)
    game_session_id = db.Column(
        db.String(36), db.ForeignKey("game_sessions.id"), nullable=False, index=True
    )
    ip = db.Column(db.String(32), nullable=False)
    x = db.Column(db.Integer, default=0)
    y = db.Column(db.Integer, default=0)
    listed = db.Column(db.Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<VLocation {self.ip}>"
