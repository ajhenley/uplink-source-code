"""Access log model."""
from app.extensions import db


class AccessLog(db.Model):
    __tablename__ = "access_logs"

    id = db.Column(db.Integer, primary_key=True)
    computer_id = db.Column(db.Integer, db.ForeignKey("computers.id"))
    log_time = db.Column(db.String(32), nullable=False)
    from_ip = db.Column(db.String(32), nullable=False)
    from_name = db.Column(db.String(128), nullable=False)
    subject = db.Column(db.String(256), nullable=False)
    log_type = db.Column(db.Integer, nullable=False)
    is_visible = db.Column(db.Boolean, default=True)
    is_deleted = db.Column(db.Boolean, default=False)
    data1 = db.Column(db.String(256), nullable=True)
