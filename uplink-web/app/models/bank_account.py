"""Bank account model."""
from app.extensions import db


class BankAccount(db.Model):
    __tablename__ = "bank_accounts"

    id = db.Column(db.Integer, primary_key=True)
    game_session_id = db.Column(db.String(36), db.ForeignKey("game_sessions.id"))
    owner_name = db.Column(db.String(128), nullable=False)
    bank_ip = db.Column(db.String(32), nullable=False)
    balance = db.Column(db.Integer, default=0)
    loan_amount = db.Column(db.Integer, default=0)
    is_player = db.Column(db.Boolean, default=False)
    account_number = db.Column(db.String(32), nullable=True)


class LoanRecord(db.Model):
    __tablename__ = "loan_records"

    id = db.Column(db.Integer, primary_key=True)
    bank_account_id = db.Column(db.Integer, db.ForeignKey("bank_accounts.id"))
    amount = db.Column(db.Integer, nullable=False)
    interest_rate = db.Column(db.Float, nullable=False)
    created_at_tick = db.Column(db.Integer, default=0)
    is_paid = db.Column(db.Boolean, default=False)
