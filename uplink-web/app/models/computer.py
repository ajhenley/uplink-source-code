"""Computer and screen definition models."""
from app.extensions import db


class Computer(db.Model):
    __tablename__ = "computers"

    id = db.Column(db.Integer, primary_key=True)
    game_session_id = db.Column(db.String(36), db.ForeignKey("game_sessions.id"))
    name = db.Column(db.String(128), nullable=False)
    company_name = db.Column(db.String(128), nullable=False)
    ip = db.Column(db.String(32), nullable=False)
    computer_type = db.Column(db.Integer, nullable=False)
    trace_speed = db.Column(db.Float, nullable=False)
    hack_difficulty = db.Column(db.Float, nullable=False)
    is_running = db.Column(db.Boolean, default=True)


class ComputerScreenDef(db.Model):
    __tablename__ = "computer_screen_defs"

    id = db.Column(db.Integer, primary_key=True)
    computer_id = db.Column(db.Integer, db.ForeignKey("computers.id"))
    screen_type = db.Column(db.Integer, nullable=False)
    next_page = db.Column(db.Integer, nullable=True)
    sub_page = db.Column(db.Integer, default=0)
    data1 = db.Column(db.String(256), nullable=True)
    data2 = db.Column(db.String(256), nullable=True)
    data3 = db.Column(db.String(256), nullable=True)
