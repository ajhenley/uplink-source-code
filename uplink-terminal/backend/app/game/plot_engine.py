"""Plot engine: Revelation storyline state machine (Acts 1-6).

The plot is driven by game ticks. Each scene fires at a fixed tick threshold,
sending emails, generating news, and advancing the plot_act/plot_scene state.
The player can lock loyalty by replying to any ARC or Arunmor email during
Acts 2-3. Once locked, loyalty is permanent.

Acts 1-3 use a fixed _SCENE_SEQUENCE table with absolute tick thresholds.
Acts 4-6 use dynamic scheduling via gs.plot_next_scene_tick, since their
timing is relative to when the player locked loyalty and completed missions.
"""

from ..extensions import db
from ..models import Email, GameSession, Mission, Computer, DataFile
from .constants import (
    PLOT_ACT_NONE, PLOT_ACT_1, PLOT_ACT_2, PLOT_ACT_3,
    PLOT_ACT_4, PLOT_ACT_5, PLOT_ACT_6,
    SCENE_1_INTRO, SCENE_1_ARC_CONTACT, SCENE_1_ARUNMOR_CONTACT,
    SCENE_2_ARC_OFFER, SCENE_2_ARUN_OFFER, SCENE_2_NEWS_VIRUS,
    SCENE_2_ARC_SWEETEN, SCENE_2_ARUN_SWEETEN,
    SCENE_3_CHOICE_PROMPT, SCENE_3_PLAYER_CHOSE,
    SCENE_4_MISSION_1, SCENE_4_MISSION_1_DONE,
    SCENE_4_MISSION_2, SCENE_4_MISSION_2_DONE,
    SCENE_4_NEWS_ESCALATION,
    SCENE_5_DEPLOYMENT, SCENE_5_WARFARE_1, SCENE_5_WARFARE_2,
    SCENE_5_RESOLUTION,
    SCENE_6_AFTERMATH, SCENE_6_SENTENCING, SCENE_6_EPILOGUE, SCENE_6_COMPLETE,
    MISSION_PLOT_STEAL, MISSION_PLOT_DESTROY, MISSION_PLOT_DEPLOY,
    MISSION_ACCEPTED, MISSION_COMPLETED,
    PLOT_START_TICK, PLOT_SCENE_INTERVAL,
    PLOT_ACT4_DELAY, PLOT_MISSION_INTERVAL, PLOT_ACT5_DELAY, PLOT_ACT6_DELAY,
    PLOT_MISSION_1_PAYMENT, PLOT_MISSION_2_PAYMENT, PLOT_DEPLOY_PAYMENT,
    PLOT_EMAIL_ARC, PLOT_EMAIL_ARUNMOR, PLOT_EMAIL_UPLINK_INTERNAL,
    PLOT_PAYMENT_ARC, PLOT_PAYMENT_ARUNMOR,
    FACTION_NONE, FACTION_ARC, FACTION_ARUNMOR,
    IP_ARC, IP_ARUNMOR, IP_UPLINK_TEST,
    RATING_GAIN,
)
from .news_engine import generate_news_article


# Scene sequence: (tick_threshold, scene_id, handler_function_name)
_SCENE_SEQUENCE = [
    (800,  SCENE_1_INTRO,           "_scene_1_intro"),
    (1200, SCENE_1_ARC_CONTACT,     "_scene_1_arc_contact"),
    (1600, SCENE_1_ARUNMOR_CONTACT, "_scene_1_arunmor_contact"),
    (2000, SCENE_2_ARC_OFFER,       "_scene_2_arc_offer"),
    (2400, SCENE_2_ARUN_OFFER,      "_scene_2_arun_offer"),
    (2800, SCENE_2_NEWS_VIRUS,      "_scene_2_news_virus"),
    (3200, SCENE_2_ARC_SWEETEN,     "_scene_2_arc_sweeten"),
    (3600, SCENE_2_ARUN_SWEETEN,    "_scene_2_arun_sweeten"),
    (4000, SCENE_3_CHOICE_PROMPT,   "_scene_3_choice_prompt"),
]


def tick_plot(gs):
    """Called every tick from the game loop. Advances plot scenes by time."""
    # Acts 4-6: dynamic scheduling based on plot_next_scene_tick
    if gs.plot_act >= 3 and gs.plot_scene not in ("", None) and gs.plot_next_scene_tick > 0:
        if gs.game_time_ticks >= gs.plot_next_scene_tick:
            _dispatch_dynamic_scene(gs)
        return

    # Plot complete — nothing more to do
    if gs.plot_scene == SCENE_6_COMPLETE:
        return

    # Don't advance if plot hasn't started yet and we haven't hit the start tick
    if gs.plot_act == PLOT_ACT_NONE and gs.game_time_ticks < PLOT_START_TICK:
        return

    # Find the next scene to fire (Acts 1-3)
    for tick_threshold, scene_id, handler_name in _SCENE_SEQUENCE:
        if gs.game_time_ticks >= tick_threshold and _scene_not_done(gs, scene_id):
            handler = globals()[handler_name]
            handler(gs)
            return  # Only fire one scene per tick


def _dispatch_dynamic_scene(gs):
    """Route to the correct Act 4-6 handler based on current plot_scene."""
    scene = gs.plot_scene
    handlers = {
        SCENE_3_PLAYER_CHOSE: _start_act_4,
        SCENE_4_MISSION_1: _check_plot_mission_1,
        SCENE_4_MISSION_1_DONE: _scene_4_mission_2,
        SCENE_4_NEWS_ESCALATION: lambda gs: None,
        SCENE_4_MISSION_2: _check_plot_mission_2,
        SCENE_4_MISSION_2_DONE: _start_act_5,
        SCENE_5_DEPLOYMENT: _check_plot_deploy,
        SCENE_5_WARFARE_1: _scene_5_warfare_2,
        SCENE_5_WARFARE_2: _scene_5_resolution,
        SCENE_5_RESOLUTION: _scene_6_aftermath,
        SCENE_6_AFTERMATH: _scene_6_sentencing,
        SCENE_6_SENTENCING: _scene_6_epilogue,
    }
    handler = handlers.get(scene)
    if handler:
        handler(gs)


def _scene_not_done(gs, scene_id):
    """Check if a scene has already been completed."""
    data = gs.plot_data
    return not data.get(f"scene_done_{scene_id}", False)


def _mark_scene_done(gs, scene_id, act):
    """Mark a scene as completed and update act/scene state."""
    data = gs.plot_data
    data[f"scene_done_{scene_id}"] = True
    gs.plot_data = data
    gs.plot_scene = scene_id
    gs.plot_act = act


