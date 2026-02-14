"""Plot engine -- implements the Revelation/Faith 6-act background story.

This is a faithful port of PlotGenerator from the original C++ source
(uplink/src/world/generator/plotgenerator.cpp). The plot is a state machine
driven by game ticks, generating news articles and player messages as it
advances through 6 acts:

  Act 1 - Discovery:   ARC begins work on Revelation; news and suspicion build.
  Act 2 - Contact:     Player contacted by both sides; chooses Arunmor or ARC.
  Act 3 - Missions:    Side-specific plot missions; Revelation details emerge.
  Act 4 - Escalation:  Special missions (Tracer, Darwin, etc.); virus spreading.
  Act 5 - Climax:      Final mission -- deploy Faith or launch Revelation.
  Act 6 - Resolution:  Andromeda leader jailed (Arunmor) or Internet destroyed (ARC).

Plot state is tracked in-memory keyed by session_id. This is acceptable for the
web port since state is reconstructed on server restart and the plot is driven by
tick_plot() calls from the game loop.
"""

import logging

from app.extensions import db
from app.models.message import Message
from app.models.news import NewsArticle
from app.models.player import Player
from app.models.game_session import GameSession
from app.game import constants as C

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Plot state constants
# ---------------------------------------------------------------------------

PLOT_STATES = {
    "inactive": 0,
    "act1_discovery": 1,
    "act2_contact": 2,
    "act2_choice_arunmor": 3,
    "act2_choice_arc": 4,
    "act3_arunmor_missions": 5,
    "act3_arc_missions": 6,
    "act4_escalation": 7,
    "act5_climax": 8,
    "act6_arunmor_victory": 9,
    "act6_arc_victory": 10,
}

# Reverse lookup: numeric value -> name
_STATE_NAMES = {v: k for k, v in PLOT_STATES.items()}

# Tick thresholds at which each act transition fires.
# These mirror the original C++ timing where scenes were scheduled
# days apart; here we use absolute tick counts for simplicity.
TICK_ACT1_START = 5000
TICK_ACT1_SCENE2 = 5000       # "Unusual hiring practices" news
TICK_ACT1_SCENE3 = 7000       # Agent raises doubts over ARC
TICK_ACT1_SCENE4 = 8500       # Top agent reassures community
TICK_ACT1_SCENE5 = 11000      # Top agent found dead
TICK_ACT1_SCENE7 = 13000      # Delayed warning email from dead agent
TICK_ACT1_SCENE8 = 13500      # Uplink issues formal warning

TICK_ACT2_START = 15000
TICK_ACT2_SCENE1 = 15000      # "Maiden Flight" mission offered
TICK_ACT2_SCENE2 = 18000      # Another agent completes Maiden Flight
TICK_ACT2_SCENE3 = 20000      # Arunmor contacts player

TICK_ACT3_START = 22000
TICK_ACT3_SCENE1 = 22000      # News story about Revelation attack
TICK_ACT3_SCENE2 = 23500      # Arunmor announces Faith project
TICK_ACT3_SCENE3 = 25000      # Arunmor releases Revelation details
TICK_ACT3_SCENE4 = 27000      # Feds reveal ARC is run by Andromeda

TICK_ACT4_START = 29000
TICK_ACT4_SCENE1 = 29000      # "Tracer" mission put out
TICK_ACT4_SCENE4 = 30500      # News story about Tracer
TICK_ACT4_SCENE7 = 32000      # "Darwin" mission put out
TICK_ACT4_SCENE10 = 33500     # News story about Darwin

TICK_ACT5_START = 35000
TICK_ACT5_SCENE1 = 35000      # Revelation launch imminent
TICK_ACT5_SCENE2 = 36000      # Final missions: GrandTour / CounterAttack

TICK_ACT6_START = 40000
TICK_ACT6_SCENE1 = 40000      # Andromeda leader press statement
TICK_ACT6_SCENE2 = 43000      # Leader jailed
TICK_ACT6_SCENE3 = 45000      # Retrospective

# ---------------------------------------------------------------------------
# Special mission IDs (match C++ defines)
# ---------------------------------------------------------------------------

SPECIALMISSION_BACKFIRE = 0
SPECIALMISSION_TRACER = 1
SPECIALMISSION_TAKEMETOYOURLEADER = 2
SPECIALMISSION_ARCINFILTRATION = 3
SPECIALMISSION_COUNTERATTACK = 4
SPECIALMISSION_MAIDENFLIGHT = 5
SPECIALMISSION_DARWIN = 6
SPECIALMISSION_SAVEITFORTHEJURY = 7
SPECIALMISSION_SHINYHAMMER = 8
SPECIALMISSION_GRANDTOUR = 9

SPECIAL_MISSION_TITLES = {
    SPECIALMISSION_BACKFIRE: "Backfire",
    SPECIALMISSION_TRACER: "Tracer",
    SPECIALMISSION_TAKEMETOYOURLEADER: "TakeMeToYourLeader",
    SPECIALMISSION_ARCINFILTRATION: "ARCInfiltration",
    SPECIALMISSION_COUNTERATTACK: "CounterAttack",
    SPECIALMISSION_MAIDENFLIGHT: "MaidenFlight",
    SPECIALMISSION_DARWIN: "Darwin",
    SPECIALMISSION_SAVEITFORTHEJURY: "SaveItForTheJury",
    SPECIALMISSION_SHINYHAMMER: "ShinyHammer",
    SPECIALMISSION_GRANDTOUR: "GrandTour",
}

SPECIAL_MISSION_DESCRIPTIONS = {
    SPECIALMISSION_BACKFIRE: "Counter attack!",
    SPECIALMISSION_TRACER: "Perform a covert installation of a Tracer",
    SPECIALMISSION_TAKEMETOYOURLEADER: "Help bring the CEO of a major company into custody",
    SPECIALMISSION_ARCINFILTRATION: "Take advantage of an amazing opportunity",
    SPECIALMISSION_COUNTERATTACK: "Prevent the outbreak of Revelation",
    SPECIALMISSION_MAIDENFLIGHT: "Test run Revelation Version 1.0",
    SPECIALMISSION_DARWIN: "Steal vital Research into Digital Life Forms",
    SPECIALMISSION_SAVEITFORTHEJURY: "Frame the chief tech of Arunmor Corporation",
    SPECIALMISSION_SHINYHAMMER: "Destroy all research completed by Arunmor",
    SPECIALMISSION_GRANDTOUR: "Release the Revelation Virus into the wild",
}

