"""Counter-attack transitions: ball recovery to shot / final-third entry."""

from typing import Any

from .. import config
from .common import attack_direction, event_time


def compute_transitions(events: list[dict[str, Any]], team_ids_list: list[int]) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    for team_id in team_ids_list:
        direction = attack_direction(events, team_id)
        own_goal_x = 0.0 if direction == 1 else 120.0
        count = 0
        total_seconds = 0.0
        for i, ev in enumerate(events):
            if ev.get("type", {}).get("name") != "Ball Recovery":
                continue
            if ev.get("team", {}).get("id") != team_id:
                continue
            t0 = event_time(ev)
            for j in range(i + 1, min(len(events), i + 1 + config.TRANSITION_MAX_EVENTS)):
                ej = events[j]
                dt = event_time(ej) - t0
                if dt > config.TRANSITION_WINDOW_SECONDS:
                    break
                if ej.get("team", {}).get("id") != team_id:
                    continue
                etype = ej.get("type", {}).get("name")
                reached = False
                if etype == "Shot":
                    reached = True
                elif etype in ("Pass", "Carry"):
                    loc = ej.get("pass", {}).get("end_location") or ej.get("carry", {}).get("end_location") or ej.get("location")
                    if loc and (loc[0] - own_goal_x) * direction >= 80:
                        reached = True
                if reached:
                    count += 1
                    total_seconds += dt
                    break
        out[team_id] = {
            "count": count,
            "avg_seconds": round(total_seconds / count, 2) if count else None,
        }
    return out