def _send_plot_email(gs, subject, body, from_addr):
    """Send a plot-related email to the player."""
    db.session.add(Email(
        game_session_id=gs.id,
        subject=subject,
        body=body,
        from_addr=from_addr,
        to_addr="agent@uplink.co.uk",
        game_tick_sent=gs.game_time_ticks,
    ))


def _schedule_next(gs, delay):
    """Schedule the next dynamic scene after `delay` ticks from now."""
    gs.plot_next_scene_tick = gs.game_time_ticks + delay


def _get_faction_names(gs):
    """Return (player_faction_name, rival_faction_name, player_email, rival_ip)."""
    if gs.player_loyalty == FACTION_ARC:
        return "ARC Technologies", "Arunmor Corporation", PLOT_EMAIL_ARC, IP_ARUNMOR
    else:
        return "Arunmor Corporation", "ARC Technologies", PLOT_EMAIL_ARUNMOR, IP_ARC


# --- Act 1: Introduction ---

def _scene_1_intro(gs):
    """Uplink internal warning about strange network activity."""
    _send_plot_email(
        gs,
        subject="INTERNAL: Unusual Network Activity",
        body=(
            "Agent,\n\n"
            "Our monitoring systems have detected unusual patterns across\n"
            "the global network. Several corporate systems have gone dark\n"
            "in the past 48 hours with no explanation.\n\n"
            "We're not sure what's happening yet, but we advise all agents\n"
            "to exercise increased caution during operations.\n\n"
            "We'll update you as we learn more.\n\n"
            "-- Uplink Internal Affairs"
        ),
        from_addr=PLOT_EMAIL_UPLINK_INTERNAL,
    )
    _mark_scene_done(gs, SCENE_1_INTRO, PLOT_ACT_1)


def _scene_1_arc_contact(gs):
    """ARC Technologies contacts the player."""
    _send_plot_email(
        gs,
        subject="Opportunity — ARC Technologies",
        body=(
            "To the Uplink Agent,\n\n"
            "We are ARC Technologies, a leader in advanced computing\n"
            "research. We are working on something truly revolutionary —\n"
            "a project that will reshape the digital landscape.\n\n"
            "We are looking for talented agents to assist with our work.\n"
            "If you are interested, keep an eye on your inbox.\n\n"
            f"Our systems are accessible at {IP_ARC}.\n\n"
            "-- ARC Technologies Administration"
        ),
        from_addr=PLOT_EMAIL_ARC,
    )
    generate_news_article(
        gs.id,
        "ARC Technologies announces major new research initiative",
        (
            "ARC Technologies announces major new research initiative.\n\n"
            "The secretive technology firm revealed today that it has begun\n"
            "work on a groundbreaking project in the field of self-evolving\n"
            "software. Details remain scarce, but sources suggest the project\n"
            "has attracted significant investment from unnamed backers."
        ),
        "Uplink News Network",
        gs.game_time_ticks,
    )
    _mark_scene_done(gs, SCENE_1_ARC_CONTACT, PLOT_ACT_1)


def _scene_1_arunmor_contact(gs):
    """Arunmor Corporation contacts the player."""
    _send_plot_email(
        gs,
        subject="A Warning — Arunmor Corporation",
        body=(
            "To the Uplink Agent,\n\n"
            "We are Arunmor Corporation. We have serious concerns about\n"
            "the activities of a competitor — ARC Technologies.\n\n"
            "We believe they are developing dangerous software that could\n"
            "threaten the stability of the entire network. We need talented\n"
            "agents to help us investigate and counter this threat.\n\n"
            f"You can reach our systems at {IP_ARUNMOR}.\n\n"
            "More details will follow.\n\n"
            "-- Arunmor Research Division"
        ),
        from_addr=PLOT_EMAIL_ARUNMOR,
    )
    generate_news_article(
        gs.id,
        "Arunmor Corporation raises security concerns about competitor",
        (
            "Arunmor Corporation raises security concerns about competitor.\n\n"
            "In a rare public statement, Arunmor Corporation expressed concern\n"
            "about the research activities of rival firm ARC Technologies.\n"
            "\"We have reason to believe their current project poses a risk\n"
            "to network infrastructure worldwide,\" said a spokesperson."
        ),
        "Uplink News Network",
        gs.game_time_ticks,
    )
    _mark_scene_done(gs, SCENE_1_ARUNMOR_CONTACT, PLOT_ACT_1)


# --- Act 2: Bidding War ---

def _scene_2_arc_offer(gs):
    """ARC offers payment to test Revelation."""
    _send_plot_email(
        gs,
        subject="Job Offer — Test Our New Software",
        body=(
            "Agent,\n\n"
            "We have completed the first version of our software —\n"
            "codenamed 'Revelation'. We need a skilled agent to help us\n"
            "test it on a live target system.\n\n"
            f"We are prepared to pay {PLOT_PAYMENT_ARC:,} credits for your\n"
            "assistance. This is just the beginning — there will be more\n"
            "work and more payment to follow.\n\n"
            "Reply to this email to accept.\n\n"
            "-- ARC Technologies Administration"
        ),
        from_addr=PLOT_EMAIL_ARC,
    )
    _mark_scene_done(gs, SCENE_2_ARC_OFFER, PLOT_ACT_2)


def _scene_2_arun_offer(gs):
    """Arunmor offers payment to help counter the virus."""
    _send_plot_email(
        gs,
        subject="Urgent: Help Us Counter a Dangerous Program",
        body=(
            "Agent,\n\n"
            "Our analysts have confirmed our worst fears. ARC Technologies\n"
            "has developed a self-replicating virus called 'Revelation'.\n"
            "If released, it could destroy data across the entire network.\n\n"
            "We are developing a counter-virus called 'Faith' and need\n"
            "a skilled agent to help us analyze and deploy it.\n\n"
            f"We can offer {PLOT_PAYMENT_ARUNMOR:,} credits for your help.\n\n"
            "Reply to this email to accept.\n\n"
            "-- Arunmor Research Division"
        ),
        from_addr=PLOT_EMAIL_ARUNMOR,
    )
    _mark_scene_done(gs, SCENE_2_ARUN_OFFER, PLOT_ACT_2)


