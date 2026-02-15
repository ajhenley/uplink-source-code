"""SecuritySystem model."""

from ..extensions import db


class SecuritySystem(db.Model):
    __tablename__ = "security_systems"

    id = db.Column(db.Integer, primary_key=True)
    computer_id = db.Column(db.Integer, db.ForeignKey("computers.id"), nullable=False)
    security_type = db.Column(db.String(32), nullable=False)
    level = db.Column(db.Integer, default=1)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_bypassed = db.Column(db.Boolean, default=False, nullable=False)

    def __repr__(self):
        return f"<Security {self.security_type} lv{self.level}>"
