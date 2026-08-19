"""Shared helpers for the analysis engine."""

from typing import Any, Optional

from .. import config


def event_time(ev: dict[str, Any]) -> float:
    """Absolute seconds, with a large offset per period so extra time is ordered."""
    period = ev.get("period", 1)
    minute = ev.get("minute", 0)
    second = ev.get("second", 0)
    return (period - 1) * 3600 + minute * 60 + second


def team_ids(events: list[dict[str, Any]]) -> list[int]:
    ids: list[int] = []
    for ev in events:
        tid = ev.get("team", {}).get("id")
        if tid is not None and tid not in ids:
            ids.append(tid)
    return ids


def opponent_of(team_id: int, team_ids_list: list[int]) -> Optional[int]:
    for tid in team_ids_list:
        if tid != team_id:
            return tid
    return None


def attack_direction(events: list[dict[str, Any]], team_id: int) -> int:
    """+1 if the team attacks toward x=120, -1 toward x=0 (inferred from shots)."""
    xs = [
        ev["location"][0]
        for ev in events
        if ev.get("type", {}).get("name") == "Shot"
        and ev.get("team", {}).get("id") == team_id
        and ev.get("location")
    ]
    if not xs:
        return 1
    return 1 if sum(xs) / len(xs) > config.PITCH_W / 2 else -1


def is_completed_pass(ev: dict[str, Any]) -> bool:
    if ev.get("type", {}).get("name") != "Pass":
        return False
    outcome = ev.get("pass", {}).get("outcome", {}).get("name")
    return outcome in (None, "Complete", "Injury Clearance")


def build_lineup_maps(lineups: list[dict[str, Any]]) -> dict[int, dict[int, dict[str, Any]]]:
    """lineups -> {team_id: {player_id: {name, number, position, gk}}}"""
    maps: dict[int, dict[int, dict[str, Any]]] = {}
    for team in lineups or []:
        tid = team.get("team_id")
        if tid is None:
            continue
        team_map: dict[int, dict[str, Any]] = {}
        for p in team.get("lineup", []):
            positions = p.get("positions") or []
            position = positions[-1].get("position") if positions else p.get("position", "Unknown")
            team_map[p["player_id"]] = {
                "name": p.get("player_name", f"P{p['player_id']}"),
                "number": p.get("jersey_number"),
                "position": position or "Unknown",
                "gk": (position or "").lower() == "goalkeeper",
            }
        maps[tid] = team_map
    return maps