SPECIAL_MISSION_PAYMENTS = {
    SPECIALMISSION_BACKFIRE: C.PAYMENT_SPECIALMISSION_BACKFIRE,
    SPECIALMISSION_TRACER: C.PAYMENT_SPECIALMISSION_TRACER,
    SPECIALMISSION_TAKEMETOYOURLEADER: C.PAYMENT_SPECIALMISSION_TAKEMETOYOURLEADER,
    SPECIALMISSION_ARCINFILTRATION: C.PAYMENT_SPECIALMISSION_ARCINFILTRATION,
    SPECIALMISSION_COUNTERATTACK: C.PAYMENT_SPECIALMISSION_COUNTERATTACK,
    SPECIALMISSION_MAIDENFLIGHT: C.PAYMENT_SPECIALMISSION_MAIDENFLIGHT,
    SPECIALMISSION_DARWIN: C.PAYMENT_SPECIALMISSION_DARWIN,
    SPECIALMISSION_SAVEITFORTHEJURY: C.PAYMENT_SPECIALMISSION_SAVEITFORTHEJURY,
    SPECIALMISSION_SHINYHAMMER: C.PAYMENT_SPECIALMISSION_SHINYHAMMER,
    SPECIALMISSION_GRANDTOUR: C.PAYMENT_SPECIALMISSION_GRANDTOUR,
}

# Arunmor missions (loyalty == 1)
ARUNMOR_MISSIONS = [
    SPECIALMISSION_TRACER,
    SPECIALMISSION_TAKEMETOYOURLEADER,
    SPECIALMISSION_ARCINFILTRATION,
    SPECIALMISSION_COUNTERATTACK,
]

# ARC missions (loyalty == -1)
ARC_MISSIONS = [
    SPECIALMISSION_MAIDENFLIGHT,
    SPECIALMISSION_DARWIN,
    SPECIALMISSION_SAVEITFORTHEJURY,
    SPECIALMISSION_SHINYHAMMER,
    SPECIALMISSION_GRANDTOUR,
]

# Mission type code used for plot/special missions in the Mission model.
TYPE_SPECIAL = 0

# ---------------------------------------------------------------------------
# In-memory plot state storage (keyed by session_id)
# ---------------------------------------------------------------------------


class _PlotState:
    """Per-session plot state, mirrors PlotGenerator member variables from C++."""

    __slots__ = (
        "state",
        "act",
        "scene",
        "player_loyalty",       # 0 = none, 1 = Arunmor, -1 = ARC
        "version_revelation",
        "version_faith",
        "num_uses_revelation",
        "infected_ips",
        "revelation_release_uncontrolled",
        "revelation_release_failed",
        "revelation_arc_busted",
        "special_missions_completed",
        "scenes_run",           # set of (act, scene) tuples already executed
    )

    def __init__(self):
        self.state = PLOT_STATES["inactive"]
        self.act = 0
        self.scene = 0
        self.player_loyalty = 0
        self.version_revelation = 0.0
        self.version_faith = 0.0
        self.num_uses_revelation = 0
        self.infected_ips = []
        self.revelation_release_uncontrolled = False
        self.revelation_release_failed = False
        self.revelation_arc_busted = False
        self.special_missions_completed = 0  # bitfield
        self.scenes_run = set()


# Module-level registry -- survives within the process lifetime.
_plot_states = {}  # type: dict[str, _PlotState]


def _get_ps(session_id):
    """Return or create the _PlotState for a session."""
    if session_id not in _plot_states:
        _plot_states[session_id] = _PlotState()
    return _plot_states[session_id]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def tick_plot(session_id, current_tick):
    """Called by the game loop each tick to advance the plot state machine.

    Checks whether the current tick has crossed any scene threshold and
    runs the corresponding scene handler exactly once.  Returns a list of
    dicts describing any broadcast-worthy events produced this tick.
    """
    ps = _get_ps(session_id)
    events = []

    # Scene dispatch table: (tick_threshold, act, scene, handler)
    _SCENE_TABLE = [
        # Act 1 -- Discovery
        (TICK_ACT1_SCENE2, 1, 2, _run_act1_scene2),
        (TICK_ACT1_SCENE3, 1, 3, _run_act1_scene3),
        (TICK_ACT1_SCENE4, 1, 4, _run_act1_scene4),
        (TICK_ACT1_SCENE5, 1, 5, _run_act1_scene5),
        (TICK_ACT1_SCENE7, 1, 7, _run_act1_scene7),
        (TICK_ACT1_SCENE8, 1, 8, _run_act1_scene8),
        # Act 2 -- Contact
        (TICK_ACT2_SCENE1, 2, 1, _run_act2_scene1),
        (TICK_ACT2_SCENE2, 2, 2, _run_act2_scene2),
        (TICK_ACT2_SCENE3, 2, 3, _run_act2_scene3),
        # Act 3 -- Missions
        (TICK_ACT3_SCENE1, 3, 1, _run_act3_scene1),
        (TICK_ACT3_SCENE2, 3, 2, _run_act3_scene2),
        (TICK_ACT3_SCENE3, 3, 3, _run_act3_scene3),
        (TICK_ACT3_SCENE4, 3, 4, _run_act3_scene4),
        # Act 4 -- Escalation
        (TICK_ACT4_SCENE1, 4, 1, _run_act4_scene1),
        (TICK_ACT4_SCENE4, 4, 4, _run_act4_scene4),
        (TICK_ACT4_SCENE7, 4, 7, _run_act4_scene7),
        (TICK_ACT4_SCENE10, 4, 10, _run_act4_scene10),
        # Act 5 -- Climax
        (TICK_ACT5_SCENE1, 5, 1, _run_act5_scene1),
        (TICK_ACT5_SCENE2, 5, 2, _run_act5_scene2),
        # Act 6 -- Resolution
        (TICK_ACT6_SCENE1, 6, 1, _run_act6_scene1),
        (TICK_ACT6_SCENE2, 6, 2, _run_act6_scene2),
        (TICK_ACT6_SCENE3, 6, 3, _run_act6_scene3),
    ]

    for tick_threshold, act, scene, handler in _SCENE_TABLE:
        if current_tick >= tick_threshold and (act, scene) not in ps.scenes_run:
            # Scenes must run in order -- skip if a prior scene in the same
            # act has not run yet.
            if not _prerequisites_met(ps, act, scene):
                continue
            ps.scenes_run.add((act, scene))
            ps.act = act
            ps.scene = scene
            _update_state_from_act(ps, act)
            result = handler(session_id, ps, current_tick)
            if result:
                events.extend(result if isinstance(result, list) else [result])
            log.info("Plot: session=%s act=%d scene=%d at tick=%d",
                     session_id, act, scene, current_tick)

    return events


def choose_side(session_id, side):
    """Player chooses Arunmor (side='arunmor') or ARC (side='arc').

    Returns a dict with the updated plot state.
    """
    ps = _get_ps(session_id)

    if side == "arunmor":
        ps.player_loyalty = 1
        ps.state = PLOT_STATES["act2_choice_arunmor"]
    elif side == "arc":
        ps.player_loyalty = -1
        ps.state = PLOT_STATES["act2_choice_arc"]
    else:
        raise ValueError(f"Invalid side: {side!r}. Must be 'arunmor' or 'arc'.")

    log.info("Plot: session=%s chose side=%s (loyalty=%d)",
             session_id, side, ps.player_loyalty)

    return get_plot_state(session_id)


