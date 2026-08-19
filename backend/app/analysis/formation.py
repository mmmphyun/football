"""Average player positions per possession state (formation)."""

from typing import Any

from .common import build_lineup_maps, is_completed_pass, opponent_of

STATES = ("possession", "out_of_possession")


def compute_formation(
    events: list[dict[str, Any]],
    lineup_maps: dict[int, dict[int, dict[str, Any]]],
    three_sixty: list[dict[str, Any]] | None,
    has_360: bool,
    team_ids_list: list[int],
) -> dict[int, dict[str, Any]]:
    sums: dict[int, dict[str, dict[int, list[float]]]] = {}

    def acc(team_id: int, state: str, player_id: int, loc: list[float]) -> None:
        entry = sums.setdefault(team_id, {}).setdefault(state, {}).setdefault(player_id, [0.0, 0.0, 0])
        entry[0] += loc[0]
        entry[1] += loc[1]
        entry[2] += 1

    if has_360:
        for ev in events:
            ff = ev.get("freeze_frame")
            if not ff:
                continue
            ev_team = ev.get("team", {}).get("id")
            poss_team = ev.get("possession_team", {}).get("id", ev_team)
            for p in ff:
                pid = p.get("player", {}).get("id")
                loc = p.get("location")
                if pid is None or not loc:
                    continue
                team = ev_team if p.get("teammate") else opponent_of(ev_team, team_ids_list)
                if team is None:
                    continue
                state = "possession" if team == poss_team else "out_of_possession"
                acc(team, state, pid, loc)
    else:
        for ev in events:
            team = ev.get("team", {}).get("id")
            if team is None:
                continue
            poss_team = ev.get("possession_team", {}).get("id", team)
            state = "possession" if team == poss_team else "out_of_possession"
            pid = ev.get("player", {}).get("id")
            loc = ev.get("location")
            if pid is not None and loc:
                acc(team, state, pid, loc)
            etype = ev.get("type", {}).get("name")
            if etype == "Pass" and is_completed_pass(ev):
                recipient = ev.get("pass", {}).get("recipient", {}).get("id")
                end_loc = ev.get("pass", {}).get("end_location")
                if recipient is not None and end_loc:
                    acc(team, state, recipient, end_loc)
            elif etype == "Carry":
                pid = ev.get("player", {}).get("id")
                end_loc = ev.get("carry", {}).get("end_location")
                if pid is not None and end_loc:
                    acc(team, state, pid, end_loc)

    out: dict[int, dict[str, Any]] = {}
    for team_id in team_ids_list:
        team_map = lineup_maps.get(team_id, {})
        team_out: dict[str, Any] = {}
        for state in STATES:
            entries = []
            for pid, (sx, sy, n) in sums.get(team_id, {}).get(state, {}).items():
                info = team_map.get(pid, {"name": f"P{pid}", "number": None, "position": "Unknown", "gk": False})
                entries.append(
                    {
                        "player_id": pid,
                        "name": info["name"],
                        "number": info["number"],
                        "position": info["position"],
                        "gk": info["gk"],
                        "x": round(sx / n, 1),
                        "y": round(sy / n, 1),
                        "frames": n,
                    }
                )
            entries.sort(key=lambda e: -e["frames"])
            team_out[state] = entries
        out[team_id] = team_out
    return out