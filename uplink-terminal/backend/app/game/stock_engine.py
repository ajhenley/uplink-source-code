"""Stock market price simulation and trading."""

import random

from ..extensions import db
from ..models import GameSession, StockHolding


def init_stock_prices(gs, company_specs):
    """Initialize stock prices for all companies in a new game.

    Called from world_generator after companies are created.
    company_specs: list of (name, size, company_type) tuples.
    """
    from .constants import STOCK_BASE_PRICE, STOCK_PRICE_PER_SIZE

    prices = {}
    for name, size, ctype in company_specs:
        base = STOCK_BASE_PRICE + size * STOCK_PRICE_PER_SIZE
        # Add +/-15% randomness
        price = int(base * (1 + random.uniform(-0.15, 0.15)))
        prices[name] = {
            "price": max(10, price),
            "sentiment": 0.0,
            "prev_price": max(10, price),
        }

    plot_data = gs.plot_data
    plot_data["stock_market"] = prices
    gs.plot_data = plot_data


def tick_stocks(gs):
    """Fluctuate stock prices -- called every STOCK_TICK_INTERVAL ticks."""
    from .constants import STOCK_VOLATILITY, STOCK_SENTIMENT_DECAY

    plot_data = gs.plot_data
    market = plot_data.get("stock_market")
    if not market:
        return

    for name, data in market.items():
        price = data["price"]
        sentiment = data.get("sentiment", 0.0)

        # Random walk: -VOLATILITY to +VOLATILITY, biased by sentiment
        drift = sentiment * 0.01  # sentiment of 3 -> +3% drift
        change_pct = random.uniform(-STOCK_VOLATILITY, STOCK_VOLATILITY) + drift
        new_price = int(price * (1 + change_pct))
        new_price = max(5, new_price)  # floor at 5c

        # Decay sentiment toward 0
        new_sentiment = sentiment * STOCK_SENTIMENT_DECAY
        if abs(new_sentiment) < 0.1:
            new_sentiment = 0.0

        data["prev_price"] = price
        data["price"] = new_price
        data["sentiment"] = new_sentiment

    plot_data["stock_market"] = market
    gs.plot_data = plot_data


def add_sentiment(gs, company_name, amount):
    """Add sentiment to a company's stock (positive=bullish, negative=bearish)."""
    plot_data = gs.plot_data
    market = plot_data.get("stock_market")
    if not market or company_name not in market:
        return
    market[company_name]["sentiment"] = market[company_name].get("sentiment", 0.0) + amount
    # Cap sentiment at +/-5
    market[company_name]["sentiment"] = max(-5, min(5, market[company_name]["sentiment"]))
    plot_data["stock_market"] = market
    gs.plot_data = plot_data


def buy_shares(gs, company_name, num_shares):
    """Buy shares. Returns (success, message)."""
    plot_data = gs.plot_data
    market = plot_data.get("stock_market", {})
    if company_name not in market:
        return False, f"Company '{company_name}' not listed on the exchange."

    price = market[company_name]["price"]
    total_cost = price * num_shares

    if gs.balance < total_cost:
        return False, f"Insufficient funds. Need {total_cost:,}c, have {gs.balance:,}c."

    # Deduct credits
    gs.balance -= total_cost

    # Update or create holding
    holding = StockHolding.query.filter_by(
        game_session_id=gs.id, company_name=company_name
    ).first()
    if holding:
        # Weighted average buy price
        old_total = holding.shares * holding.avg_buy_price
        new_total = old_total + total_cost
        holding.shares += num_shares
        holding.avg_buy_price = new_total // holding.shares if holding.shares > 0 else price
    else:
        holding = StockHolding(
            game_session_id=gs.id,
            company_name=company_name,
            shares=num_shares,
            avg_buy_price=price,
        )
        db.session.add(holding)

    db.session.commit()
    return True, (
        f"Bought {num_shares} share(s) of {company_name} at {price}c each. "
        f"Total: {total_cost:,}c. Balance: {gs.balance:,}c."
    )


def sell_shares(gs, company_name, num_shares):
    """Sell shares. Returns (success, message)."""
    plot_data = gs.plot_data
    market = plot_data.get("stock_market", {})
    if company_name not in market:
        return False, f"Company '{company_name}' not listed on the exchange."

    holding = StockHolding.query.filter_by(
        game_session_id=gs.id, company_name=company_name
    ).first()
    if not holding or holding.shares < num_shares:
        owned = holding.shares if holding else 0
        return False, f"You only own {owned} share(s) of {company_name}."

    price = market[company_name]["price"]
    total_revenue = price * num_shares

    # Credit player
    gs.balance += total_revenue
    holding.shares -= num_shares

    # Clean up empty holdings
    if holding.shares <= 0:
        db.session.delete(holding)

    db.session.commit()

    return True, (
        f"Sold {num_shares} share(s) of {company_name} at {price}c each. "
        f"Revenue: {total_revenue:,}c. Balance: {gs.balance:,}c."
    )


def get_portfolio(gs):
    """Get player's stock holdings with current values."""
    holdings = StockHolding.query.filter_by(game_session_id=gs.id).all()
    market = gs.plot_data.get("stock_market", {})

    portfolio = []
    total_value = 0
    total_cost = 0
    for h in holdings:
        if h.shares <= 0:
            continue
        current_price = market.get(h.company_name, {}).get("price", 0)
        value = current_price * h.shares
        cost = h.avg_buy_price * h.shares
        profit = value - cost
        portfolio.append({
            "company": h.company_name,
            "shares": h.shares,
            "avg_price": h.avg_buy_price,
            "current_price": current_price,
            "value": value,
            "profit": profit,
        })
        total_value += value
        total_cost += cost

    return portfolio, total_value, total_cost