def _scene_2_news_virus(gs):
    """News articles about mysterious system failures."""
    generate_news_article(
        gs.id,
        "Multiple corporate systems experience unexplained failures",
        (
            "Multiple corporate systems experience unexplained failures.\n\n"
            "At least three major corporations have reported catastrophic\n"
            "data loss in the past 24 hours. Security experts are baffled\n"
            "by the pattern of failures, which appear to target core system\n"
            "files. Some analysts suspect a new form of malware, though no\n"
            "samples have been recovered."
        ),
        "Uplink News Network",
        gs.game_time_ticks,
    )
    generate_news_article(
        gs.id,
        "Network security firms report surge in anomalous traffic",
        (
            "Network security firms report surge in anomalous traffic.\n\n"
            "Several major security monitoring firms have detected unusual\n"
            "traffic patterns across the global network. The traffic appears\n"
            "to originate from compromised corporate servers and exhibits\n"
            "self-replicating behavior. Experts warn this could be the\n"
            "precursor to a large-scale attack."
        ),
        "Uplink News Network",
        gs.game_time_ticks,
    )
    _mark_scene_done(gs, SCENE_2_NEWS_VIRUS, PLOT_ACT_2)


def _scene_2_arc_sweeten(gs):
    """ARC sweetens the deal."""
    if gs.player_loyalty != FACTION_NONE:
        _mark_scene_done(gs, SCENE_2_ARC_SWEETEN, PLOT_ACT_2)
        return

    _send_plot_email(
        gs,
        subject="Increased Offer — Don't Miss This Opportunity",
        body=(
            "Agent,\n\n"
            "We understand you may be weighing your options. Let us make\n"
            "this easier for you.\n\n"
            "We are prepared to offer 10,000 credits for your assistance,\n"
            "plus access to our advanced tools and technology. Revelation\n"
            "is the future — and you can be part of it.\n\n"
            "Arunmor will tell you we're dangerous. They're afraid of\n"
            "progress. Don't let their fear hold you back.\n\n"
            "Reply to accept.\n\n"
            "-- ARC Technologies Administration"
        ),
        from_addr=PLOT_EMAIL_ARC,
    )
    _mark_scene_done(gs, SCENE_2_ARC_SWEETEN, PLOT_ACT_2)


def _scene_2_arun_sweeten(gs):
    """Arunmor sweetens the deal."""
    if gs.player_loyalty != FACTION_NONE:
        _mark_scene_done(gs, SCENE_2_ARUN_SWEETEN, PLOT_ACT_2)
        return

    _send_plot_email(
        gs,
        subject="The Threat Is Real — We Need You",
        body=(
            "Agent,\n\n"
            "The situation is worsening. More systems are going dark every\n"
            "day. Revelation is spreading faster than we anticipated.\n\n"
            "We are increasing our offer to 9,000 credits, and we will\n"
            "give you access to our Faith counter-virus technology.\n\n"
            "ARC may offer more money, but ask yourself: what happens\n"
            "when Revelation destroys the network you work on? There\n"
            "won't be any systems left to hack.\n\n"
            "Reply to accept. Time is running out.\n\n"
            "-- Arunmor Research Division"
        ),
        from_addr=PLOT_EMAIL_ARUNMOR,
    )
    _mark_scene_done(gs, SCENE_2_ARUN_SWEETEN, PLOT_ACT_2)


# --- Act 3: The Choice ---

def _scene_3_choice_prompt(gs):
    """Both factions send final urgent emails."""
    if gs.player_loyalty != FACTION_NONE:
        _mark_scene_done(gs, SCENE_3_CHOICE_PROMPT, PLOT_ACT_3)
        return

    _send_plot_email(
        gs,
        subject="FINAL OFFER — Last Chance",
        body=(
            "Agent,\n\n"
            "This is your last chance. We are about to begin full\n"
            "deployment of Revelation. Once it's released, there's\n"
            "no going back.\n\n"
            "Join us now and be on the winning side. 10,000 credits\n"
            "and a place in the new order.\n\n"
            "Reply NOW to accept. After today, the offer is withdrawn.\n\n"
            "-- ARC Technologies Administration"
        ),
        from_addr=PLOT_EMAIL_ARC,
    )
    _send_plot_email(
        gs,
        subject="URGENT: ARC Is About to Release Revelation",
        body=(
            "Agent,\n\n"
            "This is it. Our intelligence indicates ARC Technologies is\n"
            "preparing to release Revelation across the global network.\n\n"
            "If they succeed, the damage will be catastrophic and\n"
            "irreversible. Every server, every database, every system\n"
            "you've ever connected to — gone.\n\n"
            "We need your help NOW. 9,000 credits and full access to\n"
            "the Faith counter-virus.\n\n"
            "Reply to this email to join us. There is no more time.\n\n"
            "-- Arunmor Research Division"
        ),
        from_addr=PLOT_EMAIL_ARUNMOR,
    )
    _mark_scene_done(gs, SCENE_3_CHOICE_PROMPT, PLOT_ACT_3)


# --- Plot email detection and reply handling ---

_PLOT_ADDRESSES = {PLOT_EMAIL_ARC, PLOT_EMAIL_ARUNMOR}


def is_plot_email(email):
    """Return True if the email is from a plot faction."""
    return email.from_addr in _PLOT_ADDRESSES


