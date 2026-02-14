"""Mission engine -- generates, accepts, checks, and completes missions."""
import json
import logging
import random

from app.extensions import db
from app.models.mission import Mission
from app.models.message import Message
from app.models.player import Player
from app.models.company import Company
from app.models.computer import Computer
from app.models.data_file import DataFile
from app.models.person import Person
from app.models.vlocation import VLocation
from app.game import constants as C
from app.game.name_generator import generate_name

log = logging.getLogger(__name__)

TYPE_STEALFILE = 1
TYPE_DESTROYFILE = 2
TYPE_FINDDATA = 3
TYPE_CHANGEDATA = 4

_PROB_TABLES = {
    TYPE_STEALFILE: C.PROB_MISSION_STEALFILE,
    TYPE_DESTROYFILE: C.PROB_MISSION_DESTROYFILE,
    TYPE_FINDDATA: C.PROB_MISSION_FINDDATA,
    TYPE_CHANGEDATA: C.PROB_MISSION_CHANGEDATA,
}

_BASE_PAYMENT = {
    TYPE_STEALFILE: C.PAYMENT_MISSION_STEALFILE,
    TYPE_DESTROYFILE: C.PAYMENT_MISSION_DESTROYFILE,
    TYPE_FINDDATA: C.PAYMENT_MISSION_FINDDATA,
    TYPE_CHANGEDATA: C.PAYMENT_MISSION_CHANGEDATA,
}

_MIN_DIFFICULTY = {
    TYPE_STEALFILE: C.MINDIFFICULTY_MISSION_STEALFILE,
    TYPE_DESTROYFILE: C.MINDIFFICULTY_MISSION_DESTROYFILE,
    TYPE_FINDDATA: C.MINDIFFICULTY_MISSION_FINDDATA,
    TYPE_CHANGEDATA: C.MINDIFFICULTY_MISSION_CHANGEDATA,
}

_STEAL_FILENAMES = [
    "accounts.dat", "personnel.db", "clients.dat", "finances.xls",
    "passwords.sys", "strategy.doc", "research.dat", "patents.db",
    "contracts.dat", "internal_memo.doc", "salary_data.xls",
    "project_plans.doc", "customer_list.db", "trade_secrets.dat",
]

_DESTROY_FILENAMES = [
    "evidence.log", "backup.dat", "audit_trail.log", "witness_report.doc",
    "transaction_log.dat", "security_footage.dat", "communications.log",
    "incriminating_data.dat", "surveillance.dat", "financial_records.db",
]

_FIND_DATA_TYPES = [
    "financial records", "employment history", "personal details",
    "medical records", "criminal record", "banking information",
]


def _select_mission_type(rng, player_rating):
    rating_index = max(0, min(16, player_rating))
    weights = [table[rating_index] for table in _PROB_TABLES.values()]
    types = list(_PROB_TABLES.keys())
    total = sum(weights)
    if total == 0:
        return rng.choice(types)
    return rng.choices(types, weights=weights, k=1)[0]


def _get_rating_level(score):
    level = 0
    for idx, (_, threshold) in enumerate(C.UPLINKRATING):
        if score >= threshold:
            level = idx
    return level


