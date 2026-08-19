"""Pass network: nodes (players), edges (completed passes), forward progression."""

from typing import Any

from .common import is_completed_pass

TOP_EDGES = 15


def compute_pass_network(
    events: list[dict[str, Any]],
    lineup_maps: dict[int, dict[int, dict[str, Any]]],
    team_ids_list: list[int],
) -> dict[int, dict[str, Any]]:
    edges: dict[tuple[int, int, int], int] = {}
    touches: dict[int, dict[int, int]] = {}
    progression: dict[int, float] = {}
    total_passes: dict[int, int] = {}

    for ev in events:
        if not is_completed_pass(ev):
            continue
        team = ev.get("team", {}).get("id")
        passer = ev.get("player", {}).get("id")
        recipient = ev.get("pass", {}).get("recipient", {}).get("id")
        if team is None or passer is None or recipient is None:
            continue
        key = (team, passer, recipient)
        edges[key] = edges.get(key, 0) + 1
        touches.setdefault(team, {})
        touches[team][passer] = touches[team].get(passer, 0) + 1
        touches[team][recipient] = touches[team].get(recipient, 0) + 1
        total_passes[team] = total_passes.get(team, 0) + 1
        start = ev.get("location")
        end = ev.get("pass", {}).get("end_location")
        if start and end:
            progression[team] = progression.get(team, 0.0) + (end[0] - start[0])

    out: dict[int, dict[str, Any]] = {}
    for team_id in team_ids_list:
        team_map = lineup_maps.get(team_id, {})
        nodes = [
            {
                "player_id": pid,
                "name": team_map.get(pid, {}).get("name", f"P{pid}"),
                "position": team_map.get(pid, {}).get("position", "Unknown"),
                "touches": count,
            }
            for pid, count in touches.get(team_id, {}).items()
        ]
        nodes.sort(key=lambda n: -n["touches"])
        team_edges = [
            {"from": f, "to": t, "count": c}
            for (team, f, t), c in edges.items()
            if team == team_id
        ]
        team_edges.sort(key=lambda e: -e["count"])
        total = total_passes.get(team_id, 0)
        out[team_id] = {
            "nodes": nodes,
            "edges": team_edges[:TOP_EDGES],
            "progression": round(progression.get(team_id, 0.0) / total, 2) if total else 0.0,
            "total_passes": total,
        }
    return out