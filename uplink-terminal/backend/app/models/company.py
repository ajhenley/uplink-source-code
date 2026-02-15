"""Company model."""

from ..extensions import db


class Company(db.Model):
    __tablename__ = "companies"

    id = db.Column(db.Integer, primary_key=True)
    game_session_id = db.Column(
        db.String(36), db.ForeignKey("game_sessions.id"), nullable=False, index=True
    )
    name = db.Column(db.String(128), nullable=False)
    company_type = db.Column(db.String(32), nullable=False, default="COMMERCIAL")
    size = db.Column(db.Integer, default=5)
    growth = db.Column(db.Integer, default=0)
    alignment = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f"<Company {self.name}>"