def get_plot_state(session_id):
    """Return current plot state and relevant data as a dict."""
    ps = _get_ps(session_id)
    return {
        "state": ps.state,
        "state_name": _STATE_NAMES.get(ps.state, "unknown"),
        "act": ps.act,
        "scene": ps.scene,
        "player_loyalty": ps.player_loyalty,
        "player_loyalty_name": _loyalty_name(ps.player_loyalty),
        "version_revelation": ps.version_revelation,
        "version_faith": ps.version_faith,
        "num_uses_revelation": ps.num_uses_revelation,
        "infected_count": len(ps.infected_ips),
        "infected_ips": list(ps.infected_ips),
        "revelation_release_uncontrolled": ps.revelation_release_uncontrolled,
        "revelation_arc_busted": ps.revelation_arc_busted,
        "special_missions_completed": _decode_special_missions(ps.special_missions_completed),
    }


def get_plot_missions(session_id):
    """Get available plot-specific missions for the current session.

    Returns a list of dicts describing special missions the player can accept
    based on their current loyalty and plot progress.
    """
    ps = _get_ps(session_id)

    if ps.player_loyalty == 0:
        return []

    pool = ARUNMOR_MISSIONS if ps.player_loyalty == 1 else ARC_MISSIONS
    missions = []

    for mission_id in pool:
        if _has_completed_special(ps, mission_id):
            continue
        missions.append({
            "special_mission_id": mission_id,
            "title": SPECIAL_MISSION_TITLES.get(mission_id, "Unknown"),
            "description": SPECIAL_MISSION_DESCRIPTIONS.get(mission_id, ""),
            "payment": SPECIAL_MISSION_PAYMENTS.get(mission_id, 0),
            "employer": "Arunmor" if ps.player_loyalty == 1 else "ARC",
            "completed": False,
        })

    return missions


def complete_special_mission(session_id, mission_id):
    """Mark a special mission as completed and reward the player.

    Returns a dict with payment and updated state info.
    """
    ps = _get_ps(session_id)
    if _has_completed_special(ps, mission_id):
        return {"error": "Mission already completed"}

    ps.special_missions_completed |= (1 << mission_id)
    payment = SPECIAL_MISSION_PAYMENTS.get(mission_id, 0)

    player = Player.query.filter_by(game_session_id=session_id).first()
    if player and payment > 0:
        player.balance += payment
        employer = "Arunmor" if ps.player_loyalty == 1 else "ARC"
        title = SPECIAL_MISSION_TITLES.get(mission_id, "Special Mission")
        db.session.add(Message(
            game_session_id=session_id,
            player_id=player.id,
            from_name=employer,
            subject=f"Mission Complete: {title} -- {payment}c credited",
            body=(
                f"Agent,\n\n"
                f"Excellent work on the {title} operation.\n\n"
                f"Payment of {payment}c has been credited to your account.\n"
                f"Your current balance is {player.balance}c.\n\n"
                f"- {employer}"
            ),
        ))
        db.session.flush()

    # Advance Revelation/Faith versions based on mission
    if mission_id in (SPECIALMISSION_MAIDENFLIGHT, SPECIALMISSION_DARWIN,
                      SPECIALMISSION_GRANDTOUR):
        ps.version_revelation = round(ps.version_revelation + 1.0, 1)
    elif mission_id in (SPECIALMISSION_TRACER, SPECIALMISSION_ARCINFILTRATION,
                        SPECIALMISSION_COUNTERATTACK):
        ps.version_faith = round(ps.version_faith + 1.0, 1)

    log.info("Plot: session=%s completed special mission %d (%s)",
             session_id, mission_id,
             SPECIAL_MISSION_TITLES.get(mission_id, "?"))

    return {
        "mission_id": mission_id,
        "title": SPECIAL_MISSION_TITLES.get(mission_id, "Unknown"),
        "payment": payment,
        "balance": player.balance if player else 0,
        "version_revelation": ps.version_revelation,
        "version_faith": ps.version_faith,
    }


def reset_plot(session_id):
    """Remove all plot state for a session (used on session deletion)."""
    _plot_states.pop(session_id, None)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _loyalty_name(loyalty):
    if loyalty == 1:
        return "Arunmor"
    elif loyalty == -1:
        return "ARC"
    return "none"


def _has_completed_special(ps, mission_id):
    return bool(ps.special_missions_completed & (1 << mission_id))


def _decode_special_missions(bitfield):
    """Return a list of completed special mission IDs from the bitfield."""
    completed = []
    for mid in SPECIAL_MISSION_TITLES:
        if bitfield & (1 << mid):
            completed.append(mid)
    return completed


def _update_state_from_act(ps, act):
    """Set the coarse plot state based on which act we are in."""
    if act == 1:
        ps.state = PLOT_STATES["act1_discovery"]
    elif act == 2:
        if ps.player_loyalty == 1:
            ps.state = PLOT_STATES["act2_choice_arunmor"]
        elif ps.player_loyalty == -1:
            ps.state = PLOT_STATES["act2_choice_arc"]
        else:
            ps.state = PLOT_STATES["act2_contact"]
    elif act == 3:
        if ps.player_loyalty == 1:
            ps.state = PLOT_STATES["act3_arunmor_missions"]
        else:
            ps.state = PLOT_STATES["act3_arc_missions"]
    elif act == 4:
        ps.state = PLOT_STATES["act4_escalation"]
    elif act == 5:
        ps.state = PLOT_STATES["act5_climax"]
    elif act == 6:
        if ps.revelation_release_uncontrolled:
            ps.state = PLOT_STATES["act6_arc_victory"]
        else:
            ps.state = PLOT_STATES["act6_arunmor_victory"]


def _prerequisites_met(ps, act, scene):
    """Return True if all scenes that must precede (act, scene) have run."""
    # Within an act, scenes must execute in order of their scene number.
    for (ran_act, ran_scene_key) in _SCENE_ORDER:
        if ran_act == act and ran_scene_key < scene:
            if (ran_act, ran_scene_key) not in ps.scenes_run:
                return False
        if ran_act > act:
            break
    return True


# Ordered list of (act, scene) for prerequisite checking.
_SCENE_ORDER = [
    (1, 2), (1, 3), (1, 4), (1, 5), (1, 7), (1, 8),
    (2, 1), (2, 2), (2, 3),
    (3, 1), (3, 2), (3, 3), (3, 4),
    (4, 1), (4, 4), (4, 7), (4, 10),
    (5, 1), (5, 2),
    (6, 1), (6, 2), (6, 3),
]


def _add_news(session_id, headline, body, category, tick, expires_offset=None):
    """Helper: create a NewsArticle record."""
    expires = (tick + expires_offset) if expires_offset else None
    article = NewsArticle(
        game_session_id=session_id,
        headline=headline,
        body=body,
        category=category,
        created_at_tick=tick,
        expires_at_tick=expires,
    )
    db.session.add(article)
    return article