def generate_missions(session_id, count, player_rating=0, current_tick=0):
    """Generate count random missions for the given game session."""
    rng = random.Random()

    companies = Company.query.filter(
        Company.game_session_id == session_id,
        Company.name.notin_(["Government", "Uplink Corporation"]),
    ).all()
    if not companies:
        return []

    target_computers = Computer.query.filter(
        Computer.game_session_id == session_id,
        Computer.computer_type == 1,
    ).all()
    if not target_computers:
        return []

    people = Person.query.filter(
        Person.game_session_id == session_id,
        Person.is_agent == False,
    ).all()

    missions = []

    for _ in range(count):
        mission_type = _select_mission_type(rng, player_rating)
        employer = rng.choice(companies)
        target_computer = rng.choice(target_computers)

        base_payment = _BASE_PAYMENT[mission_type]
        variance = rng.uniform(-C.PAYMENT_MISSION_VARIANCE, C.PAYMENT_MISSION_VARIANCE)
        payment = int(base_payment * (1 + variance))

        min_diff = _MIN_DIFFICULTY[mission_type]
        difficulty = min_diff + rng.randint(0, C.DIFFICULTY_MISSION_VARIANCE)
        min_rating = max(0, min(16, difficulty // 2))

        if mission_type == TYPE_STEALFILE:
            filename = rng.choice(_STEAL_FILENAMES)
            description = f"Steal file '{filename}' from {target_computer.company_name} Internal Services Machine"
            target_data = {
                "target_filename": filename,
                "target_company": target_computer.company_name,
                "target_computer_id": target_computer.id,
            }
            db.session.add(DataFile(
                computer_id=target_computer.id,
                filename=filename,
                size=rng.randint(1, 4),
                file_type=2,
                data=f"Confidential: {filename}",
            ))

        elif mission_type == TYPE_DESTROYFILE:
            filename = rng.choice(_DESTROY_FILENAMES)
            description = f"Destroy all evidence: delete file '{filename}' from {target_computer.company_name} file server"
            target_data = {
                "target_filename": filename,
                "target_company": target_computer.company_name,
                "target_computer_id": target_computer.id,
            }
            db.session.add(DataFile(
                computer_id=target_computer.id,
                filename=filename,
                size=rng.randint(1, 4),
                file_type=2,
                data=f"Confidential data from {target_computer.company_name}",
            ))

        elif mission_type == TYPE_FINDDATA:
            person_name = generate_name(rng) if not people else rng.choice(people).name
            data_type = rng.choice(_FIND_DATA_TYPES)
            description = f"Find {data_type} for {person_name} - check {target_computer.company_name} records"
            target_data = {
                "target_person": person_name,
                "target_data_type": data_type,
                "target_company": target_computer.company_name,
                "target_computer_id": target_computer.id,
            }

        elif mission_type == TYPE_CHANGEDATA:
            person_name = generate_name(rng) if not people else rng.choice(people).name
            description = f"Change academic record for {person_name} at International Academic Database"
            target_data = {
                "target_person": person_name,
                "target_company": target_computer.company_name,
                "target_computer_id": target_computer.id,
            }
        else:
            continue

        mission = Mission(
            game_session_id=session_id,
            mission_type=mission_type,
            description=description,
            employer_name=employer.name,
            payment=payment,
            difficulty=difficulty,
            min_rating=min_rating,
            target_computer_ip=target_computer.ip,
            target_data=json.dumps(target_data),
            created_at_tick=current_tick,
            due_at_tick=current_tick + C.TIME_TOEXPIREMISSIONS,
        )
        db.session.add(mission)
        missions.append(mission)

    db.session.flush()
    return missions


def accept_mission(session_id, player_id, mission_id):
    mission = Mission.query.filter_by(id=mission_id, game_session_id=session_id).first()
    if mission is None:
        raise ValueError(f"Mission {mission_id} not found")
    if mission.is_accepted:
        raise ValueError(f"Mission {mission_id} is already accepted")

    mission.is_accepted = True
    mission.accepted_by = str(player_id)

    db.session.add(Message(
        game_session_id=session_id,
        player_id=player_id,
        from_name=mission.employer_name,
        subject=f"Mission Accepted: {mission.description[:80]}",
        body=(
            f"Agent,\n\nThank you for accepting this mission.\n\n"
            f"Objective: {mission.description}\n"
            f"Payment on completion: {mission.payment}c\n\n"
            f"- {mission.employer_name}"
        ),
    ))
    db.session.flush()
    return _mission_to_dict(mission)


def check_mission_completion(session_id, player_id, mission_id):
    mission = Mission.query.filter_by(id=mission_id, game_session_id=session_id).first()
    if mission is None:
        raise ValueError(f"Mission {mission_id} not found")
    if not mission.is_accepted or mission.accepted_by != str(player_id):
        raise ValueError(f"Mission {mission_id} is not accepted by this player")
    if mission.is_completed:
        return {"completed": True, "reason": "Mission already completed"}

    target_data = json.loads(mission.target_data or "{}")
    player = Player.query.get(player_id)
    gateway_computer_id = _get_gateway_computer_id(session_id, player)

    if mission.mission_type == TYPE_STEALFILE:
        target_filename = target_data.get("target_filename", "")
        if gateway_computer_id is None:
            return {"completed": False, "reason": "No gateway computer found"}
        file_on_gateway = DataFile.query.filter_by(
            computer_id=gateway_computer_id, filename=target_filename
        ).first()
        if file_on_gateway is not None:
            return {"completed": True, "reason": f"File '{target_filename}' found on gateway"}
        return {"completed": False, "reason": f"File '{target_filename}' not found on gateway"}

    elif mission.mission_type == TYPE_DESTROYFILE:
        target_filename = target_data.get("target_filename", "")
        target_computer_id = target_data.get("target_computer_id")
        if target_computer_id is None:
            return {"completed": False, "reason": "Target computer not specified"}
        file_on_target = DataFile.query.filter_by(
            computer_id=int(target_computer_id), filename=target_filename
        ).first()
        if file_on_target is None:
            return {"completed": True, "reason": f"File '{target_filename}' has been destroyed"}
        return {"completed": False, "reason": f"File '{target_filename}' still exists"}

    elif mission.mission_type == TYPE_FINDDATA:
        target_person = target_data.get("target_person", "")
        if gateway_computer_id is None:
            return {"completed": False, "reason": "No gateway computer found"}
        files = DataFile.query.filter_by(computer_id=gateway_computer_id).all()
        for f in files:
            if f.data and target_person in f.data:
                return {"completed": True, "reason": f"Data about '{target_person}' found"}
        return {"completed": False, "reason": f"No data about '{target_person}' found"}

    elif mission.mission_type == TYPE_CHANGEDATA:
        target_computer_id = target_data.get("target_computer_id")
        if target_computer_id is None:
            return {"completed": False, "reason": "Target computer not specified"}
        from app.models.access_log import AccessLog
        player_log = AccessLog.query.filter_by(
            computer_id=int(target_computer_id),
            from_ip=player.localhost_ip or "127.0.0.1",
        ).first()
        if player_log is not None:
            return {"completed": True, "reason": "Record has been modified"}
        return {"completed": False, "reason": "Records have not been changed"}

    return {"completed": False, "reason": "Unknown mission type"}


def complete_mission(session_id, player_id, mission_id):
    mission = Mission.query.filter_by(id=mission_id, game_session_id=session_id).first()
    if mission is None:
        raise ValueError(f"Mission {mission_id} not found")
    if mission.is_completed:
        raise ValueError(f"Mission {mission_id} is already completed")

    mission.is_completed = True
    player = Player.query.get(player_id)
    player.balance += mission.payment
    player.uplink_rating += mission.difficulty

    mission_type_index = mission.mission_type
    if 0 <= mission_type_index < len(C.NEUROMANCERCHANGE):
        player.neuromancer_rating += C.NEUROMANCERCHANGE[mission_type_index]

    rating_level = _get_rating_level(player.uplink_rating)

    db.session.add(Message(
        game_session_id=session_id,
        player_id=player_id,
        from_name=mission.employer_name,
        subject=f"Payment: {mission.payment}c credited",
        body=(
            f"Agent,\n\nMission completed successfully.\n\n"
            f"Payment of {mission.payment}c has been credited to your account.\n"
            f"Your current balance is {player.balance}c.\n\n"
            f"- {mission.employer_name}"
        ),
    ))
    db.session.flush()

    return {
        "balance": player.balance,
        "uplink_rating": player.uplink_rating,
        "uplink_rating_level": rating_level,
        "uplink_rating_name": C.UPLINKRATING[rating_level][0],
        "neuromancer_rating": player.neuromancer_rating,
        "mission_payment": mission.payment,
    }


def get_available_missions(session_id, player_rating=0):
    rating_level = _get_rating_level(player_rating)
    missions = Mission.query.filter(
        Mission.game_session_id == session_id,
        Mission.is_accepted == False,
        Mission.is_completed == False,
        Mission.min_rating <= rating_level,
    ).order_by(Mission.payment.desc()).all()
    return [_mission_to_dict(m) for m in missions]


def _mission_to_dict(mission):
    return {
        "id": mission.id,
        "mission_type": mission.mission_type,
        "description": mission.description,
        "employer_name": mission.employer_name,
        "payment": mission.payment,
        "difficulty": mission.difficulty,
        "min_rating": mission.min_rating,
        "target_computer_ip": mission.target_computer_ip,
        "is_accepted": mission.is_accepted,
        "is_completed": mission.is_completed,
    }


def _get_gateway_computer_id(session_id, player):
    if player.localhost_ip is None:
        return None
    gateway_loc = VLocation.query.filter_by(
        game_session_id=session_id, ip=player.localhost_ip
    ).first()
    if gateway_loc is None:
        return None
    return gateway_loc.computer_id
