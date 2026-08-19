"""Grid zone occupancy per team and possession state."""

from typing import Any

from .. import config
from .common import opponent_of


def compute_zones(
    events: list[dict[str, Any]],
    three_sixty: list[dict[str, Any]] | None,
    has_360: bool,
    team_ids_list: list[int],
    cols: int = 12,
    rows: int = 8,
) -> dict[str, Any]:
    counts: dict[tuple[int, str, int, int], int] = {}
    totals: dict[tuple[int, str], int] = {}

    def cell_of(x: float, y: float) -> tuple[int, int]:
        col = min(cols - 1, max(0, int(x * cols / config.PITCH_W)))
        row = min(rows - 1, max(0, int(y * rows / config.PITCH_H)))
        return col, row

    def add(team_id: int, state: str, loc: list[float]) -> None:
        col, row = cell_of(loc[0], loc[1])
        key = (team_id, state, col, row)
        counts[key] = counts.get(key, 0) + 1
        tkey = (team_id, state)
        totals[tkey] = totals.get(tkey, 0) + 1

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
                add(team, state, loc)
    else:
        for ev in events:
            team = ev.get("team", {}).get("id")
            if team is None or not ev.get("location"):
                continue
            poss_team = ev.get("possession_team", {}).get("id", team)
            state = "possession" if team == poss_team else "out_of_possession"
            add(team, state, ev["location"])
            etype = ev.get("type", {}).get("name")
            if etype == "Pass":
                recipient = ev.get("pass", {}).get("recipient", {}).get("id")
                end_loc = ev.get("pass", {}).get("end_location")
                outcome = ev.get("pass", {}).get("outcome", {}).get("name")
                if recipient is not None and end_loc and outcome in (None, "Complete", "Injury Clearance"):
                    add(team, state, end_loc)
            elif etype == "Carry":
                end_loc = ev.get("carry", {}).get("end_location")
                if end_loc:
                    add(team, state, end_loc)

    cells = []
    for col in range(cols):
        for row in range(rows):
            values: dict[int, dict[str, float]] = {}
            for team_id in team_ids_list:
                values[team_id] = {
                    "possession": _norm(counts.get((team_id, "possession", col, row), 0), totals.get((team_id, "possession"), 0)),
                    "out_of_possession": _norm(counts.get((team_id, "out_of_possession", col, row), 0), totals.get((team_id, "out_of_possession"), 0)),
                }
            cells.append({"col": col, "row": row, "values": values})
    return {"cols": cols, "rows": rows, "cells": cells}


def _norm(count: int, total: int) -> float:
    return round(count / total, 5) if total else 0.0