def _send_message(session_id, from_name, subject, body, tick=0):
    """Helper: create a Message for the player."""
    player = Player.query.filter_by(game_session_id=session_id).first()
    if player is None:
        log.warning("Plot: no player found for session %s", session_id)
        return None
    msg = Message(
        game_session_id=session_id,
        player_id=player.id,
        from_name=from_name,
        subject=subject,
        body=body,
        created_at_tick=tick,
    )
    db.session.add(msg)
    return msg


# ---------------------------------------------------------------------------
# Act 1 -- Discovery
# ---------------------------------------------------------------------------


def _run_act1_scene2(session_id, ps, tick):
    """ARC hiring all top Uplink Agents -- makes the news."""
    ps.version_revelation = 0.2

    _add_news(
        session_id,
        headline="Unusual hiring practices noticed by analysts",
        body=(
            "Andromeda Research Corporation, otherwise known as ARC, have been "
            "extremely busy lately.\n\n"
            "The company has been hiring all of the top Uplink Agents for the "
            "past couple of weeks, sometimes posting several missions in one "
            "day.\n\n"
            "Details are thin but it appears that the work done is very vague "
            "in nature - ARC are keeping quiet about the ultimate goal of this "
            "work and all of the Agents involved are sworn to secrecy. Analysts "
            "predict that ARC has spent over fifty-thousand credits in the last "
            "week alone on agent fees.\n\n"
            "At the time of writing, ARC was unwilling to comment."
        ),
        category="plot",
        tick=tick,
    )
    return {"type": "plot_news", "headline": "Unusual hiring practices noticed by analysts"}


def _run_act1_scene3(session_id, ps, tick):
    """High ranking agent raises doubts over ARC."""
    _add_news(
        session_id,
        headline="High ranking Agent raises doubts over ARC",
        body=(
            "One of the top ranking Uplink Agents has broken the silence over "
            "the recent activity of ARC (Andromeda Research Corporation) and "
            "raised doubts over the morality of the work being done.\n\n"
            "The announcement comes less than a month after ARC began recruiting "
            "all the top agents for work on some unspecified project.\n\n"
            "The Agent states that 'We don't know anything about this company "
            "ARC - some of the work that I've seen done for them is highly "
            "suspicious and could be used in a very destructive manner if "
            "properly exploited. ARC are relying on the unofficial code of "
            "honour of Uplink Agents - that they won't discuss what they were "
            "working on. Someone needs to come forward and explain what this "
            "company is up to.'\n\n"
            "Once again, ARC refused to comment, but did say that a press "
            "release was imminent."
        ),
        category="plot",
        tick=tick,
    )
    return {"type": "plot_news", "headline": "High ranking Agent raises doubts over ARC"}


def _run_act1_scene4(session_id, ps, tick):
    """Top Uplink Agent reassures community -- but adds suspicious logs."""
    ps.version_revelation = 0.7

    _add_news(
        session_id,
        headline="Top Uplink Agent reassures community",
        body=(
            "In a surprising development in the mystery of Andromeda Research "
            "Corporation (ARC), the number one rated Uplink Agent has come "
            "forward and tried to reassure the community.\n\n"
            "The Agent says in his statement that 'I have been working for ARC "
            "on a confidential project for the past two weeks. The project is "
            "immensely ambitious in nature but is nothing to worry about. ARC "
            "have been keeping the public in the dark to protect their trade "
            "secrets. Uplink Agents should not be afraid of accepting jobs from "
            "this company.'\n\n"
            "'Some people have said they think ARC are building some kind of "
            "military weapon - I can say that I have had full access to the ARC "
            "Central Mainframe for the past week and there is nothing of the "
            "sort on the system. What they are doing is being kept under wraps "
            "but it is definitely not a weapon.'\n\n"
            "The Agent is a well respected hacker with years of experience and "
            "his comments will certainly reassure the community."
        ),
        category="plot",
        tick=tick,
    )
    return {"type": "plot_news", "headline": "Top Uplink Agent reassures community"}


def _run_act1_scene5(session_id, ps, tick):
    """Top agent found dead -- suicide / murder. Delayed email set up."""
    _add_news(
        session_id,
        headline="Top agent working for ARC found dead",
        body=(
            "A top-ranked Uplink Agent has been found dead in his house after "
            "an apparent suicide. Preliminary forensic analysis suggests he "
            "overdosed on sleeping pills.\n\n"
            "He was at the top of the Agent leaderboard and made the news "
            "recently after commenting on the actions of Andromeda Research "
            "Corporation (ARC). He had been working for them on their latest "
            "product which is currently shrouded in mystery. This latest "
            "development will no doubt add to the mystery surrounding the "
            "project.\n\n"
            "ARC released a statement earlier today, stating 'He was the best "
            "programmer we had ever seen and was a lead player in the project. "
            "For something like this to happen is a tragedy of the greatest "
            "order. Our thoughts go out to this man's family and friends.'"
        ),
        category="plot",
        tick=tick,
    )

    return {"type": "plot_news", "headline": "Top agent working for ARC found dead"}


def _run_act1_scene7(session_id, ps, tick):
    """Dead agent's delayed warning email arrives to all agents (player)."""
    _send_message(
        session_id,
        from_name="Agent [DECEASED]",
        subject="Warning about ARC",
        body=(
            "[Autosend - 7 day delay expired]\n"
            "[Sent to ALL-AGENTS]\n\n"
            "Agents,\n"
            "If you are reading this email then it means I am dead. I have "
            "been working for Andromeda for the past month on a top secret "
            "project - and until yesterday I did not even know what exactly "
            "I was coding.\n\n"
            "This story hit the news and I decided that I should try to find "
            "out what was happening with project Revelation - and yesterday I "
            "managed to gain access to their stand-alone server room and copy "
            "the files that we were working on.\n\n"
            "Unfortunately they saw what I was doing and I had to leave quick, "
            "and I haven't had time to analyse the project files yet. If you "
            "read this then they have already caught me.\n\n"
            "ARC cannot be trusted. We must come together as a group and find "
            "out what they are up to before something terrible happens. I "
            "don't know if it's already too late."
        ),
        tick=tick,
    )
    return {"type": "plot_message", "subject": "Warning about ARC"}


def _run_act1_scene8(session_id, ps, tick):
    """Uplink Corporation issues formal warning against ARC."""
    _add_news(
        session_id,
        headline="Formal warning issued by Uplink Corporation",
        body=(
            "Uplink Corporation has issued a formal warning to all of its "
            "agents, warning them against accepting work for Andromeda Research "
            "Corporation (ARC).\n\n"
            "In a statement released today, they say 'Uplink Corporation is "
            "currently investigating the claim that ARC have been developing "
            "some kind of high-tech weapon, using the expertise of freelance "
            "Uplink agents to assist them. Federal agents have been called in "
            "to assist and are also pursuing the matter of a recent suicide, "
            "which they believe may have been a related murder.\n\n"
            "'Until we can determine if these charges have any truth in them, "
            "we must insist that all Uplink Agents refuse any work being "
            "offered to them from ARC or anyone working for that company. "
            "Anyone caught working for this company will lose their Uplink "
            "status immediately.'"
        ),
        category="plot",
        tick=tick,
    )

    _send_message(
        session_id,
        from_name="Uplink Corporation",
        subject="FORMAL WARNING: Andromeda Research Corporation",
        body=(
            "Agent,\n\n"
            "Uplink Corporation is formally warning all agents against "
            "accepting work from Andromeda Research Corporation (ARC).\n\n"
            "We are investigating serious allegations against this company. "
            "Any agent found to be working for ARC will have their Uplink "
            "status revoked immediately.\n\n"
            "Please exercise caution.\n\n"
            "- Uplink Corporation"
        ),
        tick=tick,
    )

    return {"type": "plot_news", "headline": "Formal warning issued by Uplink Corporation"}


