"""Finance engine -- banking, stock market, and loan systems."""
import logging
import random

from app.extensions import db
from app.models.bank_account import BankAccount, LoanRecord
from app.models.stock_market import StockEntry, StockHolding
from app.models.player import Player
from app.game import constants as C

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Credit-rating thresholds for loan interest rates
# ---------------------------------------------------------------------------
CREDIT_EXCELLENT_THRESHOLD = 7
CREDIT_GOOD_THRESHOLD = 3

INTEREST_RATE_EXCELLENT = 0.05
INTEREST_RATE_GOOD = 0.10
INTEREST_RATE_POOR = 0.20

# Minimum balance allowed after a transfer (overdraft protection)
MIN_BALANCE = 0

# Maximum number of statement entries returned
MAX_STATEMENT_ENTRIES = 50

# Stock price fluctuation bounds (percentage of current price)
STOCK_TICK_MIN_CHANGE = -0.03
STOCK_TICK_MAX_CHANGE = 0.03

# Minimum stock price floor -- stocks cannot drop below this
STOCK_PRICE_FLOOR = 1


# ===================================================================
# Bank Operations
# ===================================================================

def get_player_accounts(session_id):
    """Return all bank accounts belonging to the player in this session.

    Returns:
        list[dict]: Each dict contains account id, bank_ip, balance,
                    loan_amount, account_number, and owner_name.
    """
    accounts = BankAccount.query.filter_by(
        game_session_id=session_id,
        is_player=True,
    ).all()

    return [
        {
            "id": acct.id,
            "bank_ip": acct.bank_ip,
            "balance": acct.balance,
            "loan_amount": acct.loan_amount,
            "account_number": acct.account_number,
            "owner_name": acct.owner_name,
        }
        for acct in accounts
    ]


def transfer_funds(session_id, from_account_id, to_account_id, amount):
    """Transfer credits between two bank accounts.

    Both accounts must belong to the same game session.  The source
    account must have sufficient funds.

    Returns:
        dict with ``"ok"`` bool and ``"error"`` string on failure.
    """
    if amount <= 0:
        return {"ok": False, "error": "Transfer amount must be positive"}

    from_acct = BankAccount.query.filter_by(
        id=from_account_id,
        game_session_id=session_id,
    ).first()

    to_acct = BankAccount.query.filter_by(
        id=to_account_id,
        game_session_id=session_id,
    ).first()

    if from_acct is None:
        return {"ok": False, "error": "Source account not found"}
    if to_acct is None:
        return {"ok": False, "error": "Destination account not found"}
    if from_acct.id == to_acct.id:
        return {"ok": False, "error": "Cannot transfer to the same account"}
    if from_acct.balance < amount:
        return {"ok": False, "error": "Insufficient funds"}

    from_acct.balance -= amount
    to_acct.balance += amount

    # Update the player model balance if either account is the player's
    _sync_player_balance(session_id)

    db.session.flush()

    log.info(
        "Transfer %d credits: account %d -> account %d (session %s)",
        amount, from_account_id, to_account_id, session_id,
    )

    return {
        "ok": True,
        "from_balance": from_acct.balance,
        "to_balance": to_acct.balance,
    }


def get_account_statement(account_id):
    """Return recent transaction log entries for a bank account.

    Uses AccessLog entries associated with the bank computer to build a
    statement.  Falls back to a minimal summary when no logs exist.

    Returns:
        dict with account details and a ``"transactions"`` list.
    """
    from app.models.access_log import AccessLog
    from app.models.computer import Computer
    from app.models.vlocation import VLocation

    acct = BankAccount.query.get(account_id)
    if acct is None:
        return {"ok": False, "error": "Account not found"}

    # Resolve the bank computer from the account's bank_ip
    loc = VLocation.query.filter_by(
        game_session_id=acct.game_session_id,
        ip=acct.bank_ip,
    ).first()

    transactions = []
    if loc is not None and loc.computer_id is not None:
        logs = AccessLog.query.filter(
            AccessLog.computer_id == loc.computer_id,
            AccessLog.is_deleted == False,
        ).order_by(AccessLog.id.desc()).limit(MAX_STATEMENT_ENTRIES).all()

        for entry in logs:
            transactions.append({
                "time": entry.log_time,
                "from_ip": entry.from_ip,
                "from_name": entry.from_name,
                "subject": entry.subject,
                "data": entry.data1,
            })

    return {
        "ok": True,
        "account_id": acct.id,
        "owner_name": acct.owner_name,
        "bank_ip": acct.bank_ip,
        "balance": acct.balance,
        "loan_amount": acct.loan_amount,
        "transactions": transactions,
    }


