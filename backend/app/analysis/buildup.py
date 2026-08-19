"""Buildup direction: progressive passes/carries and possession start thirds."""

from typing import Any

from .common import attack_direction, is_completed_pass

PASS_PROGRESS_THRESHOLD = 10.0
CARRY_PROGRESS_THRESHOLD = 5.0


def compute_buildup(events: list[dict[str, Any]], team_ids_list: list[int]) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    for team_id in team_ids_list:
        direction = attack_direction(events, team_id)
        progressive_passes = 0
        progressive_carries = 0
        net_progression = 0.0
        possession_starts: dict[int, int] = {}
        seen_possessions: set[int] = set()

        for ev in events:
            team = ev.get("team", {}).get("id")
            if team != team_id:
                continue
            etype = ev.get("type", {}).get("name")
            if etype == "Pass" and is_completed_pass(ev):
                start = ev.get("location")
                end = ev.get("pass", {}).get("end_location")
                if start and end:
                    progress = (end[0] - start[0]) * direction
                    if progress >= PASS_PROGRESS_THRESHOLD:
                        progressive_passes += 1
                        net_progression += progress
            elif etype == "Carry":
                start = ev.get("location")
                end = ev.get("carry", {}).get("end_location")
                if start and end:
                    progress = (end[0] - start[0]) * direction
                    if progress >= CARRY_PROGRESS_THRESHOLD:
                        progressive_carries += 1
                        net_progression += progress

            poss = ev.get("possession")
            if poss is not None and poss not in seen_possessions:
                seen_possessions.add(poss)
                loc = ev.get("location")
                if loc:
                    own_goal_x = 0.0 if direction == 1 else 120.0
                    rel = (loc[0] - own_goal_x) * direction
                    if rel < 40:
                        third = "defensive"
                    elif rel < 80:
                        third = "middle"
                    else:
                        third = "final"
                    possession_starts[third] = possession_starts.get(third, 0) + 1

        out[team_id] = {
            "progressive_passes": progressive_passes,
            "progressive_carries": progressive_carries,
            "net_progression": round(net_progression, 1),
            "thirds": {
                "defensive": possession_starts.get("defensive", 0),
                "middle": possession_starts.get("middle", 0),
                "final": possession_starts.get("final", 0),
            },
            "attack_direction": direction,
        }
    return out