# ---------------------------------------------------------------------------
# Act 2 -- Contact
# ---------------------------------------------------------------------------


def _run_act2_scene1(session_id, ps, tick):
    """Maiden Flight mission offered -- ARC wants to test Revelation v1.0."""
    ps.version_revelation = 1.0

    _send_message(
        session_id,
        from_name="internal@ARC.net",
        subject="An opportunity - Maiden Flight",
        body=(
            "Agent,\n\n"
            "We are Andromeda Research Corporation. You may have heard of us "
            "in the news recently. We want you to know that those allegations "
            "are entirely false.\n\n"
            "We are working on a revolutionary new software product and we "
            "need the help of skilled Uplink Agents to test it. The mission is "
            "simple: run a test copy of our software on a designated target "
            "system.\n\n"
            "Payment: 10,000c\n\n"
            "If you are interested, this mission will be available on the "
            "Uplink BBS board. Look for 'MaidenFlight'.\n\n"
            "- ARC Internal"
        ),
        tick=tick,
    )

    return {"type": "plot_message", "subject": "An opportunity - Maiden Flight"}


def _run_act2_scene2(session_id, ps, tick):
    """Another agent completes Maiden Flight (if player has not)."""
    if not _has_completed_special(ps, SPECIALMISSION_MAIDENFLIGHT):
        _add_news(
            session_id,
            headline="New computer virus detected - Revelation",
            body=(
                "A new computer virus has been detected on several corporate "
                "systems. The virus, known as 'Revelation', appears to be an "
                "extremely sophisticated piece of software capable of "
                "destroying data on any system it infects.\n\n"
                "The source of the virus is currently unknown but investigators "
                "believe it may be connected to Andromeda Research Corporation."
            ),
            category="plot",
            tick=tick,
        )

    return {"type": "plot_news", "headline": "New computer virus detected"}


def _run_act2_scene3(session_id, ps, tick):
    """Arunmor contacts player -- offers alliance against ARC."""
    _send_message(
        session_id,
        from_name="internal@Arunmor.net",
        subject="We need your help - confidential",
        body=(
            "Agent,\n\n"
            "We are Arunmor Corporation. We have been monitoring the "
            "activities of Andromeda Research Corporation and we believe they "
            "are developing a virus capable of destroying the entire "
            "Internet.\n\n"
            "We are developing a counter-virus called 'Faith' but we need "
            "help from skilled agents like you. If you agree to work with us, "
            "we can offer substantial payment and you will be helping to "
            "protect the Internet from destruction.\n\n"
            "You have a choice to make:\n"
            "- Work with us (Arunmor) to develop Faith and stop Revelation\n"
            "- Work with ARC to spread Revelation\n"
            "- Stay neutral (but the plot will advance without you)\n\n"
            "Choose wisely. The fate of the Internet depends on agents like "
            "you.\n\n"
            "- Arunmor Corporation"
        ),
        tick=tick,
    )

    # ARC also sends a competing offer
    _send_message(
        session_id,
        from_name="internal@ARC.net",
        subject="Join us - the future awaits",
        body=(
            "Agent,\n\n"
            "You have proven yourself to be a capable operative. Andromeda "
            "Research Corporation invites you to join our cause.\n\n"
            "The Internet as it exists today is nothing more than an extension "
            "of Western Capitalism. It must be cleansed. Our Revelation "
            "project will achieve this goal.\n\n"
            "If you join us, you will be handsomely rewarded and will play a "
            "part in reshaping the digital world.\n\n"
            "The choice is yours.\n\n"
            "- ARC Internal"
        ),
        tick=tick,
    )

    return [
        {"type": "plot_message", "subject": "We need your help - Arunmor"},
        {"type": "plot_message", "subject": "Join us - ARC"},
        {"type": "plot_choice_available", "choices": ["arunmor", "arc"]},
    ]


# ---------------------------------------------------------------------------
# Act 3 -- Missions
# ---------------------------------------------------------------------------


def _run_act3_scene1(session_id, ps, tick):
    """News story about Revelation attack on Arunmor systems."""
    if ps.player_loyalty == 1:
        # Player betrayed ARC
        _send_message(
            session_id,
            from_name="internal@ARC.net",
            subject="Warning",
            body=(
                "So it seems that you were working for the enemy behind our "
                "backs all this time. You cannot imagine how surprised we were "
                "when we heard that Arunmor had received a complete copy of "
                "Revelation, and that it was an Uplink Agent who was the "
                "source.\n\n"
                "Take this message however you want - but Andromeda Research "
                "Corporation will not let this betrayal go unpunished. We'll "
                "be watching you, and when we finally come after you, you're "
                "going to wish you had never heard of Arunmor Corporation or "
                "Uplink."
            ),
            tick=tick,
        )

        _add_news(
            session_id,
            headline="Arunmor Security scare - a special report",
            body=(
                "Earlier today Arunmor Corporation shut down all of its primary "
                "computer systems and disconnected their Internal Network from "
                "the web. The disconnection lasted just under one hour, and "
                "caused a great deal of disruption to Internet traffic flowing "
                "through their systems.\n\n"
                "Arunmor says they had received word that they were about to be "
                "attacked by a group of hackers working for the controversial "
                "Andromeda Research Corporation. So far Arunmor has not said "
                "why they suspect this company. It is believed they had some "
                "kind of inside information.\n\n"
                "This latest accusation casts Andromeda Research Corporation "
                "in an increasingly bad light."
            ),
            category="plot",
            tick=tick,
        )
    else:
        _add_news(
            session_id,
            headline="The Arunmor virus outbreak - a special report",
            body=(
                "Arunmor Corporation recently suffered an attack from a new "
                "computer virus, dubbed by industry experts as 'Revelation'.\n\n"
                "This virus has never been seen before and contains a payload "
                "capable of destroying almost any computer it is used against. "
                "Currently the virus does not appear to spread particularly "
                "fast and it is limited to systems owned by the target company, "
                "but it is believed that whoever is responsible is probably "
                "still working on improving it.\n\n"
                "Recently a high ranking Uplink Agent contacted us and "
                "suggested that Andromeda Research Corporation might be "
                "connected to this viral outbreak. Agents have been assigned "
                "the task of investigating."
            ),
            category="plot",
            tick=tick,
        )

    return {"type": "plot_news", "headline": "Act 3 begins - Revelation in the wild"}


