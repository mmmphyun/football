"""Pressure index and PPDA."""

from typing import Any

from .common import event_time

DEFENSIVE_TYPES = {"Pressure", "Tackle", "Interception", "Clearance", "Block"}


def compute_pressure(events: list[dict[str, Any]], team_ids_list: list[int]) -> dict[int, dict[str, Any]]:
    times = [event_time(ev) for ev in events]
    duration_min = ((max(times) - min(times)) / 60.0) if times else 1.0
    duration_min = max(duration_min, 1.0)

    stats: dict[int, dict[str, int]] = {}
    for team_id in team_ids_list:
        stats[team_id] = {"pressures": 0, "defensive_actions": 0, "opponent_passes": 0}

    for ev in events:
        team = ev.get("team", {}).get("id")
        if team is None or team not in stats:
            continue
        etype = ev.get("type", {}).get("name")
        if etype == "Pressure":
            stats[team]["pressures"] += 1
        if etype in DEFENSIVE_TYPES:
            stats[team]["defensive_actions"] += 1
        if etype == "Pass":
            for other in team_ids_list:
                if other != team:
                    stats[other]["opponent_passes"] += 1

    out: dict[int, dict[str, Any]] = {}
    for team_id in team_ids_list:
        s = stats[team_id]
        ppda = round(s["opponent_passes"] / s["defensive_actions"], 2) if s["defensive_actions"] else None
        out[team_id] = {
            "pressures": s["pressures"],
            "pressures_per_min": round(s["pressures"] / duration_min, 2),
            "defensive_actions": s["defensive_actions"],
            "opponent_passes": s["opponent_passes"],
            "ppda": ppda,
        }
    return out