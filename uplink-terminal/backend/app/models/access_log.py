"""AccessLog model."""

from ..extensions import db


class AccessLog(db.Model):
    __tablename__ = "access_logs"

    id = db.Column(db.Integer, primary_key=True)
    computer_id = db.Column(db.Integer, db.ForeignKey("computers.id"), nullable=False)
    game_tick = db.Column(db.Integer, default=0)
    from_ip = db.Column(db.String(32), default="")
    from_name = db.Column(db.String(128), default="")
    action = db.Column(db.String(128), default="")
    is_visible = db.Column(db.Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<AccessLog {self.action}>"