def _run_act3_scene2(session_id, ps, tick):
    """Arunmor announces Faith project."""
    ps.version_faith = 1.0

    _add_news(
        session_id,
        headline="Arunmor: we'll retaliate",
        body=(
            "Following the recent attempted attack on the Arunmor computer "
            "network, Arunmor have announced that they have begun work on a "
            "new project - dubbed 'Faith'. The aim of this project is to stop "
            "the release of destructive computer viruses onto the Net.\n\n"
            "A company spokesman said 'We cannot allow any virus, including "
            "the so called Revelation virus, to roam freely around our "
            "corporate networks. Project Faith will actively seek out "
            "Revelation and other destructive viruses, and will totally "
            "eradicate them. At this moment we are seeking Government "
            "assistance as this project could help everyone.'\n\n"
            "Arunmor has taken the unprecedented step of offering a reward of "
            "25000 credits to anyone who can help them with their research "
            "into Revelation. Anyone with any data related to this virus "
            "should send it to internal@Arunmor.net to claim their reward."
        ),
        category="plot",
        tick=tick,
    )

    _add_news(
        session_id,
        headline="New Uplink service available",
        body=(
            "In light of the recent developments related to Revelation and "
            "Faith, Uplink Corporation has installed a new system which will "
            "allow agents to track the progress of the two rival viruses.\n\n"
            "A new option has appeared in the main menu, titled 'Faith "
            "Progress'. Clicking this option will show you the current latest "
            "versions of both viruses. This data is based on reports of these "
            "programs on the Web, so they may not be entirely accurate."
        ),
        category="plot",
        tick=tick,
    )

    return {"type": "plot_news", "headline": "Arunmor announces Faith project"}


def _run_act3_scene3(session_id, ps, tick):
    """Arunmor releases details on Revelation. Describes its destructive potential."""
    if ps.player_loyalty == 1:
        detail_suffix = (
            "'We have hired a small number of capable Uplink Agents to help "
            "work against this.'"
        )
    else:
        detail_suffix = (
            "We will be posting missions on the Uplink BBS mission board. Any "
            "agents that can help us will be well rewarded, and will be "
            "fighting for a good cause.\n\n"
            "'The offer of 25000c for any data related to Revelation is still "
            "open, and will remain open for the next 48 hours.'"
        )

    _add_news(
        session_id,
        headline="Arunmor release details on Revelation",
        body=(
            "Arunmor Corporation have been working hard on researching the "
            "recently discovered Revelation project, and have released details "
            "of their findings.\n\n"
            "'Revelation is the most destructive computer virus we have ever "
            "seen' said the CEO of Arunmor Corporation earlier today. 'At "
            "first we thought it was targeted specifically at us. It has now "
            "become clear that the aim of Revelation is to totally destroy the "
            "Internet, from the inside.\n\n"
            "'Once released, it will spread like wildfire to all the main "
            "systems, then eventually to the entire Internet, destroying "
            "everything in its path. Its payload is extremely well designed "
            "and will take down any system it comes up against.'\n\n"
            f"{detail_suffix}\n\n"
            "'Our Faith project is now aiming to provide a counter-virus that "
            "will stop Revelation in its tracks.'\n"
            "Federal Agents today began an investigation into the activities "
            "of Andromeda Research Corporation."
        ),
        category="plot",
        tick=tick,
    )

    return {"type": "plot_news", "headline": "Arunmor release details on Revelation"}


def _run_act3_scene4(session_id, ps, tick):
    """Federal agents release findings -- ARC is controlled by Andromeda."""
    _add_news(
        session_id,
        headline="Federal Agents release findings on ARC",
        body=(
            "Federal Agents today made their first public announcement on "
            "their investigation into Andromeda Research Corporation (ARC).\n\n"
            "'Our investigation so far has uncovered a number of disturbing "
            "facts, however no concrete evidence has yet been discovered' said "
            "a Federal Spokesman. 'It would appear that ARC are developing a "
            "software tool in an attempt to damage the operation of the "
            "Internet. So far no evidence has been found and no witnesses have "
            "come forward to back this up.'\n\n"
            "'Most importantly, we have determined that Andromeda Research "
            "Corporation is privately owned and controlled by the secretive "
            "group Andromeda, and that the CEO and the Managing Director of "
            "ARC are both core members of this group. Our profile of Andromeda "
            "lists them as well funded Anti-Capitalist Techno-Anarchists, "
            "which would seem to fit the charges against them.'\n\n"
            "'We intend to continue our investigation and appeal for anyone "
            "with any information to come forward.'"
        ),
        category="plot",
        tick=tick,
    )

    return {"type": "plot_news", "headline": "Federal Agents release findings on ARC"}


# ---------------------------------------------------------------------------
# Act 4 -- Escalation
# ---------------------------------------------------------------------------


def _run_act4_scene1(session_id, ps, tick):
    """Arunmor put out 'Tracer' mission; ARC put out 'Darwin'."""
    ps.version_revelation = round(ps.version_revelation + 0.5, 1)

    if ps.player_loyalty == 1:
        _send_message(
            session_id,
            from_name="internal@Arunmor.net",
            subject="New Mission: Tracer",
            body=(
                "Agent,\n\n"
                "We need you to perform a covert installation of a Tracer "
                "program onto the ARC Central Mainframe. This will allow us to "
                "monitor their activities and prepare our counter-measures.\n\n"
                f"Payment: {SPECIAL_MISSION_PAYMENTS[SPECIALMISSION_TRACER]}c\n\n"
                "This is critical work. Good luck.\n\n"
                "- Arunmor Corporation"
            ),
            tick=tick,
        )
    elif ps.player_loyalty == -1:
        _send_message(
            session_id,
            from_name="internal@ARC.net",
            subject="New Mission: Darwin",
            body=(
                "Agent,\n\n"
                "We need you to steal vital research into Digital Life Forms "
                "from Darwin Research Associates. This data is critical to "
                "improving our Revelation virus.\n\n"
                f"Payment: {SPECIAL_MISSION_PAYMENTS[SPECIALMISSION_DARWIN]}c\n\n"
                "Do not fail us.\n\n"
                "- ARC Internal"
            ),
            tick=tick,
        )

    return {"type": "plot_missions_available", "act": 4}


def _run_act4_scene4(session_id, ps, tick):
    """News about ongoing special missions and Revelation spread."""
    ps.version_revelation = round(ps.version_revelation + 0.3, 1)
    ps.version_faith = round(ps.version_faith + 0.2, 1)

    _add_news(
        session_id,
        headline="Revelation virus spreading - experts concerned",
        body=(
            "The Revelation computer virus continues to spread across major "
            "systems. Several corporate Internal Services Machines have "
            "reported infections this week alone.\n\n"
            "Arunmor Corporation says their Faith counter-virus is making "
            "progress, but admits they are in a race against time. 'Every day "
            "that passes, Revelation grows more sophisticated,' said an "
            "Arunmor spokesperson.\n\n"
            "Federal investigators continue to pursue leads connecting "
            "Andromeda Research Corporation to the outbreak."
        ),
        category="plot",
        tick=tick,
    )

    return {"type": "plot_news", "headline": "Revelation virus spreading"}


