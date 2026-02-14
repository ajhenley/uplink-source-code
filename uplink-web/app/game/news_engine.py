"""News generation engine -- procedural news articles triggered by game events."""
import logging
import random

from app.extensions import db
from app.models.news import NewsArticle
from app.game import constants as C
from app.game.name_generator import generate_name, generate_company_name

log = logging.getLogger(__name__)

# ============================================================
# Timing constants
# ============================================================

# How many game-time ticks between ambient news generation cycles
AMBIENT_NEWS_TICK_INTERVAL = 6000  # roughly every 20 game-minutes at 5 ticks/min

# News article expiry (in ticks) -- matches C.TIME_TOEXPIRENEWS * 5
NEWS_EXPIRY_TICKS = C.TIME_TOEXPIRENEWS * 5

# Maximum ambient articles generated per cycle
AMBIENT_MAX_PER_CYCLE = 2

# Probability (0-1) of generating an ambient article each cycle
AMBIENT_GENERATION_PROBABILITY = 0.40


# ============================================================
# Article templates keyed by event_type
# ============================================================

_TEMPLATES = {
    "arrest": {
        "headlines": [
            "Hacker '{agent_name}' Arrested by Federal Agents",
            "Uplink Agent '{agent_name}' Seized in Dawn Raid",
            "Cybercriminal '{agent_name}' Apprehended",
            "Federal Bureau Arrests Notorious Hacker '{agent_name}'",
            "'{agent_name}' Taken Into Custody After Hacking Spree",
        ],
        "bodies": [
            (
                "Federal Investigation Bureau agents stormed the gateway of the "
                "hacker known as '{agent_name}' early this morning. The suspect is "
                "believed to have been involved in multiple unauthorized computer "
                "intrusions over recent weeks. Equipment was confiscated and the "
                "suspect's Uplink account has been suspended pending trial."
            ),
            (
                "Authorities have confirmed the arrest of '{agent_name}', a "
                "freelance hacker operating through the Uplink network. Sources "
                "close to the investigation say the suspect failed to adequately "
                "cover their tracks after a recent intrusion. If convicted, "
                "'{agent_name}' faces up to 15 years in federal custody."
            ),
        ],
        "category": "crime",
    },
    "company_hack": {
        "headlines": [
            "{company_name} Suffers Major Security Breach",
            "Hackers Penetrate {company_name} Mainframe",
            "{company_name} Data Compromised in Cyber Attack",
            "Security Failure at {company_name} Exposes Sensitive Files",
            "{company_name} Internal Systems Breached by Unknown Hacker",
        ],
        "bodies": [
            (
                "{company_name} confirmed today that their internal computer "
                "systems were accessed by an unauthorized third party. A "
                "spokesperson said that the breach was detected by their security "
                "monitoring systems but not before significant data was accessed. "
                "The company has engaged forensic investigators and is cooperating "
                "with federal authorities."
            ),
            (
                "Shares in {company_name} fell sharply after reports emerged that "
                "hackers had penetrated the company's central mainframe. Industry "
                "analysts warn that the breach could have serious implications for "
                "the company's competitive position. {company_name} has declined "
                "to comment on the nature of the data stolen."
            ),
        ],
        "category": "corporate",
    },
    "stock_crash": {
        "headlines": [
            "{company_name} Shares Plummet After Financial Irregularities",
            "Stock Market Turmoil: {company_name} Loses {percent}%",
            "Investors Flee {company_name} as Share Price Collapses",
            "Trading Halted on {company_name} After Dramatic Sell-Off",
        ],
        "bodies": [
            (
                "Shares in {company_name} lost {percent}% of their value in "
                "frantic trading today amid rumours of financial irregularities. "
                "The crash wiped millions off the company's market capitalisation. "
                "Regulators are examining whether insider trading or external "
                "manipulation may have contributed to the sudden decline."
            ),
            (
                "The stock market was rocked today as {company_name} experienced "
                "its worst single-day loss in history. Analysts attributed the "
                "sell-off to concerns about data integrity in the company's "
                "financial systems. There is speculation that hackers may have "
                "tampered with the company's accounting records."
            ),
        ],
        "category": "financial",
    },
    "revelation_spread": {
        "headlines": [
            "Mystery Virus Spreads to New Systems",
            "Revelation Virus Claims Another Network",
            "Unstoppable Digital Plague Continues to Spread",
            "Computer Scientists Baffled by Self-Replicating Code",
        ],
        "bodies": [
            (
                "The so-called 'Revelation' virus has been detected on yet more "
                "computer systems worldwide. The virus, which appears to destroy "
                "all data on infected machines, has so far resisted all attempts "
                "at containment. Leading anti-virus researchers admit they have "
                "never seen anything like it. Internet traffic continues to be "
                "disrupted as administrators scramble to isolate affected systems."
            ),
            (
                "Officials today confirmed that the Revelation virus has spread "
                "to an additional {count} systems. The self-replicating program "
                "continues to evade all known counter-measures. Government "
                "cybersecurity advisors have issued an emergency alert urging all "
                "organisations to disconnect non-essential systems from the network "
                "until further notice."
            ),
        ],
        "category": "technology",
    },
    "system_failure": {
        "headlines": [
            "{system_name} Experiences Critical System Failure",
            "Major Outage Hits {system_name}",
            "{system_name} Goes Offline After Hardware Failure",
            "Users Report Widespread {system_name} Downtime",
        ],
        "bodies": [
            (
                "{system_name} suffered a critical failure today, leaving "
                "thousands of users without access to essential services. "
                "Engineers are working around the clock to restore operations. "
                "A spokesperson attributed the outage to 'an unexpected hardware "
                "malfunction' but declined to rule out external interference."
            ),
            (
                "Operations at {system_name} ground to a halt this morning after "
                "a catastrophic system failure. Backup systems also failed to "
                "engage, suggesting possible sabotage. Federal investigators have "
                "been called in to determine whether the outage was the result of "
                "a deliberate cyber attack."
            ),
        ],
        "category": "technology",
    },
    "agent_promotion": {
        "headlines": [
            "Uplink Agent '{agent_name}' Achieves {rating_name} Status",
            "'{agent_name}' Rises Through Uplink Ranks to {rating_name}",
            "Rising Star: '{agent_name}' Now Rated {rating_name}",
        ],
        "bodies": [
            (
                "The Uplink Corporation has confirmed that agent '{agent_name}' "
                "has been promoted to {rating_name} status. The promotion follows "
                "a string of successful operations and reflects the agent's "
                "growing reputation within the hacking community. '{agent_name}' "
                "is now ranked among the top operatives on the network."
            ),
            (
                "Sources within Uplink Corporation report that '{agent_name}' has "
                "achieved the coveted {rating_name} rating. Industry watchers note "
                "that few agents reach this level, and those who do tend to attract "
                "the attention of both employers and law enforcement in equal measure."
            ),
        ],
        "category": "community",
    },
}

