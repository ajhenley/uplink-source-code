"""Mission generation, acceptance, completion, and expiry."""

import random

from ..extensions import db
from ..models import (
    Mission, Email, GameSession, Computer, DataFile, PlayerLink,
)
from .constants import *


def generate_missions(game_session_id, count=None):
    """Generate available missions for the BBS.

    Called on game creation and periodically from the game loop.
    """
    gs = db.session.get(GameSession, game_session_id)
    if not gs:
        return

    if count is None:
        count = random.randint(3, 5)

    # Find company ISMs with files (mission targets)
    isms = Computer.query.filter_by(
        game_session_id=game_session_id,
        computer_type=COMP_INTERNAL,
    ).all()

    # Filter to ISMs that have data files
    viable_targets = []
    for ism in isms:
        files = DataFile.query.filter_by(computer_id=ism.id).all()
        if files:
            viable_targets.append((ism, files))

    if not viable_targets:
        return

    mission_types = [MISSION_STEAL_FILE, MISSION_DESTROY_FILE]

    for _ in range(count):
        mtype = random.choice(mission_types)
        target_comp, target_files = random.choice(viable_targets)
        target_file = random.choice(target_files)

        # Determine payment with variance
        base_pay, variance = MISSION_PAYMENTS.get(mtype, (800, 0.3))
        payment = int(base_pay * (1 + random.uniform(-variance, variance)))

        # Pick an employer (different company from target)
        employer = target_comp.company_name

        # Generate mission text
        if mtype == MISSION_STEAL_FILE:
            description = f"Steal file from {employer}"
            details = (
                f"We need a copy of the file '{target_file.filename}' "
                f"from the {employer} Internal Services Machine."
            )
            full_details = (
                f"Target: {employer} Internal Services Machine\n"
                f"IP: {target_comp.ip}\n"
                f"File: {target_file.filename}\n\n"
                f"Copy the file '{target_file.filename}' from the target system.\n"
                f"You will need to bypass the login, locate the file server,\n"
                f"and use a File Copier to download the file.\n\n"
                f"Once you have the file, reply to the mission email to confirm."
            )
        else:  # DESTROY_FILE
            description = f"Destroy file on {employer}"
            details = (
                f"We need the file '{target_file.filename}' deleted "
                f"from the {employer} Internal Services Machine."
            )
            full_details = (
                f"Target: {employer} Internal Services Machine\n"
                f"IP: {target_comp.ip}\n"
                f"File: {target_file.filename}\n\n"
                f"Delete the file '{target_file.filename}' from the target system.\n"
                f"You will need to bypass the login, locate the file server,\n"
                f"and use a File Deleter to remove the file.\n\n"
                f"Once the file is destroyed, reply to the mission email to confirm."
            )

        mission = Mission(
            game_session_id=game_session_id,
            mission_type=mtype,
            employer=employer,
            contact=f"internal@{employer.lower().replace(' ', '')}.co.uk",
            description=description,
            details=details,
            full_details=full_details,
            target_ip=target_comp.ip,
            target_filename=target_file.filename,
            target_data={"computer_name": target_comp.name},
            payment=payment,
            difficulty=1,
            min_rating=0,
            status=MISSION_AVAILABLE,
            created_at_tick=gs.game_time_ticks,
        )
        db.session.add(mission)

    db.session.commit()


def accept_mission(game_session_id, mission_id):
    """Accept a mission from the BBS.

    Returns:
        (success: bool, message: str)
    """
    gs = db.session.get(GameSession, game_session_id)
    if not gs:
        return False, "No active game session."

    mission = db.session.get(Mission, mission_id)
    if not mission or mission.game_session_id != game_session_id:
        return False, "Mission not found."

    if mission.status != MISSION_AVAILABLE:
        return False, f"Mission is {mission.status.lower()}, not available."

    if gs.uplink_rating < mission.min_rating:
        return False, "Your rating is too low for this mission."

    # Accept the mission
    mission.status = MISSION_ACCEPTED
    mission.accepted_at_tick = gs.game_time_ticks

    # Send mission details email
    email = Email(
        game_session_id=game_session_id,
        subject=f"Mission: {mission.description}",
        body=(
            f"Mission accepted.\n\n"
            f"{mission.full_details}\n\n"
            f"Payment on completion: {mission.payment} credits.\n\n"
            f"Reply to this email when the mission is complete."
        ),
        from_addr=mission.contact,
        to_addr="agent@uplink.co.uk",
        game_tick_sent=gs.game_time_ticks,
    )
    db.session.add(email)

    # Add target IP to player links if not already there
    existing_link = PlayerLink.query.filter_by(
        game_session_id=game_session_id, ip=mission.target_ip
    ).first()
    if not existing_link:
        target_comp = Computer.query.filter_by(
            game_session_id=game_session_id, ip=mission.target_ip
        ).first()
        label = target_comp.name if target_comp else mission.target_ip
        db.session.add(PlayerLink(
            game_session_id=game_session_id,
            ip=mission.target_ip,
            label=label,
        ))

    db.session.commit()
    return True, f"Mission accepted. Check your email for details. Target: {mission.target_ip}"