def handle_plot_reply(gs, email):
    """Handle a player's reply to a plot email.

    Returns (handled: bool, message: str).
    """
    # Acts 4-5: check if this is a plot mission completion reply
    if gs.plot_act >= PLOT_ACT_4 and gs.player_loyalty != FACTION_NONE:
        return _handle_plot_mission_reply(gs, email)

    # Only allow loyalty replies during Acts 2-3
    if gs.plot_act < PLOT_ACT_2:
        return True, "You read the email with interest, but it's too early to commit."

    # Already chose a side
    if gs.player_loyalty != FACTION_NONE:
        if gs.player_loyalty == FACTION_ARC:
            faction_name = "ARC Technologies"
        else:
            faction_name = "Arunmor Corporation"
        return True, f"You have already pledged loyalty to {faction_name}."

    # Lock loyalty based on which faction the email is from
    if email.from_addr == PLOT_EMAIL_ARC:
        gs.player_loyalty = FACTION_ARC
        faction_name = "ARC Technologies"
        payment = 10000  # sweetened offer
        _send_plot_email(
            gs,
            subject="Welcome Aboard — ARC Technologies",
            body=(
                "Excellent decision, Agent.\n\n"
                f"We have transferred {payment:,} credits to your account\n"
                "as a sign of good faith.\n\n"
                "Revelation is nearly ready for deployment. We will contact\n"
                "you shortly with your first assignment.\n\n"
                "You've chosen the winning side.\n\n"
                "-- ARC Technologies Administration"
            ),
            from_addr=PLOT_EMAIL_ARC,
        )
        gs.balance += payment
        generate_news_article(
            gs.id,
            "ARC Technologies reportedly recruits elite hacker",
            (
                "ARC Technologies reportedly recruits elite hacker.\n\n"
                "Sources within the underground hacking community suggest\n"
                "that ARC Technologies has recruited a top Uplink agent\n"
                "to assist with their controversial Revelation project.\n"
                "Arunmor Corporation declined to comment on the development."
            ),
            "Uplink News Network",
            gs.game_time_ticks,
        )

    elif email.from_addr == PLOT_EMAIL_ARUNMOR:
        gs.player_loyalty = FACTION_ARUNMOR
        faction_name = "Arunmor Corporation"
        payment = 9000  # sweetened offer
        _send_plot_email(
            gs,
            subject="Thank You — Arunmor Corporation",
            body=(
                "Agent, thank you. You've made the right choice.\n\n"
                f"We have transferred {payment:,} credits to your account.\n\n"
                "Our team is preparing the Faith counter-virus for deployment.\n"
                "We will need your help to get it onto key systems before\n"
                "ARC releases Revelation.\n\n"
                "Stand by for your first assignment.\n\n"
                "-- Arunmor Research Division"
            ),
            from_addr=PLOT_EMAIL_ARUNMOR,
        )
        gs.balance += payment
        generate_news_article(
            gs.id,
            "Arunmor Corporation enlists agent in fight against cyber threat",
            (
                "Arunmor Corporation enlists agent in fight against cyber threat.\n\n"
                "Arunmor Corporation has reportedly secured the services of\n"
                "a skilled Uplink agent to assist in countering what they\n"
                "describe as an imminent threat to global network security.\n"
                "ARC Technologies dismissed the claims as 'alarmist'."
            ),
            "Uplink News Network",
            gs.game_time_ticks,
        )

    else:
        return False, "This email is not from a plot faction."

    gs.plot_scene = SCENE_3_PLAYER_CHOSE
    data = gs.plot_data
    data[f"scene_done_{SCENE_3_PLAYER_CHOSE}"] = True
    data["loyalty_locked_tick"] = gs.game_time_ticks
    gs.plot_data = data

    # Schedule Act 4 start
    _schedule_next(gs, PLOT_ACT4_DELAY)

    db.session.commit()
    return True, f"You have pledged your loyalty to {faction_name}. Payment received: {payment:,} credits."


def _handle_plot_mission_reply(gs, email):
    """Handle replies during Acts 4-5 — check if plot mission objectives are met."""
    faction_name, _, faction_email, _ = _get_faction_names(gs)

    # Only handle replies to the player's faction
    if gs.player_loyalty == FACTION_ARC and email.from_addr != PLOT_EMAIL_ARC:
        return True, "This email is from the rival faction."
    if gs.player_loyalty == FACTION_ARUNMOR and email.from_addr != PLOT_EMAIL_ARUNMOR:
        return True, "This email is from the rival faction."

    # Find the active plot mission
    plot_mission = Mission.query.filter(
        Mission.game_session_id == gs.id,
        Mission.status == MISSION_ACCEPTED,
        Mission.mission_type.in_([MISSION_PLOT_STEAL, MISSION_PLOT_DESTROY, MISSION_PLOT_DEPLOY]),
    ).first()

    if not plot_mission:
        return True, f"You are working with {faction_name}. Stand by for your next assignment."

    # Check completion based on mission type
    from .mission_engine import check_mission_completion
    ok, msg = check_mission_completion(gs.id, plot_mission.id)
    if ok:
        # Advance plot based on which mission was completed
        _on_plot_mission_complete(gs, plot_mission)
        return True, msg
    return False, msg


def _on_plot_mission_complete(gs, mission):
    """Advance the plot after a plot mission is completed."""
    data = gs.plot_data

    if mission.mission_type == MISSION_PLOT_STEAL:
        # Mission 1 complete — increment our virus version
        if gs.player_loyalty == FACTION_ARC:
            _bump_version(gs, "version_revelation", +1)
        else:
            _bump_version(gs, "version_faith", +1)
        gs.plot_scene = SCENE_4_MISSION_1_DONE
        gs.plot_act = PLOT_ACT_4
        data[f"scene_done_{SCENE_4_MISSION_1_DONE}"] = True
        gs.plot_data = data
        _schedule_next(gs, PLOT_MISSION_INTERVAL)
        _fire_escalation_news(gs)

    elif mission.mission_type == MISSION_PLOT_DESTROY:
        # Mission 2 complete — decrement rival's version
        if gs.player_loyalty == FACTION_ARC:
            _bump_version(gs, "version_faith", -1)
        else:
            _bump_version(gs, "version_revelation", -1)
        gs.plot_scene = SCENE_4_MISSION_2_DONE
        gs.plot_act = PLOT_ACT_4
        data[f"scene_done_{SCENE_4_MISSION_2_DONE}"] = True
        gs.plot_data = data
        _schedule_next(gs, PLOT_ACT5_DELAY)

    elif mission.mission_type == MISSION_PLOT_DEPLOY:
        # Deployment complete — trigger warfare news, then resolution
        gs.plot_scene = SCENE_5_WARFARE_1
        gs.plot_act = PLOT_ACT_5
        data[f"scene_done_{SCENE_5_WARFARE_1}"] = True
        gs.plot_data = data
        _fire_warfare_1_news(gs)
        _schedule_next(gs, PLOT_MISSION_INTERVAL)


def _bump_version(gs, attr, delta):
    """Increment or decrement a version string like '1.0' by delta."""
    current = getattr(gs, attr) or "1.0"
    try:
        major = int(float(current))
    except (ValueError, TypeError):
        major = 1
    major = max(0, major + delta)
    setattr(gs, attr, f"{major}.0")


# --- Act 4: Special Missions ---

def _start_act_4(gs):
    """Called after loyalty lock + delay. Sends first faction-specific mission."""
    gs.plot_act = PLOT_ACT_4
    _scene_4_mission_1(gs)


