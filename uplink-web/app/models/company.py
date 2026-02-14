"""Company model."""
from app.extensions import db


class Company(db.Model):
    __tablename__ = "companies"

    id = db.Column(db.Integer, primary_key=True)
    game_session_id = db.Column(db.String(36), db.ForeignKey("game_sessions.id"))
    name = db.Column(db.String(128), nullable=False)
    size = db.Column(db.Integer, nullable=False)
    growth = db.Column(db.Integer, nullable=False)
    alignment = db.Column(db.Integer, nullable=False)
    boss_name = db.Column(db.String(128), nullable=True)
    admin_email_addr = db.Column(db.String(128), nullable=True)