# ===================================================================
# Loan System
# ===================================================================

def _get_interest_rate_for_credit(credit_rating):
    """Determine the loan interest rate based on credit rating."""
    if credit_rating >= CREDIT_EXCELLENT_THRESHOLD:
        return INTEREST_RATE_EXCELLENT
    elif credit_rating >= CREDIT_GOOD_THRESHOLD:
        return INTEREST_RATE_GOOD
    else:
        return INTEREST_RATE_POOR


def _get_max_loan_for_credit(credit_rating):
    """Determine the maximum loan amount based on credit rating.

    Uses the Uplink constants for loan tiers.
    """
    if credit_rating >= CREDIT_EXCELLENT_THRESHOLD:
        return C.LARGELOAN_MAX
    elif credit_rating >= CREDIT_GOOD_THRESHOLD:
        return C.MEDIUMLOAN_MAX
    else:
        return C.SMALLLOAN_MAX


def take_loan(session_id, bank_account_id, amount):
    """Create a new loan on the given bank account.

    The interest rate is determined by the player's credit rating.
    The loan amount is added to the account balance and recorded as
    outstanding debt.

    Returns:
        dict with ``"ok"`` bool, loan details, or ``"error"`` string.
    """
    if amount <= 0:
        return {"ok": False, "error": "Loan amount must be positive"}

    acct = BankAccount.query.filter_by(
        id=bank_account_id,
        game_session_id=session_id,
    ).first()

    if acct is None:
        return {"ok": False, "error": "Bank account not found"}

    player = Player.query.filter_by(game_session_id=session_id).first()
    if player is None:
        return {"ok": False, "error": "Player not found"}

    credit_rating = player.credit_rating
    max_loan = _get_max_loan_for_credit(credit_rating)

    # Calculate existing outstanding debt on this account
    outstanding = LoanRecord.query.filter_by(
        bank_account_id=acct.id,
        is_paid=False,
    ).with_entities(db.func.coalesce(db.func.sum(LoanRecord.amount), 0)).scalar()

    if outstanding + amount > max_loan:
        return {
            "ok": False,
            "error": (
                f"Loan exceeds maximum allowed. "
                f"Outstanding: {outstanding}, requested: {amount}, max: {max_loan}"
            ),
        }

    interest_rate = _get_interest_rate_for_credit(credit_rating)

    # Find the current game tick for the loan record
    from app.models.game_session import GameSession
    session = db.session.get(GameSession, session_id)
    current_tick = session.game_time_ticks if session else 0

    loan = LoanRecord(
        bank_account_id=acct.id,
        amount=amount,
        interest_rate=interest_rate,
        created_at_tick=current_tick,
        is_paid=False,
    )
    db.session.add(loan)

    # Credit the loan amount to the bank account
    acct.balance += amount
    acct.loan_amount += amount

    _sync_player_balance(session_id)
    db.session.flush()

    log.info(
        "Loan of %d credits at %.0f%% interest on account %d (session %s)",
        amount, interest_rate * 100, bank_account_id, session_id,
    )

    return {
        "ok": True,
        "loan_id": loan.id,
        "amount": loan.amount,
        "interest_rate": loan.interest_rate,
        "account_balance": acct.balance,
        "total_debt": acct.loan_amount,
    }


def repay_loan(session_id, loan_id, amount):
    """Repay part or all of an outstanding loan.

    The repayment is deducted from the bank account that owns the loan.

    Returns:
        dict with ``"ok"`` bool and updated balances or ``"error"`` string.
    """
    if amount <= 0:
        return {"ok": False, "error": "Repayment amount must be positive"}

    loan = LoanRecord.query.get(loan_id)
    if loan is None:
        return {"ok": False, "error": "Loan not found"}
    if loan.is_paid:
        return {"ok": False, "error": "Loan is already paid off"}

    acct = BankAccount.query.filter_by(
        id=loan.bank_account_id,
        game_session_id=session_id,
    ).first()

    if acct is None:
        return {"ok": False, "error": "Bank account not found for this session"}

    # Clamp repayment to the remaining loan amount
    actual_repayment = min(amount, loan.amount)

    if acct.balance < actual_repayment:
        return {"ok": False, "error": "Insufficient funds to repay"}

    acct.balance -= actual_repayment
    loan.amount -= actual_repayment
    acct.loan_amount = max(0, acct.loan_amount - actual_repayment)

    if loan.amount <= 0:
        loan.is_paid = True
        loan.amount = 0

    _sync_player_balance(session_id)
    db.session.flush()

    log.info(
        "Loan %d repaid %d credits (remaining: %d, session %s)",
        loan_id, actual_repayment, loan.amount, session_id,
    )

    return {
        "ok": True,
        "loan_id": loan.id,
        "repaid": actual_repayment,
        "loan_remaining": loan.amount,
        "is_paid": loan.is_paid,
        "account_balance": acct.balance,
        "total_debt": acct.loan_amount,
    }


