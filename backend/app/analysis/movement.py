"""Player movement summaries from 360 freeze frames (360-only)."""

import math
from typing import Any

from .. import config
from .common import event_time, opponent_of


def compute_movement(
    events: list[dict[str, Any]],
    three_sixty: list[dict[str, Any]] | None,
    has_360: bool,
    lineup_maps: dict[int, dict[int, dict[str, Any]]],
    team_ids_list: list[int],
) -> dict[str, Any]:
    if not has_360:
        return {"available": False}

    seq: dict[int, list[tuple[float, float, float]]] = {}
    player_team: dict[int, int] = {}
    for ev in events:
        ff = ev.get("freeze_frame")
        if not ff:
            continue
        t = event_time(ev)
        ev_team = ev.get("team", {}).get("id")
        for p in ff:
            pid = p.get("player", {}).get("id")
            loc = p.get("location")
            if pid is None or not loc:
                continue
            seq.setdefault(pid, []).append((t, loc[0], loc[1]))
            player_team[pid] = ev_team if p.get("teammate") else opponent_of(ev_team, team_ids_list)

    players: list[dict[str, Any]] = []
    for pid, pts in seq.items():
        pts.sort(key=lambda x: x[0])
        speeds: list[float] = []
        disp_x = disp_y = 0.0
        for (t1, x1, y1), (t2, x2, y2) in zip(pts, pts[1:]):
            dt = t2 - t1
            if dt <= 0:
                continue
            vx, vy = (x2 - x1) / dt, (y2 - y1) / dt
            speeds.append(math.hypot(vx, vy))
            disp_x += x2 - x1
            disp_y += y2 - y1
        avg = sum(speeds) / len(speeds) if speeds else 0.0
        sprints = sum(1 for s in speeds if s > config.SPRINT_SPEED)
        mag = math.hypot(disp_x, disp_y)
        vector = {"x": round(disp_x / mag, 3), "y": round(disp_y / mag, 3)} if mag > 1e-6 else {"x": 0.0, "y": 0.0}
        team = player_team.get(pid)
        info = lineup_maps.get(team or -1, {}).get(pid, {"name": f"P{pid}", "position": "Unknown"})
        players.append(
            {
                "player_id": pid,
                "name": info["name"],
                "position": info["position"],
                "team_id": team,
                "avg_speed": round(avg, 2),
                "sprint_count": sprints,
                "vector": vector,
                "frames": len(pts),
            }
        )

    teams: dict[int, dict[str, Any]] = {}
    for team_id in team_ids_list:
        team_players = [p for p in players if p["team_id"] == team_id]
        if not team_players:
            continue
        avg_speed = sum(p["avg_speed"] for p in team_players) / len(team_players)
        sprints = sum(p["sprint_count"] for p in team_players)
        vx = sum(p["vector"]["x"] for p in team_players)
        vy = sum(p["vector"]["y"] for p in team_players)
        mag = math.hypot(vx, vy)
        teams[team_id] = {
            "avg_speed": round(avg_speed, 2),
            "sprint_count": sprints,
            "vector": {"x": round(vx / mag, 3), "y": round(vy / mag, 3)} if mag > 1e-6 else {"x": 0.0, "y": 0.0},
            "players": len(team_players),
        }
    return {"available": True, "players": players, "teams": teams}