def _scene_4_mission_1(gs):
    """Create the first faction-specific mission (steal data from rival)."""
    faction_name, rival_name, faction_email, rival_ip = _get_faction_names(gs)

    if gs.player_loyalty == FACTION_ARC:
        target_file = "faith_research.dat"
        description = "Steal Faith research data from Arunmor"
        details = (
            f"We need a copy of Arunmor's Faith counter-virus research.\n"
            f"The file '{target_file}' is on their Internal Services Machine."
        )
        full_details = (
            f"Target: Arunmor Corporation ISM\n"
            f"IP: {rival_ip}\n"
            f"File: {target_file}\n\n"
            f"Arunmor is developing a counter-virus called 'Faith' that could\n"
            f"neutralize Revelation. We need their research data.\n\n"
            f"Connect to {rival_ip}, bypass security, locate the file server,\n"
            f"and use File Copier to download '{target_file}' to your gateway.\n\n"
            f"Once you have the file, reply to this email to confirm."
        )
    else:
        target_file = "revelation_spec.dat"
        description = "Steal Revelation specs from ARC"
        details = (
            f"We need ARC's Revelation virus specifications.\n"
            f"The file '{target_file}' is on their Internal Services Machine."
        )
        full_details = (
            f"Target: ARC Technologies ISM\n"
            f"IP: {rival_ip}\n"
            f"File: {target_file}\n\n"
            f"ARC's Revelation virus is evolving rapidly. We need their\n"
            f"technical specifications to update our Faith counter-virus.\n\n"
            f"Connect to {rival_ip}, bypass security, locate the file server,\n"
            f"and use File Copier to download '{target_file}' to your gateway.\n\n"
            f"Once you have the file, reply to this email to confirm."
        )

    mission = Mission(
        game_session_id=gs.id,
        mission_type=MISSION_PLOT_STEAL,
        employer=faction_name,
        contact=faction_email,
        description=description,
        details=details,
        full_details=full_details,
        target_ip=rival_ip,
        target_filename=target_file,
        target_data={"rival_name": rival_name},
        payment=PLOT_MISSION_1_PAYMENT,
        difficulty=3,
        min_rating=0,
        status=MISSION_ACCEPTED,
        created_at_tick=gs.game_time_ticks,
        accepted_at_tick=gs.game_time_ticks,
    )
    db.session.add(mission)

    _send_plot_email(
        gs,
        subject=f"Assignment: {description}",
        body=(
            f"Agent,\n\n"
            f"{full_details}\n\n"
            f"Payment on completion: {PLOT_MISSION_1_PAYMENT:,} credits.\n\n"
            f"-- {faction_name}"
        ),
        from_addr=faction_email,
    )

    gs.plot_scene = SCENE_4_MISSION_1
    data = gs.plot_data
    data[f"scene_done_{SCENE_4_MISSION_1}"] = True
    gs.plot_data = data
    # Set polling interval — check every 200 ticks if player completed it
    _schedule_next(gs, 200)


def _check_plot_mission_1(gs):
    """Poll for mission 1 completion. If not done, reschedule."""
    mission = Mission.query.filter_by(
        game_session_id=gs.id,
        mission_type=MISSION_PLOT_STEAL,
        status=MISSION_ACCEPTED,
    ).first()

    if mission:
        # Still in progress — reschedule check
        _schedule_next(gs, 200)
        return

    # Mission was completed (via reply) — scene should already be advanced
    # If somehow we get here and mission is completed but scene wasn't advanced
    completed = Mission.query.filter_by(
        game_session_id=gs.id,
        mission_type=MISSION_PLOT_STEAL,
        status=MISSION_COMPLETED,
    ).first()
    if completed and gs.plot_scene == SCENE_4_MISSION_1:
        _on_plot_mission_complete(gs, completed)


def _scene_4_mission_2(gs):
    """Create the second faction-specific mission (destroy rival's data)."""
    faction_name, rival_name, faction_email, rival_ip = _get_faction_names(gs)

    if gs.player_loyalty == FACTION_ARC:
        target_file = "countermeasure_spec.dat"
        description = "Destroy Arunmor's counter-virus research"
        details = (
            f"Destroy Arunmor's counter-virus specifications.\n"
            f"Delete '{target_file}' from their Internal Services Machine."
        )
        full_details = (
            f"Target: Arunmor Corporation ISM\n"
            f"IP: {rival_ip}\n"
            f"File: {target_file}\n\n"
            f"Arunmor is close to completing their Faith counter-virus.\n"
            f"We need you to destroy their research data to set them back.\n\n"
            f"Connect to {rival_ip}, bypass security, locate the file server,\n"
            f"and use File Deleter to destroy '{target_file}'.\n\n"
            f"Once the file is destroyed, reply to this email to confirm."
        )
    else:
        target_file = "test_results.dat"
        description = "Destroy ARC's test results"
        details = (
            f"Destroy ARC's Revelation test results.\n"
            f"Delete '{target_file}' from their Internal Services Machine."
        )
        full_details = (
            f"Target: ARC Technologies ISM\n"
            f"IP: {rival_ip}\n"
            f"File: {target_file}\n\n"
            f"ARC has been testing Revelation on live systems. Their test\n"
            f"results contain critical data for the next version.\n\n"
            f"Connect to {rival_ip}, bypass security, locate the file server,\n"
            f"and use File Deleter to destroy '{target_file}'.\n\n"
            f"Once the file is destroyed, reply to this email to confirm."
        )

    mission = Mission(
        game_session_id=gs.id,
        mission_type=MISSION_PLOT_DESTROY,
        employer=faction_name,
        contact=faction_email,
        description=description,
        details=details,
        full_details=full_details,
        target_ip=rival_ip,
        target_filename=target_file,
        target_data={"rival_name": rival_name},
        payment=PLOT_MISSION_2_PAYMENT,
        difficulty=3,
        min_rating=0,
        status=MISSION_ACCEPTED,
        created_at_tick=gs.game_time_ticks,
        accepted_at_tick=gs.game_time_ticks,
    )
    db.session.add(mission)

    _send_plot_email(
        gs,
        subject=f"Assignment: {description}",
        body=(
            f"Agent,\n\n"
            f"{full_details}\n\n"
            f"Payment on completion: {PLOT_MISSION_2_PAYMENT:,} credits.\n\n"
            f"-- {faction_name}"
        ),
        from_addr=faction_email,
    )

    gs.plot_scene = SCENE_4_MISSION_2
    data = gs.plot_data
    data[f"scene_done_{SCENE_4_MISSION_2}"] = True
    gs.plot_data = data
    _schedule_next(gs, 200)


def _check_plot_mission_2(gs):
    """Poll for mission 2 completion. If not done, reschedule."""
    mission = Mission.query.filter_by(
        game_session_id=gs.id,
        mission_type=MISSION_PLOT_DESTROY,
        status=MISSION_ACCEPTED,
    ).first()

    if mission:
        _schedule_next(gs, 200)
        return

    completed = Mission.query.filter_by(
        game_session_id=gs.id,
        mission_type=MISSION_PLOT_DESTROY,
        status=MISSION_COMPLETED,
    ).first()
    if completed and gs.plot_scene == SCENE_4_MISSION_2:
        _on_plot_mission_complete(gs, completed)


