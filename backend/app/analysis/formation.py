"""포메이션 및 선수별 평균 위치 분석 모듈.

볼 소유(In-Possession) 및 미소유(Out-of-Possession) 상태에서 선수별 평균 위치,
포메이션 앵커 좌표 및 팀 전술 컴팩트니스 지표를 산출합니다.
"""

from collections import defaultdict
from typing import Any

from app.analysis.common import build_lineup_maps

# StatsBomb 포지션 ID 기준 기본 앵커 좌표 (x: 0~120, y: 0~80)
POSITION_ANCHORS: dict[int, tuple[float, float]] = {
    1: (6.0, 40.0),  # Goalkeeper
    2: (25.0, 70.0),  # Right Back
    3: (25.0, 50.0),  # Right Center Back
    4: (25.0, 40.0),  # Center Back
    5: (25.0, 30.0),  # Left Center Back
    6: (25.0, 10.0),  # Left Back
    7: (45.0, 70.0),  # Right Wing Back
    8: (45.0, 10.0),  # Left Wing Back
    9: (50.0, 40.0),  # Right Defensive Midfield
    10: (50.0, 40.0),  # Center Defensive Midfield
    11: (50.0, 40.0),  # Left Defensive Midfield
    12: (65.0, 70.0),  # Right Midfield
    13: (65.0, 50.0),  # Right Center Midfield
    14: (65.0, 40.0),  # Center Midfield
    15: (65.0, 30.0),  # Left Center Midfield
    16: (65.0, 10.0),  # Left Midfield
    17: (80.0, 70.0),  # Right Wing
    18: (80.0, 50.0),  # Right Attacking Midfield
    19: (80.0, 40.0),  # Center Attacking Midfield
    20: (80.0, 30.0),  # Left Attacking Midfield
    21: (80.0, 10.0),  # Left Wing
    22: (95.0, 50.0),  # Right Center Forward
    23: (100.0, 40.0),  # Center Forward
    24: (95.0, 30.0),  # Left Center Forward
    25: (90.0, 40.0),  # Secondary Striker
}


def get_position_anchor(position_id: int | None) -> tuple[float, float]:
    """포지션 ID에 대응하는 표준 앵커 좌표를 반환합니다."""
    if position_id is not None and position_id in POSITION_ANCHORS:
        return POSITION_ANCHORS[position_id]
    return (60.0, 40.0)


def compute_formation_summary(
    events: list[dict[str, Any]],
    lineups: list[dict[str, Any]],
    team_id: int,
) -> dict[str, Any]:
    """팀의 포메이션, 볼 소유/미소유별 선수 평균 위치 및 컴팩트니스 지표를 산출합니다."""
    lineup_maps = build_lineup_maps(lineups)
    team_meta = lineup_maps.get(team_id, {"players": {}, "starting_xi": []})
    players_meta = team_meta.get("players", {})
    starting_xi = set(team_meta.get("starting_xi", []))

    # 시작 포메이션 이름 추출 (Starting XI 이벤트 탐색)
    formation_name = "Unknown"
    for ev in events:
        if (
            ev.get("type", {}).get("name") == "Starting XI"
            and ev.get("team", {}).get("id") == team_id
        ):
            tactics = ev.get("tactics", {})
            formation_num = tactics.get("formation")
            if formation_num:
                formation_name = str(formation_num)
            break

    # 볼 소유/미소유별 위치 데이터 수집
    possession_locations: dict[int, list[tuple[float, float]]] = defaultdict(list)
    out_of_possession_locations: dict[int, list[tuple[float, float]]] = defaultdict(list)
    all_locations: dict[int, list[tuple[float, float]]] = defaultdict(list)

    for ev in events:
        player_info = ev.get("player")
        if not player_info:
            continue

        p_id = player_info.get("id")
        if p_id is None or p_id not in players_meta:
            continue

        loc = ev.get("location")
        if not loc or len(loc) < 2:
            continue

        x, y = float(loc[0]), float(loc[1])
        all_locations[p_id].append((x, y))

        poss_team_id = ev.get("possession_team", {}).get("id")
        if poss_team_id == team_id:
            possession_locations[p_id].append((x, y))
        else:
            out_of_possession_locations[p_id].append((x, y))

    def _calc_player_avg(
        loc_map: dict[int, list[tuple[float, float]]],
    ) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for p_id, p_info in players_meta.items():
            locs = loc_map.get(p_id, [])
            count = len(locs)
            anchor = get_position_anchor(p_info.get("primary_position_id"))

            if count > 0:
                avg_x = sum(x for x, _ in locs) / count
                avg_y = sum(y for _, y in locs) / count
            else:
                avg_x, avg_y = anchor

            result.append(
                {
                    "player_id": p_id,
                    "player_name": p_info.get("player_name"),
                    "jersey_number": p_info.get("jersey_number"),
                    "position": p_info.get("primary_position"),
                    "position_id": p_info.get("primary_position_id"),
                    "is_starter": p_id in starting_xi,
                    "event_count": count,
                    "x": round(avg_x, 2),
                    "y": round(avg_y, 2),
                    "anchor_x": anchor[0],
                    "anchor_y": anchor[1],
                }
            )
        return result

    players_overall = _calc_player_avg(all_locations)
    players_in_poss = _calc_player_avg(possession_locations)
    players_out_poss = _calc_player_avg(out_of_possession_locations)

    # 선발 선수 기준 평균 너비 및 길이 산출 (컴팩트니스)
    starter_locs = [
        (p["x"], p["y"])
        for p in players_overall
        if p["is_starter"] and p.get("position_id") != 1  # GK 제외
    ]

    if len(starter_locs) >= 4:
        xs = [pt[0] for pt in starter_locs]
        ys = [pt[1] for pt in starter_locs]
        team_length = round(max(xs) - min(xs), 2)
        team_width = round(max(ys) - min(ys), 2)
        team_center_x = round(sum(xs) / len(xs), 2)
        team_center_y = round(sum(ys) / len(ys), 2)
    else:
        team_length = 35.0
        team_width = 45.0
        team_center_x = 55.0
        team_center_y = 40.0

    # 선발 11명 및 교체 출전 선수 분리
    starters = [p for p in players_overall if p["is_starter"]]
    substitutes = [p for p in players_overall if not p["is_starter"] and p["event_count"] > 0]
    all_played = starters + substitutes

    return {
        "team_id": team_id,
        "formation": formation_name,
        "formation_name": formation_name,
        "team_length": team_length,
        "team_width": team_width,
        "team_center_x": team_center_x,
        "team_center_y": team_center_y,
        "players": starters if starters else players_overall,
        "starters": starters,
        "substitutes": substitutes,
        "all_played_players": all_played,
        "players_overall": players_overall,
        "players_in_possession": players_in_poss,
        "players_out_of_possession": players_out_poss,
    }
