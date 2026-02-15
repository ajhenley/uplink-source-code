"""PlayerLink (bookmarked systems) model."""

from ..extensions import db


class PlayerLink(db.Model):
    __tablename__ = "player_links"

    id = db.Column(db.Integer, primary_key=True)
    game_session_id = db.Column(
        db.String(36), db.ForeignKey("game_sessions.id"), nullable=False, index=True
    )
    ip = db.Column(db.String(32), nullable=False)
    label = db.Column(db.String(128), default="")

    def __repr__(self):
        return f"<PlayerLink {self.label} ({self.ip})>"