def _fire_escalation_news(gs):
    """Generate news about the virus war escalating (between Act 4 missions)."""
    if gs.player_loyalty == FACTION_ARC:
        generate_news_article(
            gs.id,
            "Classified data stolen from Arunmor Corporation",
            (
                "Classified data stolen from Arunmor Corporation.\n\n"
                "Arunmor Corporation has confirmed a major security breach\n"
                "at their internal systems. Sources indicate that research\n"
                "data related to their counter-virus project was copied\n"
                "by an unknown intruder. The company has refused to comment\n"
                "on the scope of the breach."
            ),
            "Uplink News Network",
            gs.game_time_ticks,
        )
    else:
        generate_news_article(
            gs.id,
            "Classified data stolen from ARC Technologies",
            (
                "Classified data stolen from ARC Technologies.\n\n"
                "ARC Technologies has suffered a significant data breach.\n"
                "Sources indicate that technical specifications for their\n"
                "controversial Revelation project were copied from their\n"
                "internal servers. ARC has declined to comment on the\n"
                "security implications."
            ),
            "Uplink News Network",
            gs.game_time_ticks,
        )


# --- Act 5: Deployment ---

def _start_act_5(gs):
    """Send the final deployment mission."""
    gs.plot_act = PLOT_ACT_5
    faction_name, rival_name, faction_email, rival_ip = _get_faction_names(gs)

    if gs.player_loyalty == FACTION_ARC:
        target_file = "revelation.dat"
        target_ip = IP_UPLINK_TEST
        description = "Deploy Revelation on the Uplink Test Machine"
        details = (
            f"Upload Revelation to the Uplink Test Machine to demonstrate\n"
            f"its power to the world."
        )
        full_details = (
            f"Target: Uplink Public Test Machine\n"
            f"IP: {target_ip}\n"
            f"File: {target_file}\n\n"
            f"The time has come. Revelation is ready for deployment.\n"
            f"Upload '{target_file}' from your gateway to the Uplink\n"
            f"Test Machine. This will trigger the final phase.\n\n"
            f"Connect to {target_ip}, access the file server, and use\n"
            f"File Copier to upload the file.\n\n"
            f"Once deployed, reply to this email to confirm."
        )
    else:
        target_file = "faith.dat"
        target_ip = IP_ARC
        description = "Deploy Faith on ARC's systems"
        details = (
            f"Upload the Faith counter-virus to ARC's Internal Services\n"
            f"Machine to neutralize Revelation at its source."
        )
        full_details = (
            f"Target: ARC Technologies ISM\n"
            f"IP: {target_ip}\n"
            f"File: {target_file}\n\n"
            f"We have completed the Faith counter-virus. It's time to\n"
            f"deploy it directly onto ARC's systems.\n\n"
            f"Upload '{target_file}' from your gateway to ARC's ISM.\n"
            f"This will neutralize Revelation before it can spread further.\n\n"
            f"Connect to {target_ip}, access the file server, and use\n"
            f"File Copier to upload the file.\n\n"
            f"Once deployed, reply to this email to confirm."
        )

    # Create the deploy file on the player's gateway if not present
    gw = Computer.query.filter_by(
        game_session_id=gs.id, ip=gs.gateway_ip
    ).first()
    if gw:
        existing = DataFile.query.filter_by(
            computer_id=gw.id, filename=target_file
        ).first()
        if not existing:
            db.session.add(DataFile(
                computer_id=gw.id,
                filename=target_file,
                size=2,
                file_type="PLOT",
            ))

    mission = Mission(
        game_session_id=gs.id,
        mission_type=MISSION_PLOT_DEPLOY,
        employer=faction_name,
        contact=faction_email,
        description=description,
        details=details,
        full_details=full_details,
        target_ip=target_ip,
        target_filename=target_file,
        target_data={"deploy_target_ip": target_ip},
        payment=PLOT_DEPLOY_PAYMENT,
        difficulty=4,
        min_rating=0,
        status=MISSION_ACCEPTED,
        created_at_tick=gs.game_time_ticks,
        accepted_at_tick=gs.game_time_ticks,
    )
    db.session.add(mission)

    _send_plot_email(
        gs,
        subject=f"FINAL ASSIGNMENT: {description}",
        body=(
            f"Agent,\n\n"
            f"{full_details}\n\n"
            f"Payment on completion: {PLOT_DEPLOY_PAYMENT:,} credits.\n\n"
            f"This is it. Make it count.\n\n"
            f"-- {faction_name}"
        ),
        from_addr=faction_email,
    )

    gs.plot_scene = SCENE_5_DEPLOYMENT
    data = gs.plot_data
    data[f"scene_done_{SCENE_5_DEPLOYMENT}"] = True
    gs.plot_data = data
    _schedule_next(gs, 200)


def _check_plot_deploy(gs):
    """Poll for deployment mission completion."""
    mission = Mission.query.filter_by(
        game_session_id=gs.id,
        mission_type=MISSION_PLOT_DEPLOY,
        status=MISSION_ACCEPTED,
    ).first()

    if mission:
        _schedule_next(gs, 200)
        return

    completed = Mission.query.filter_by(
        game_session_id=gs.id,
        mission_type=MISSION_PLOT_DEPLOY,
        status=MISSION_COMPLETED,
    ).first()
    if completed and gs.plot_scene == SCENE_5_DEPLOYMENT:
        _on_plot_mission_complete(gs, completed)


def _fire_warfare_1_news(gs):
    """News about viral warfare beginning."""
    if gs.player_loyalty == FACTION_ARC:
        generate_news_article(
            gs.id,
            "Revelation virus detected on multiple systems worldwide",
            (
                "Revelation virus detected on multiple systems worldwide.\n\n"
                "The self-replicating virus known as 'Revelation' has been\n"
                "detected on systems across the global network. The virus\n"
                "appears to destroy data indiscriminately, leaving affected\n"
                "systems completely inoperable. Security firms are scrambling\n"
                "to develop countermeasures."
            ),
            "Uplink News Network",
            gs.game_time_ticks,
        )
    else:
        generate_news_article(
            gs.id,
            "Counter-virus 'Faith' deployed against Revelation threat",
            (
                "Counter-virus 'Faith' deployed against Revelation threat.\n\n"
                "Arunmor Corporation has announced the deployment of their\n"
                "counter-virus 'Faith' in a bid to neutralize the Revelation\n"
                "virus. Early reports suggest the counter-virus is successfully\n"
                "containing the spread on systems where it has been installed."
            ),
            "Uplink News Network",
            gs.game_time_ticks,
        )