# Ambient/random news -- not tied to a specific game event
_AMBIENT_HEADLINES = [
    "Global Internet Traffic Reaches New Record High",
    "Government Proposes Stricter Cybercrime Legislation",
    "Uplink Corporation Reports Record Quarterly Profits",
    "New Encryption Standard Proposed by International Committee",
    "Debate Rages Over Digital Privacy Rights",
    "Tech Giants Invest Billions in Quantum Computing Research",
    "Cybersecurity Experts Warn of Rising Threat Landscape",
    "International Academic Database Celebrates 10 Million Records",
    "Federal Bureau Announces New Cybercrime Task Force",
    "Stock Market Reaches All-Time High on Tech Sector Strength",
    "Analysts Predict Surge in Corporate Espionage",
    "Internet Freedom Group Condemns Government Monitoring",
    "New Gateway Hardware Announced by Leading Manufacturer",
    "Social Security Database Upgrade Completed Successfully",
    "Central Medical Database Expands Coverage to New Regions",
    "InterNIC Reports Domain Registration Boom",
    "Software Piracy Costs Industry Billions Annually",
    "Virtual Reality Interfaces Gaining Traction in Corporate Sector",
    "Artificial Intelligence Lab Announces Breakthrough",
    "Cloud Computing Adoption Accelerates Worldwide",
]

_AMBIENT_BODIES = [
    (
        "In a report released today, analysts noted that global internet traffic "
        "has reached unprecedented levels. The growth is attributed to increased "
        "corporate connectivity and the proliferation of always-on gateway systems. "
        "Network engineers warn that infrastructure may struggle to keep pace with "
        "demand in the coming years."
    ),
    (
        "Industry observers report a significant shift in the digital landscape "
        "as more organisations embrace connected systems. Experts warn that this "
        "increased connectivity also brings heightened security risks, with "
        "corporate espionage and data theft on the rise. Companies are urged to "
        "invest in robust security measures."
    ),
    (
        "A new study from the International Computing Research Institute suggests "
        "that cybercrime costs the global economy over 200 billion credits "
        "annually. The report calls for greater cooperation between law "
        "enforcement agencies and the private sector to combat the growing threat."
    ),
    (
        "Technology sector stocks continued their upward trend today, buoyed by "
        "strong earnings reports from several major corporations. Market analysts "
        "remain cautiously optimistic, though some warn that current valuations "
        "may not be sustainable in the long term."
    ),
    (
        "Digital rights advocates have raised concerns about proposed new "
        "legislation that would grant law enforcement expanded powers to monitor "
        "internet communications. Critics argue the measures go too far and could "
        "be used to target legitimate privacy tools used by ordinary citizens."
    ),
]


# ============================================================
# Public API
# ============================================================