def accrue_interest(session_id, current_tick):
    """Accrue interest on all outstanding loans for a session.

    Called periodically by the game loop (every FREQUENCY_ADDINTERESTONLOANS
    game-minutes).  Each unpaid loan's amount is increased by its interest
    rate, and the owning bank account's loan_amount is updated to match.

    Returns:
        dict with ``"loans_updated"`` count and ``"total_interest"`` accrued.
    """
    # Find all player bank accounts for this session
    accounts = BankAccount.query.filter_by(
        game_session_id=session_id,
        is_player=True,
    ).all()

    total_interest = 0
    loans_updated = 0

    for acct in accounts:
        loans = LoanRecord.query.filter_by(
            bank_account_id=acct.id,
            is_paid=False,
        ).all()

        acct_interest = 0
        for loan in loans:
            interest = int(loan.amount * loan.interest_rate)
            if interest < 1 and loan.amount > 0:
                interest = 1  # Minimum 1 credit interest
            loan.amount += interest
            acct_interest += interest
            loans_updated += 1

        if acct_interest > 0:
            acct.loan_amount += acct_interest
            total_interest += acct_interest

    if loans_updated > 0:
        db.session.flush()
        log.info(
            "Interest accrued: %d credits across %d loans (session %s, tick %d)",
            total_interest, loans_updated, session_id, current_tick,
        )

    return {
        "loans_updated": loans_updated,
        "total_interest": total_interest,
    }


# ===================================================================
# Stock Market
# ===================================================================

def get_stock_prices(session_id):
    """Return current stock prices for all companies in the session.

    Returns:
        list[dict]: Each dict contains company_name, current_price,
                    previous_price, and volatility.
    """
    entries = StockEntry.query.filter_by(
        game_session_id=session_id,
    ).all()

    return [
        {
            "company_name": e.company_name,
            "current_price": e.current_price,
            "previous_price": e.previous_price,
            "volatility": e.volatility,
            "change": e.current_price - e.previous_price,
        }
        for e in entries
    ]


def buy_stock(session_id, player_id, company_name, shares):
    """Purchase shares in a company.

    The total cost is deducted from the player's primary bank account
    (first player account found).

    Returns:
        dict with ``"ok"`` bool, transaction details, or ``"error"`` string.
    """
    if shares <= 0:
        return {"ok": False, "error": "Must buy at least 1 share"}

    entry = StockEntry.query.filter_by(
        game_session_id=session_id,
        company_name=company_name,
    ).first()

    if entry is None:
        return {"ok": False, "error": f"No stock listing for '{company_name}'"}

    total_cost = entry.current_price * shares

    # Deduct from player's first bank account
    acct = BankAccount.query.filter_by(
        game_session_id=session_id,
        is_player=True,
    ).first()

    if acct is None:
        return {"ok": False, "error": "No player bank account found"}

    if acct.balance < total_cost:
        return {
            "ok": False,
            "error": (
                f"Insufficient funds. Cost: {total_cost}, "
                f"balance: {acct.balance}"
            ),
        }

    acct.balance -= total_cost

    # Update or create the stock holding
    holding = StockHolding.query.filter_by(
        game_session_id=session_id,
        player_id=player_id,
        company_name=company_name,
    ).first()

    if holding is None:
        holding = StockHolding(
            game_session_id=session_id,
            player_id=player_id,
            company_name=company_name,
            shares=shares,
            purchase_price=entry.current_price,
        )
        db.session.add(holding)
    else:
        # Average the purchase price across old + new shares
        old_total = holding.shares * holding.purchase_price
        new_total = shares * entry.current_price
        holding.shares += shares
        if holding.shares > 0:
            holding.purchase_price = (old_total + new_total) // holding.shares
        else:
            holding.purchase_price = entry.current_price

    _sync_player_balance(session_id)
    db.session.flush()

    log.info(
        "Bought %d shares of %s at %d each (total %d, session %s)",
        shares, company_name, entry.current_price, total_cost, session_id,
    )

    return {
        "ok": True,
        "company_name": company_name,
        "shares_bought": shares,
        "price_per_share": entry.current_price,
        "total_cost": total_cost,
        "account_balance": acct.balance,
        "total_shares_held": holding.shares,
    }