def _run_act4_scene7(session_id, ps, tick):
    """More special missions offered; virus versions advance."""
    ps.version_revelation = round(ps.version_revelation + 0.5, 1)
    ps.version_faith = round(ps.version_faith + 0.3, 1)

    if ps.player_loyalty == 1:
        _send_message(
            session_id,
            from_name="internal@Arunmor.net",
            subject="New Mission: ARC Infiltration",
            body=(
                "Agent,\n\n"
                "We have an amazing opportunity. Our intelligence suggests "
                "that ARC's security has been weakened by the Federal "
                "investigation. We need you to infiltrate their Central "
                "Mainframe and steal critical Revelation source code.\n\n"
                f"Payment: {SPECIAL_MISSION_PAYMENTS[SPECIALMISSION_ARCINFILTRATION]}c\n\n"
                "This could be the breakthrough we need.\n\n"
                "- Arunmor Corporation"
            ),
            tick=tick,
        )
    elif ps.player_loyalty == -1:
        _send_message(
            session_id,
            from_name="internal@ARC.net",
            subject="New Mission: Save It For The Jury",
            body=(
                "Agent,\n\n"
                "The Federal investigation is getting too close. We need you "
                "to frame the chief technician of Arunmor Corporation for "
                "financial crimes. This will discredit their testimony and "
                "buy us more time.\n\n"
                f"Payment: {SPECIAL_MISSION_PAYMENTS[SPECIALMISSION_SAVEITFORTHEJURY]}c\n\n"
                "Make it convincing.\n\n"
                "- ARC Internal"
            ),
            tick=tick,
        )

    return {"type": "plot_missions_available", "act": 4}


def _run_act4_scene10(session_id, ps, tick):
    """News about escalating virus war; stock markets affected."""
    ps.version_revelation = round(ps.version_revelation + 0.5, 1)
    ps.version_faith = round(ps.version_faith + 0.5, 1)

    _add_news(
        session_id,
        headline="Internet systems failing worldwide",
        body=(
            "Reports are flooding in from around the world of computer systems "
            "going offline. The Revelation virus has now infected hundreds of "
            "corporate and government systems.\n\n"
            "Stock markets have been severely affected, with several exchanges "
            "forced to suspend trading due to system failures. Financial "
            "analysts are calling this the worst cyber-attack in history.\n\n"
            "Arunmor Corporation says their Faith project is nearing "
            "completion and urges system administrators to hold on. 'We are "
            "close to a breakthrough,' said the CEO. 'Faith will be ready "
            "soon.'\n\n"
            "The Federal investigation into ARC has intensified, with raids "
            "expected imminently."
        ),
        category="plot",
        tick=tick,
    )

    if ps.player_loyalty == 1:
        _send_message(
            session_id,
            from_name="internal@Arunmor.net",
            subject="New Mission: Shiny Hammer",
            body=(
                "Agent,\n\n"
                "We need to strike at the heart of ARC's operation. Your "
                "mission is to destroy all copies of Revelation research data "
                "on the ARC Central Mainframe.\n\n"
                f"Payment: {SPECIAL_MISSION_PAYMENTS[SPECIALMISSION_SHINYHAMMER]}c\n\n"
                "This is our most important mission yet.\n\n"
                "- Arunmor Corporation"
            ),
            tick=tick,
        )
    elif ps.player_loyalty == -1:
        _send_message(
            session_id,
            from_name="internal@ARC.net",
            subject="New Mission: Shiny Hammer",
            body=(
                "Agent,\n\n"
                "Arunmor are getting too close to completing Faith. We need "
                "you to destroy all research completed by Arunmor Corporation. "
                "Break into their systems and delete everything related to "
                "Faith.\n\n"
                f"Payment: {SPECIAL_MISSION_PAYMENTS[SPECIALMISSION_SHINYHAMMER]}c\n\n"
                "The future of Revelation depends on this.\n\n"
                "- ARC Internal"
            ),
            tick=tick,
        )

    return {"type": "plot_news", "headline": "Internet systems failing worldwide"}


# ---------------------------------------------------------------------------
# Act 5 -- Climax
# ---------------------------------------------------------------------------


def _run_act5_scene1(session_id, ps, tick):
    """Revelation launch due soon -- industry experts predict imminent release."""
    _add_news(
        session_id,
        headline="Revelation Launch due soon?",
        body=(
            "Industry experts are predicting that a launch of the destructive "
            "Revelation virus may be due soon. If true, this could mean damage "
            "to a great deal of computer systems.\n\n"
            "Federal agents have been waiting for an opportunity to enter "
            "Andromeda Research Corporation but have so far not had enough "
            "evidence against the company.\n\n"
            "Recent events such as the arrest of a high ranked member of the "
            "company and the theft of program code from Darwin Research "
            "Associates has led industry experts to speculate that now would "
            "be the perfect time for a launch of the virus.\n\n"
            "Arunmor corporation has been working hard and have a prototype "
            "of the counter virus Faith, but it is not clear how effective "
            "this would be."
        ),
        category="plot",
        tick=tick,
    )

    return {"type": "plot_news", "headline": "Revelation launch due soon?"}


def _run_act5_scene2(session_id, ps, tick):
    """Final missions: GrandTour (ARC) or CounterAttack (Arunmor)."""
    if ps.player_loyalty == -1:
        # ARC path: player launches Revelation
        _send_message(
            session_id,
            from_name="internal@ARC.net",
            subject="FINAL MISSION: Grand Tour",
            body=(
                "Agent,\n\n"
                "The time has come. Revelation is ready for full deployment. "
                "Your mission is to release the Revelation virus into as many "
                "major systems as possible.\n\n"
                "This is it -- the Grand Tour. Visit every major system and "
                "unleash Revelation. The Internet as we know it will cease to "
                "exist.\n\n"
                f"Payment: {SPECIAL_MISSION_PAYMENTS[SPECIALMISSION_GRANDTOUR]}c\n\n"
                "This message also includes a copy of Revelation and the "
                "Revelation Tracker software.\n\n"
                "DO NOT ATTEMPT TO RUN REVELATION LOCALLY.\n\n"
                "- ARC Internal"
            ),
            tick=tick,
        )

    elif ps.player_loyalty == 1:
        # Arunmor path: player deploys Faith
        _send_message(
            session_id,
            from_name="internal@Arunmor.net",
            subject="FINAL MISSION: Counter Attack",
            body=(
                "Agent,\n\n"
                "This is it. Revelation has been released onto the Internet "
                "and is spreading fast. Your mission is to deploy Faith to "
                "every infected system and stop the virus before it destroys "
                "everything.\n\n"
                "Federal Agents are moving to shut down ARC but we need to "
                "contain the existing outbreak NOW.\n\n"
                f"Payment: {SPECIAL_MISSION_PAYMENTS[SPECIALMISSION_COUNTERATTACK]}c\n\n"
                "The fate of the Internet is in your hands. Do your best and "
                "hurry.\n\n"
                "- Arunmor Corporation"
            ),
            tick=tick,
        )

    else:
        # Neutral player: events proceed without them
        _add_news(
            session_id,
            headline="Revelation virus outbreak leaves systems crippled",
            body=(
                "The Revelation computer virus has been released into the wild "
                "and has spread rapidly through major computer systems around "
                "the world. A massive amount of damage has been done, and "
                "reports are still coming in from systems that have been "
                "literally wiped clean by the virus.\n\n"
                "However, Arunmor Corporation have been developing a counter "
                "virus known as Faith for the past few weeks with the aid of "
                "Government assistance, and have managed to stop the "
                "Revelation Virus from spreading any further.\n\n"
                "Federal Agents busted into Andromeda Research Corporation "
                "shortly after the virus outbreak and arrested staff members "
                "suspected of involvement."
            ),
            category="plot",
            tick=tick,
        )

    return {"type": "plot_climax", "loyalty": ps.player_loyalty}


