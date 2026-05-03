"""
Build sync payloads from live CTFd data.
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Payload builders
# ---------------------------------------------------------------------------


def build_full_payload() -> dict:
    """
    Build a complete payload from all current CTFd data.

    Returns a dict ready to POST to the CTFProfile ctfd-sync endpoint.
    Pulls from CTFd's SQLAlchemy models at call-time so it always reflects the
    current database state.
    """
    from CTFd.models import Challenges, Teams, Users, Solves  # type: ignore

    challenges = []
    for ch in Challenges.query.all():
        challenges.append({
            "id": ch.id,
            "name": ch.name,
            "category": ch.category or "",
            "description": ch.description or "",
            "value": ch.value,
        })

    users = []
    for u in Users.query.filter_by(banned=False, hidden=False).all():
        entry: dict[str, Any] = {
            "id": u.id,
            "name": u.name,
        }
        ctfprofile_id = _get_ctfprofile_id(u)
        if ctfprofile_id:
            entry["ctfprofile_id"] = ctfprofile_id
        users.append(entry)

    teams = []
    try:
        for t in Teams.query.filter_by(banned=False, hidden=False).all():
            teams.append({
                "id": t.id,
                "name": t.name,
            })
    except Exception:
        # CTFd may be running in user-mode (no teams table)
        pass

    solves = []
    for s in Solves.query.all():
        entry = {
            "id": s.id,
            "challenge_id": s.challenge_id,
            "user_id": s.account_id,
            "date": s.date.isoformat() if s.date else None,
            "type": "correct",
        }
        # In team mode the solve belongs to a team; expose both ids
        if hasattr(s, "team_id"):
            entry["team_id"] = s.team_id
        solves.append(entry)

    standings: list[dict] = []
    try:
        standings = _build_standings()
    except Exception:
        pass

    return {
        "challenges": challenges,
        "users": users,
        "teams": teams,
        "solves": solves,
        "standings": standings,
    }


def build_solve_payload(solve) -> dict:
    """
    Build a minimal payload for a *single* new solve event.

    ``solve`` is the SQLAlchemy Solves instance passed by the after_insert
    event listener.
    """
    from CTFd.models import Challenges, Users  # type: ignore

    ch = Challenges.query.get(solve.challenge_id)
    u = Users.query.get(solve.account_id)

    entry: dict[str, Any] = {
        "id": solve.id,
        "challenge_id": solve.challenge_id,
        "user_id": solve.account_id,
        "date": solve.date.isoformat() if solve.date else None,
        "type": "correct",
    }
    if hasattr(solve, "team_id") and solve.team_id:
        entry["team_id"] = solve.team_id

    payload: dict[str, Any] = {
        "challenges": [],
        "users": [],
        "teams": [],
        "solves": [entry],
        "standings": [],
    }

    if ch:
        payload["challenges"].append({
            "id": ch.id,
            "name": ch.name,
            "category": ch.category or "",
            "value": ch.value,
        })

    if u:
        user_entry: dict[str, Any] = {"id": u.id, "name": u.name}
        ctfprofile_id = _get_ctfprofile_id(u)
        if ctfprofile_id:
            user_entry["ctfprofile_id"] = ctfprofile_id
        payload["users"].append(user_entry)

    # Include team info if solve is team-based
    if hasattr(solve, "team_id") and solve.team_id:
        try:
            from CTFd.models import Teams  # type: ignore
            t = Teams.query.get(solve.team_id)
            if t:
                payload["teams"].append({"id": t.id, "name": t.name})
        except Exception:
            pass

    return payload


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_ctfprofile_id(user) -> str:
    """
    Read the value of the 'CTFProfile ID' custom user field for *user*.

    CTFd stores custom profile fields in UserFieldEntries, not as direct
    model attributes — so we query the table explicitly.  Returns an empty
    string if the field doesn't exist or the user hasn't filled it in.
    """
    try:
        from CTFd.models import UserFields, UserFieldEntries  # type: ignore
        field = UserFields.query.filter_by(name="CTFProfile ID").first()
        if not field:
            return ""
        entry = UserFieldEntries.query.filter_by(
            field_id=field.id,
            user_id=user.id,
        ).first()
        return (entry.value or "").strip() if entry else ""
    except Exception:
        return ""


def _build_standings() -> list[dict]:
    """Return current score standings from CTFd's scoreboard cache."""
    try:
        from CTFd.utils.scores import get_standings  # type: ignore
        raw = get_standings()
        return [
            {
                "pos": i + 1,
                "account_id": entry.account_id,
                "name": entry.name,
                "score": entry.score,
            }
            for i, entry in enumerate(raw)
        ]
    except Exception:
        return []