def sell_stock(session_id, player_id, company_name, shares):
    """Sell shares in a company.

    Proceeds are credited to the player's primary bank account.

    Returns:
        dict with ``"ok"`` bool, transaction details, or ``"error"`` string.
    """
    if shares <= 0:
        return {"ok": False, "error": "Must sell at least 1 share"}

    entry = StockEntry.query.filter_by(
        game_session_id=session_id,
        company_name=company_name,
    ).first()

    if entry is None:
        return {"ok": False, "error": f"No stock listing for '{company_name}'"}

    holding = StockHolding.query.filter_by(
        game_session_id=session_id,
        player_id=player_id,
        company_name=company_name,
    ).first()

    if holding is None or holding.shares < shares:
        available = holding.shares if holding else 0
        return {
            "ok": False,
            "error": f"Not enough shares. Held: {available}, selling: {shares}",
        }

    total_proceeds = entry.current_price * shares

    # Credit the player's first bank account
    acct = BankAccount.query.filter_by(
        game_session_id=session_id,
        is_player=True,
    ).first()

    if acct is None:
        return {"ok": False, "error": "No player bank account found"}

    acct.balance += total_proceeds
    holding.shares -= shares

    # Clean up empty holdings
    if holding.shares <= 0:
        db.session.delete(holding)

    _sync_player_balance(session_id)
    db.session.flush()

    log.info(
        "Sold %d shares of %s at %d each (proceeds %d, session %s)",
        shares, company_name, entry.current_price, total_proceeds, session_id,
    )

    return {
        "ok": True,
        "company_name": company_name,
        "shares_sold": shares,
        "price_per_share": entry.current_price,
        "total_proceeds": total_proceeds,
        "account_balance": acct.balance,
        "shares_remaining": max(0, (holding.shares if holding in db.session else 0)),
    }


def tick_stock_market(session_id):
    """Randomly fluctuate stock prices for a session.

    Called by the game loop each tick (or at a reduced frequency).
    Each stock entry's price moves by a random percentage bounded by
    its volatility.

    Returns:
        list[dict]: Updated stock prices.
    """
    entries = StockEntry.query.filter_by(
        game_session_id=session_id,
    ).all()

    updates = []
    for entry in entries:
        vol = entry.volatility if entry.volatility > 0 else 0.1
        change_pct = random.uniform(
            STOCK_TICK_MIN_CHANGE * vol / 0.1,
            STOCK_TICK_MAX_CHANGE * vol / 0.1,
        )
        delta = int(entry.current_price * change_pct)

        entry.previous_price = entry.current_price
        entry.current_price = max(STOCK_PRICE_FLOOR, entry.current_price + delta)

        updates.append({
            "company_name": entry.company_name,
            "current_price": entry.current_price,
            "previous_price": entry.previous_price,
            "change": entry.current_price - entry.previous_price,
        })

    if updates:
        db.session.flush()

    return updates


def crash_stock(session_id, company_name, amount):
    """Force a stock price crash for a company (e.g. when hacked).

    The price drops by the specified amount (clamped to the floor).

    Returns:
        dict with ``"ok"`` bool and updated price or ``"error"`` string.
    """
    entry = StockEntry.query.filter_by(
        game_session_id=session_id,
        company_name=company_name,
    ).first()

    if entry is None:
        return {"ok": False, "error": f"No stock listing for '{company_name}'"}

    entry.previous_price = entry.current_price
    entry.current_price = max(STOCK_PRICE_FLOOR, entry.current_price - abs(amount))

    # Increase volatility after a crash event
    entry.volatility = min(1.0, entry.volatility + 0.15)

    db.session.flush()

    log.info(
        "Stock crash: %s dropped by %d to %d (session %s)",
        company_name, abs(amount), entry.current_price, session_id,
    )

    return {
        "ok": True,
        "company_name": company_name,
        "previous_price": entry.previous_price,
        "current_price": entry.current_price,
        "drop": entry.previous_price - entry.current_price,
    }


# ===================================================================
# Internal helpers
# ===================================================================

def _sync_player_balance(session_id):
    """Keep the Player.balance field in sync with their primary bank account.

    The player's balance mirrors the first player-owned bank account so
    that HUD display code doesn't need to query the bank table separately.
    """
    player = Player.query.filter_by(game_session_id=session_id).first()
    if player is None:
        return

    acct = BankAccount.query.filter_by(
        game_session_id=session_id,
        is_player=True,
    ).first()

    if acct is not None:
        player.balance = acct.balance