# ---------------------------------------------------------------------------
# Act 6 -- Resolution
# ---------------------------------------------------------------------------


def _run_act6_scene1(session_id, ps, tick):
    """Andromeda leader releases press statement."""
    # Determine outcome based on player loyalty and mission completion
    if ps.player_loyalty == -1 and _has_completed_special(ps, SPECIALMISSION_GRANDTOUR):
        # ARC victory: Internet destroyed
        ps.revelation_release_uncontrolled = True
        ps.state = PLOT_STATES["act6_arc_victory"]

        _add_news(
            session_id,
            headline="Internet destroyed - Revelation spreads uncontrolled",
            body=(
                "The worst fears of the Internet community have been "
                "realized. The Revelation virus has spread beyond control, "
                "destroying systems across the globe.\n\n"
                "Uplink Corporation has been forced to cease operations. "
                "Financial markets have collapsed. Government systems are "
                "offline.\n\n"
                "The leader of the Andromeda group has claimed responsibility, "
                "calling it 'the liberation of humanity from digital slavery.'"
            ),
            category="plot",
            tick=tick,
        )

        session = db.session.get(GameSession, session_id)
        if session:
            session.is_active = False

        return {"type": "plot_ending", "outcome": "arc_victory",
                "headline": "Internet destroyed"}
    else:
        # Arunmor victory / neutral: ARC busted, Revelation contained
        ps.revelation_arc_busted = True
        ps.state = PLOT_STATES["act6_arunmor_victory"]

        _add_news(
            session_id,
            headline="First press release from Andromeda Leader",
            body=(
                "The Leader of the Andromeda group today issued a statement "
                "through his lawyer, regarding his recent arrest for criminal "
                "damage to the Web. In it he outlines why he tried to destroy "
                "the Internet that we all rely on.\n\n"
                "'Firstly, I make no apologies for what I have done. My only "
                "regret is that I did not succeed' says the man, who has not "
                "yet been identified by Federal Agents.\n\n"
                "'The Internet used to be a place of amazing opportunity and "
                "promise - the last remnant of free speech and true anonymity. "
                "Now it is little more than an extension of the evil of "
                "Western Capitalism.'\n\n"
                "'Think of this. Do you have any idea how much money Arunmor "
                "will make from recent events? This is why I tried to destroy "
                "the Internet. It only serves to line the pockets of those "
                "who would try to control us.'\n\n"
                "'While the Web exists, you will never be safe. Your entire "
                "life is on file, waiting for somebody to tamper with it. "
                "Your lives are being destroyed by the Computers you "
                "desperately try to defend.'\n\n"
                "It is believed this man will spend several years in jail for "
                "this crime."
            ),
            category="plot",
            tick=tick,
        )

        return {"type": "plot_news",
                "headline": "First press release from Andromeda Leader"}


def _run_act6_scene2(session_id, ps, tick):
    """Leader of Andromeda jailed."""
    if ps.revelation_release_uncontrolled:
        # ARC victory already handled -- no further scenes
        return None

    _add_news(
        session_id,
        headline="Leader of Andromeda jailed",
        body=(
            "The Federal courts today found the CEO of ARC and the leader of "
            "Andromeda Guilty of criminal destruction of data.\n\n"
            "The judge called the Leader of Andromeda 'an evil and vindictive "
            "man, who truly believes the world would be a better place in a "
            "state of Anarchy.'\n\n"
            "He went on to say that he had little sympathy for both the "
            "defendants.\n\n"
            "As punishment for their crimes, both members will serve eight "
            "years imprisonment and will be banned from the use of computers "
            "for life."
        ),
        category="plot",
        tick=tick,
    )

    return {"type": "plot_news", "headline": "Leader of Andromeda jailed"}


def _run_act6_scene3(session_id, ps, tick):
    """Retrospective -- the plot concludes."""
    if ps.revelation_release_uncontrolled:
        return None

    _add_news(
        session_id,
        headline="Revelation: A retrospective",
        body=(
            "It would appear that the recent panic over Revelation was (as "
            "usual) totally unnecessary. The Internet has suffered a number of "
            "high profile scares since its foundation, and it has always "
            "survived. This incident was no different, and only serves to "
            "highlight the ease with which the public can be scared into "
            "thinking their lives are in danger.\n\n"
            "Since the collapse of the Andromeda Group, ARC has been exposed "
            "as little more than a front for their activities, and has shut "
            "down all operations. It is a wonder that nobody noticed ARC never "
            "released any products.\n\n"
            "Arunmor Corporation yesterday launched their new Active-Virus-"
            "Guard software, titled 'Faith'. This is an extension of the tool "
            "used to defeat Revelation, and the makers claim it actively seeks "
            "out viruses and eradicates them. Sales have apparently been 'very "
            "promising'.\n\n"
            "At the time of writing, shares in Arunmor Corporation had risen "
            "to a new high."
        ),
        category="plot",
        tick=tick,
    )

    if ps.player_loyalty == 1:
        _send_message(
            session_id,
            from_name="internal@Arunmor.net",
            subject="Thank you",
            body=(
                "Agent,\n\n"
                "On behalf of everyone at Arunmor Corporation, we want to "
                "thank you for your role in stopping Revelation.\n\n"
                "The Internet has been saved, and your contribution was "
                "invaluable. You are a true hero of the digital age.\n\n"
                "Your final payment has been credited to your account.\n\n"
                "- Arunmor Corporation"
            ),
            tick=tick,
        )

    # Mark end of plot
    log.info("Plot: session=%s -- plot concluded (act 6 scene 3). "
             "Arunmor victory.", session_id)

    return {"type": "plot_ending", "outcome": "arunmor_victory",
            "headline": "Revelation: A retrospective"}
