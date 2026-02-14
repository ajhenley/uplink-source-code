"""Security system model."""
from app.extensions import db


class SecuritySystem(db.Model):
    __tablename__ = "security_systems"

    id = db.Column(db.Integer, primary_key=True)
    computer_id = db.Column(db.Integer, db.ForeignKey("computers.id"))
    security_type = db.Column(db.Integer, nullable=False)
    level = db.Column(db.Integer, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