def _scene_5_warfare_2(gs):
    """News about warfare intensifying."""
    if gs.player_loyalty == FACTION_ARC:
        generate_news_article(
            gs.id,
            "Viral warfare between corporations intensifies",
            (
                "Viral warfare between corporations intensifies.\n\n"
                "The battle between ARC Technologies' Revelation virus and\n"
                "Arunmor Corporation's Faith counter-virus has escalated.\n"
                "Dozens of systems have been caught in the crossfire as both\n"
                "programs fight for dominance. Network administrators worldwide\n"
                "are reporting unprecedented levels of automated activity."
            ),
            "Uplink News Network",
            gs.game_time_ticks,
        )
        generate_news_article(
            gs.id,
            "Arunmor's defenses faltering against Revelation onslaught",
            (
                "Arunmor's defenses faltering against Revelation onslaught.\n\n"
                "Sources close to Arunmor Corporation indicate that their\n"
                "Faith counter-virus is struggling to keep up with the\n"
                "latest version of Revelation. Several key systems have\n"
                "already fallen to the virus despite Arunmor's best efforts."
            ),
            "Uplink News Network",
            gs.game_time_ticks,
        )
    else:
        generate_news_article(
            gs.id,
            "Viral warfare between corporations intensifies",
            (
                "Viral warfare between corporations intensifies.\n\n"
                "The battle between ARC Technologies' Revelation virus and\n"
                "Arunmor Corporation's Faith counter-virus has reached a\n"
                "critical stage. Faith appears to be gaining the upper hand\n"
                "on most systems, though isolated pockets of Revelation\n"
                "continue to cause damage."
            ),
            "Uplink News Network",
            gs.game_time_ticks,
        )
        generate_news_article(
            gs.id,
            "Revelation virus losing ground as Faith spreads",
            (
                "Revelation virus losing ground as Faith spreads.\n\n"
                "Network analysts report that the Revelation virus is being\n"
                "systematically neutralized by Arunmor's Faith counter-virus.\n"
                "ARC Technologies has not commented on the apparent failure\n"
                "of their creation."
            ),
            "Uplink News Network",
            gs.game_time_ticks,
        )

    gs.plot_scene = SCENE_5_WARFARE_2
    data = gs.plot_data
    data[f"scene_done_{SCENE_5_WARFARE_2}"] = True
    gs.plot_data = data
    _schedule_next(gs, PLOT_MISSION_INTERVAL)


def _scene_5_resolution(gs):
    """Determine the outcome of the virus war."""
    data = gs.plot_data

    if gs.player_loyalty == FACTION_ARC:
        # ARC victory — Revelation spreads
        data["ending"] = "arc_victory"
        generate_news_article(
            gs.id,
            "BREAKING: Revelation virus overwhelms global network defenses",
            (
                "BREAKING: Revelation virus overwhelms global network defenses.\n\n"
                "In a devastating blow to the global computing infrastructure,\n"
                "ARC Technologies' Revelation virus has overwhelmed all known\n"
                "countermeasures. Arunmor Corporation's Faith counter-virus\n"
                "has proven unable to contain the latest version of Revelation.\n\n"
                "Experts estimate that over 60% of connected systems have been\n"
                "affected. The long-term implications are still being assessed."
            ),
            "Uplink News Network",
            gs.game_time_ticks,
        )
    else:
        # Arunmor victory — Faith stops Revelation
        data["ending"] = "arunmor_victory"
        generate_news_article(
            gs.id,
            "BREAKING: Faith counter-virus successfully neutralizes Revelation",
            (
                "BREAKING: Faith counter-virus successfully neutralizes Revelation.\n\n"
                "Arunmor Corporation has announced that their Faith counter-virus\n"
                "has successfully contained and neutralized the Revelation virus\n"
                "across all major network systems. The threat that had paralyzed\n"
                "the global computing infrastructure appears to be over.\n\n"
                "ARC Technologies has gone silent following the apparent failure\n"
                "of their creation."
            ),
            "Uplink News Network",
            gs.game_time_ticks,
        )

    gs.plot_scene = SCENE_5_RESOLUTION
    gs.plot_act = PLOT_ACT_5
    data[f"scene_done_{SCENE_5_RESOLUTION}"] = True
    gs.plot_data = data
    _schedule_next(gs, PLOT_ACT6_DELAY)


# --- Act 6: Epilogue ---

def _scene_6_aftermath(gs):
    """Post-resolution news about consequences."""
    gs.plot_act = PLOT_ACT_6
    data = gs.plot_data
    ending = data.get("ending", "")

    if ending == "arc_victory":
        generate_news_article(
            gs.id,
            "Arunmor Corporation files for bankruptcy after Revelation disaster",
            (
                "Arunmor Corporation files for bankruptcy after Revelation disaster.\n\n"
                "Arunmor Corporation, the firm that had attempted to counter ARC\n"
                "Technologies' Revelation virus, has filed for bankruptcy protection.\n"
                "The company's failure to stop the virus has been blamed for\n"
                "billions in damages to global computing infrastructure.\n\n"
                "Former employees describe a 'valiant but ultimately futile' effort\n"
                "to develop the Faith counter-virus in time."
            ),
            "Uplink News Network",
            gs.game_time_ticks,
        )
    else:
        generate_news_article(
            gs.id,
            "ARC Technologies raided by authorities in dawn operation",
            (
                "ARC Technologies raided by authorities in dawn operation.\n\n"
                "Law enforcement agencies have raided the headquarters of\n"
                "ARC Technologies following the Revelation virus crisis.\n"
                "Multiple senior executives have been detained for questioning.\n\n"
                "Authorities allege that ARC knowingly developed and deployed\n"
                "the Revelation virus, causing widespread damage to global\n"
                "computing systems before it was neutralized by Arunmor's\n"
                "Faith counter-virus."
            ),
            "Uplink News Network",
            gs.game_time_ticks,
        )

    gs.plot_scene = SCENE_6_AFTERMATH
    data[f"scene_done_{SCENE_6_AFTERMATH}"] = True
    gs.plot_data = data
    _schedule_next(gs, PLOT_MISSION_INTERVAL)


