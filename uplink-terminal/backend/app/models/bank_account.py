"""BankAccount model."""

from ..extensions import db


class BankAccount(db.Model):
    __tablename__ = "bank_accounts"

    id = db.Column(db.Integer, primary_key=True)
    computer_id = db.Column(db.Integer, db.ForeignKey("computers.id"), nullable=False)
    account_holder = db.Column(db.String(128), nullable=False)
    account_number = db.Column(db.String(16), nullable=False)
    balance = db.Column(db.Integer, default=0)
    is_player = db.Column(db.Boolean, default=False, nullable=False)

    def __repr__(self):
        return f"<BankAccount {self.account_number} ({self.account_holder})>"
