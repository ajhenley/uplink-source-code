"""Person/NPC model."""
from app.extensions import db


class Person(db.Model):
    __tablename__ = "persons"

    id = db.Column(db.Integer, primary_key=True)
    game_session_id = db.Column(db.String(36), db.ForeignKey("game_sessions.id"))
    name = db.Column(db.String(128), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    is_agent = db.Column(db.Boolean, default=False)
    localhost_ip = db.Column(db.String(32), nullable=True)
    rating = db.Column(db.Integer, default=0)
    uplink_rating = db.Column(db.Integer, default=0)
    neuromancer_rating = db.Column(db.Integer, default=0)
    has_criminal_record = db.Column(db.Boolean, default=False)
    voice_index = db.Column(db.Integer, default=0)
    photo_index = db.Column(db.Integer, default=0)
