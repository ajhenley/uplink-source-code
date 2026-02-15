"""News article generation for the Uplink News Network."""

import random

from ..extensions import db
from ..models import Computer, DataFile
from .constants import (
    IP_NEWS_NETWORK, MAX_NEWS_ARTICLES, NEWS_RANDOM_EVENTS, COMPANY_NAMES,
)


def generate_news_article(game_session_id, headline, body, source, tick):
    """Create a news article as a DataFile on the news computer.

    Trims oldest articles beyond MAX_NEWS_ARTICLES.
    """
    news_comp = Computer.query.filter_by(
        game_session_id=game_session_id, ip=IP_NEWS_NETWORK
    ).first()
    if not news_comp:
        return

    article = DataFile(
        computer_id=news_comp.id,
        filename=f"news_{tick}.dat",
        size=1,
        file_type="NEWS",
    )
    article.content = {
        "headline": headline,
        "body": body,
        "source": source,
        "tick": tick,
    }
    db.session.add(article)

    # Trim oldest articles beyond cap
    all_articles = (
        DataFile.query
        .filter_by(computer_id=news_comp.id, file_type="NEWS")
        .order_by(DataFile.id.desc())
        .all()
    )
    # +1 because we just added one that may not be flushed yet
    if len(all_articles) >= MAX_NEWS_ARTICLES:
        for old in all_articles[MAX_NEWS_ARTICLES - 1:]:
            db.session.delete(old)


def generate_random_news(game_session_id, tick):
    """Generate a random news article from the template pool."""
    company = random.choice(COMPANY_NAMES)
    template = random.choice(NEWS_RANDOM_EVENTS)
    headline = template.format(company=company)
    body = (
        f"{headline}.\n\n"
        f"Sources close to {company} confirmed the development today.\n"
        f"Further details are expected in the coming days."
    )
    generate_news_article(game_session_id, headline, body, "Uplink News Network", tick)