def generate_news(session_id, event_type, current_tick=0, **kwargs):
    """Generate a news article based on a game event.

    Parameters
    ----------
    session_id : str
        The game session this article belongs to.
    event_type : str
        One of: ``"arrest"``, ``"company_hack"``, ``"stock_crash"``,
        ``"revelation_spread"``, ``"system_failure"``, ``"agent_promotion"``.
    current_tick : int
        Current game-time tick (used for timestamps and expiry).
    **kwargs
        Template variables such as ``agent_name``, ``company_name``,
        ``percent``, ``count``, ``system_name``, ``rating_name``.

    Returns
    -------
    dict
        A dict representation of the created ``NewsArticle``.
    """
    rng = random.Random()

    template = _TEMPLATES.get(event_type)
    if template is None:
        log.warning("Unknown news event_type: %s -- generating generic article", event_type)
        return _generate_ambient_article(session_id, current_tick, rng)

    # Fill in default placeholder values if not supplied
    defaults = _build_defaults(rng)
    merged = {**defaults, **kwargs}

    headline = rng.choice(template["headlines"]).format_map(_SafeFormatDict(merged))
    body = rng.choice(template["bodies"]).format_map(_SafeFormatDict(merged))
    category = template.get("category", "general")

    article = NewsArticle(
        game_session_id=session_id,
        headline=headline[:256],
        body=body[:4096],
        category=category,
        created_at_tick=current_tick,
        expires_at_tick=current_tick + NEWS_EXPIRY_TICKS,
    )
    db.session.add(article)
    db.session.flush()

    log.debug("Generated news [%s]: %s", event_type, headline)
    return _article_to_dict(article)


def get_recent_news(session_id, limit=20):
    """Get the most recent news articles for a session.

    Returns a list of dicts ordered newest-first.
    """
    articles = NewsArticle.query.filter(
        NewsArticle.game_session_id == session_id,
    ).order_by(NewsArticle.created_at_tick.desc()).limit(limit).all()

    return [_article_to_dict(a) for a in articles]


def tick_news(session_id, current_tick):
    """Generate ambient/random news periodically.

    Should be called every tick; the function gates itself internally based on
    ``AMBIENT_NEWS_TICK_INTERVAL``.

    Returns a list of event dicts for any articles created.
    """
    if current_tick % AMBIENT_NEWS_TICK_INTERVAL != 0:
        return []

    rng = random.Random()
    events = []

    # Expire old articles
    _expire_old_news(session_id, current_tick)

    count = rng.randint(1, AMBIENT_MAX_PER_CYCLE)
    for _ in range(count):
        if rng.random() > AMBIENT_GENERATION_PROBABILITY:
            continue
        article_dict = _generate_ambient_article(session_id, current_tick, rng)
        if article_dict:
            events.append({
                "type": "news_published",
                "session_id": session_id,
                "article": article_dict,
            })

    db.session.flush()
    return events


# ============================================================
# Internal helpers
# ============================================================

class _SafeFormatDict(dict):
    """A dict subclass that returns the key name wrapped in braces for missing keys,
    preventing KeyError in str.format_map calls."""

    def __missing__(self, key):
        return "{" + key + "}"


def _build_defaults(rng):
    """Build sensible default placeholder values for templates."""
    return {
        "agent_name": generate_name(rng),
        "company_name": generate_company_name(rng),
        "percent": str(rng.randint(5, 45)),
        "count": str(rng.randint(3, 50)),
        "system_name": rng.choice([
            "International Academic Database",
            "Global Criminal Database",
            "Social Security Database",
            "Central Medical Database",
            "InterNIC",
            "Stock Market System",
        ]),
        "rating_name": rng.choice([name for name, _ in C.UPLINKRATING[3:]]),
    }


def _generate_ambient_article(session_id, current_tick, rng):
    """Create a single ambient/filler news article."""
    headline = rng.choice(_AMBIENT_HEADLINES)
    body = rng.choice(_AMBIENT_BODIES)

    article = NewsArticle(
        game_session_id=session_id,
        headline=headline[:256],
        body=body[:4096],
        category="general",
        created_at_tick=current_tick,
        expires_at_tick=current_tick + NEWS_EXPIRY_TICKS,
    )
    db.session.add(article)
    db.session.flush()

    log.debug("Generated ambient news: %s", headline)
    return _article_to_dict(article)


def _expire_old_news(session_id, current_tick):
    """Delete news articles that have passed their expiry tick."""
    expired = NewsArticle.query.filter(
        NewsArticle.game_session_id == session_id,
        NewsArticle.expires_at_tick != None,  # noqa: E711
        NewsArticle.expires_at_tick <= current_tick,
    ).all()

    for article in expired:
        db.session.delete(article)

    if expired:
        log.debug("Expired %d old news articles for session %s", len(expired), session_id)


def _article_to_dict(article):
    """Convert a NewsArticle ORM instance to a plain dict."""
    return {
        "id": article.id,
        "headline": article.headline,
        "body": article.body,
        "category": article.category,
        "created_at_tick": article.created_at_tick,
        "expires_at_tick": article.expires_at_tick,
    }