def check_mission_completion(game_session_id, mission_id):
    """Check if a mission's objectives have been met.

    Returns:
        (success: bool, message: str)
    """
    gs = db.session.get(GameSession, game_session_id)
    if not gs:
        return False, "No active game session."

    mission = db.session.get(Mission, mission_id)
    if not mission or mission.game_session_id != game_session_id:
        return False, "Mission not found."

    if mission.status != MISSION_ACCEPTED:
        return False, f"Mission is {mission.status.lower()}, cannot complete."

    # Check objectives based on type
    if mission.mission_type == MISSION_STEAL_FILE:
        ok, msg = _check_steal_file(gs, mission)
    elif mission.mission_type == MISSION_DESTROY_FILE:
        ok, msg = _check_destroy_file(gs, mission)
    else:
        return False, "Unknown mission type."

    if not ok:
        return False, msg

    # Mission complete — pay the player
    mission.status = MISSION_COMPLETED
    mission.completed_at_tick = gs.game_time_ticks
    gs.balance += mission.payment

    # Increase rating
    rating_gain = RATING_GAIN.get(mission.mission_type, 1)
    gs.uplink_rating += rating_gain

    # Send completion email
    email = Email(
        game_session_id=game_session_id,
        subject=f"Re: Mission: {mission.description}",
        body=(
            f"Mission completed successfully.\n\n"
            f"Payment: {mission.payment} credits transferred.\n"
            f"Rating increase: +{rating_gain}\n\n"
            f"Good work, agent."
        ),
        from_addr=mission.contact,
        to_addr="agent@uplink.co.uk",
        game_tick_sent=gs.game_time_ticks,
    )
    db.session.add(email)
    db.session.commit()

    return True, (
        f"Mission complete! Payment: {mission.payment} credits. "
        f"Rating +{rating_gain}."
    )


def _check_steal_file(gs, mission):
    """Verify player has a copy of the target file on their gateway."""
    gw = Computer.query.filter_by(
        game_session_id=gs.id, ip=gs.gateway_ip
    ).first()
    if not gw:
        return False, "Gateway not found."

    copied = DataFile.query.filter_by(
        computer_id=gw.id, filename=mission.target_filename
    ).first()
    if not copied:
        return False, (
            f"File '{mission.target_filename}' not found on your gateway. "
            f"Use File Copier to download it from {mission.target_ip}."
        )
    return True, "File found."


def _check_destroy_file(gs, mission):
    """Verify the target file no longer exists on the target computer."""
    target_comp = Computer.query.filter_by(
        game_session_id=gs.id, ip=mission.target_ip
    ).first()
    if not target_comp:
        return False, "Target computer not found."

    still_exists = DataFile.query.filter_by(
        computer_id=target_comp.id, filename=mission.target_filename
    ).first()
    if still_exists:
        return False, (
            f"File '{mission.target_filename}' still exists on {mission.target_ip}. "
            f"Use File Deleter to remove it."
        )
    return True, "File destroyed."


def check_mission_expiry(game_session_id):
    """Expire old available missions. Called periodically from game loop."""
    gs = db.session.get(GameSession, game_session_id)
    if not gs:
        return

    expired_count = 0
    missions = Mission.query.filter_by(
        game_session_id=game_session_id, status=MISSION_AVAILABLE
    ).all()

    for m in missions:
        if gs.game_time_ticks - m.created_at_tick > 1500:
            m.status = MISSION_EXPIRED
            expired_count += 1

    if expired_count:
        db.session.commit()


def get_available_missions(game_session_id):
    """Get available missions for the BBS display."""
    return Mission.query.filter_by(
        game_session_id=game_session_id, status=MISSION_AVAILABLE
    ).all()


def get_accepted_missions(game_session_id):
    """Get player's accepted (in-progress) missions."""
    return Mission.query.filter_by(
        game_session_id=game_session_id, status=MISSION_ACCEPTED
    ).all()


def find_accepted_mission_for_email(game_session_id, email_obj):
    """Find the accepted mission that matches a given email (for reply-based completion)."""
    missions = Mission.query.filter_by(
        game_session_id=game_session_id, status=MISSION_ACCEPTED
    ).all()

    for m in missions:
        # Match by contact email address
        if m.contact == email_obj.from_addr:
            return m
        # Match by subject containing mission description
        if m.description in email_obj.subject:
            return m

    return None