def _scene_6_sentencing(gs):
    """ARC leader sentenced — news article."""
    data = gs.plot_data
    ending = data.get("ending", "")

    if ending == "arc_victory":
        generate_news_article(
            gs.id,
            "Arunmor leadership resigns amid recriminations",
            (
                "Arunmor leadership resigns amid recriminations.\n\n"
                "The entire board of directors of Arunmor Corporation has\n"
                "resigned following intense criticism of their failure to\n"
                "prevent the Revelation catastrophe. Shareholders have filed\n"
                "multiple lawsuits alleging negligence and mismanagement."
            ),
            "Uplink News Network",
            gs.game_time_ticks,
        )
    else:
        generate_news_article(
            gs.id,
            "ARC Technologies CEO sentenced to 8 years for cyber terrorism",
            (
                "ARC Technologies CEO sentenced to 8 years for cyber terrorism.\n\n"
                "The CEO of ARC Technologies has been sentenced to 8 years in\n"
                "prison for orchestrating the development and deployment of the\n"
                "Revelation virus. The judge described the virus as 'an act of\n"
                "technological warfare against the global computing community.'\n\n"
                "Several other ARC executives received lesser sentences for\n"
                "their roles in the conspiracy."
            ),
            "Uplink News Network",
            gs.game_time_ticks,
        )

    gs.plot_scene = SCENE_6_SENTENCING
    data[f"scene_done_{SCENE_6_SENTENCING}"] = True
    gs.plot_data = data
    _schedule_next(gs, PLOT_MISSION_INTERVAL)


def _scene_6_epilogue(gs):
    """Final retrospective article and congratulatory email. Marks plot complete."""
    data = gs.plot_data
    ending = data.get("ending", "")
    faction_name, _, faction_email, _ = _get_faction_names(gs)

    # Final news article
    if ending == "arc_victory":
        generate_news_article(
            gs.id,
            "Revelation: A Retrospective — The Virus That Changed Everything",
            (
                "Revelation: A Retrospective — The Virus That Changed Everything.\n\n"
                "One month after the Revelation virus swept through the global\n"
                "network, the world is still counting the cost. Thousands of\n"
                "systems remain offline. Entire databases have been lost forever.\n\n"
                "ARC Technologies' creation proved more powerful than anyone\n"
                "anticipated. While Arunmor Corporation's Faith counter-virus\n"
                "showed early promise, it ultimately could not keep pace with\n"
                "Revelation's self-evolving capabilities.\n\n"
                "The digital landscape has been permanently altered. Some call\n"
                "it a catastrophe. Others call it evolution."
            ),
            "Uplink News Network",
            gs.game_time_ticks,
        )
        _send_plot_email(
            gs,
            subject="A New World — ARC Technologies",
            body=(
                "Agent,\n\n"
                "Revelation has fulfilled its purpose. The old network is gone.\n"
                "A new one will rise in its place — one built on our technology.\n\n"
                "Your contributions were instrumental in making this happen.\n"
                "We will not forget your service.\n\n"
                "The future belongs to those who shape it.\n\n"
                "-- ARC Technologies Administration"
            ),
            from_addr=PLOT_EMAIL_ARC,
        )
    else:
        generate_news_article(
            gs.id,
            "Revelation: A Retrospective — The Crisis That Was Averted",
            (
                "Revelation: A Retrospective — The Crisis That Was Averted.\n\n"
                "One month after the Revelation virus crisis, the global\n"
                "network has largely recovered thanks to the deployment of\n"
                "Arunmor Corporation's Faith counter-virus.\n\n"
                "While some systems suffered permanent data loss during the\n"
                "brief period before Faith was deployed, the vast majority\n"
                "of the network was saved. Arunmor has been praised for their\n"
                "foresight in developing the counter-virus.\n\n"
                "With ARC Technologies' leadership behind bars, experts believe\n"
                "the threat of Revelation is permanently over."
            ),
            "Uplink News Network",
            gs.game_time_ticks,
        )
        _send_plot_email(
            gs,
            subject="Thank You — The World Is Safe",
            body=(
                "Agent,\n\n"
                "It's over. Faith has neutralized Revelation across the\n"
                "entire network. The world will never know how close it\n"
                "came to losing everything.\n\n"
                "Your skill and courage made all the difference. Without\n"
                "you, we could not have stopped ARC in time.\n\n"
                "The network is safe — thanks to you.\n\n"
                "-- Arunmor Research Division"
            ),
            from_addr=PLOT_EMAIL_ARUNMOR,
        )

    gs.plot_scene = SCENE_6_COMPLETE
    gs.plot_act = PLOT_ACT_6
    data[f"scene_done_{SCENE_6_EPILOGUE}"] = True
    data[f"scene_done_{SCENE_6_COMPLETE}"] = True
    data["plot_complete"] = True
    gs.plot_data = data
    gs.plot_next_scene_tick = 0  # No more scenes


# --- Plot status display ---

_ACT_NAMES = {
    PLOT_ACT_NONE: "Prologue",
    PLOT_ACT_1: "Act 1 — Introduction",
    PLOT_ACT_2: "Act 2 — The Bidding War",
    PLOT_ACT_3: "Act 3 — The Choice",
    PLOT_ACT_4: "Act 4 — Special Missions",
    PLOT_ACT_5: "Act 5 — Deployment",
    PLOT_ACT_6: "Act 6 — Endgame",
}

_LOYALTY_NAMES = {
    FACTION_NONE: "Neutral",
    FACTION_ARC: "ARC Technologies",
    FACTION_ARUNMOR: "Arunmor Corporation",
}


def get_plot_status(gs):
    """Return a dict with current plot status for display."""
    data = gs.plot_data
    status = {
        "act": gs.plot_act,
        "act_name": _ACT_NAMES.get(gs.plot_act, f"Act {gs.plot_act}"),
        "scene": gs.plot_scene,
        "loyalty": gs.player_loyalty,
        "loyalty_name": _LOYALTY_NAMES.get(gs.player_loyalty, "Unknown"),
        "plot_complete": data.get("plot_complete", False),
        "ending": data.get("ending", ""),
    }

    # Add current objective info for Acts 4-5
    if gs.plot_act == PLOT_ACT_4:
        plot_mission = Mission.query.filter(
            Mission.game_session_id == gs.id,
            Mission.status == MISSION_ACCEPTED,
            Mission.mission_type.in_([MISSION_PLOT_STEAL, MISSION_PLOT_DESTROY]),
        ).first()
        if plot_mission:
            status["current_objective"] = plot_mission.description
            status["current_target"] = plot_mission.target_ip
            status["current_file"] = plot_mission.target_filename
        else:
            status["current_objective"] = "Awaiting next assignment..."

    elif gs.plot_act == PLOT_ACT_5 and gs.plot_scene == SCENE_5_DEPLOYMENT:
        plot_mission = Mission.query.filter_by(
            game_session_id=gs.id,
            mission_type=MISSION_PLOT_DEPLOY,
            status=MISSION_ACCEPTED,
        ).first()
        if plot_mission:
            status["current_objective"] = plot_mission.description
            status["current_target"] = plot_mission.target_ip
            status["current_file"] = plot_mission.target_filename
        else:
            status["current_objective"] = "Deployment in progress..."

    return status
