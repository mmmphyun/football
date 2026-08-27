"""포메이션 및 선수별 평균 위치 분석 모듈.

볼 소유(In-Possession) 및 미소유(Out-of-Possession) 상태에서 선수별 평균 위치,
포메이션 앵커 좌표 및 팀 전술 컴팩트니스 지표를 산출합니다.
"""

from collections import defaultdict
from typing import Any

from app.analysis.common import build_lineup_maps
from app.config import HALF_PITCH_X

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

DEFENDER_POSITION_IDS = {2, 3, 4, 5, 6, 7, 8}
MIDFIELDER_POSITION_IDS = {9, 10, 11, 12, 13, 14, 15, 16, 18, 19, 20}
FORWARD_POSITION_IDS = {17, 21, 22, 23, 24, 25}


def get_position_anchor(position_id: int | None) -> tuple[float, float]:
    """포지션 ID에 대응하는 표준 앵커 좌표를 반환합니다."""
    if position_id is not None and position_id in POSITION_ANCHORS:
        return POSITION_ANCHORS[position_id]
    return (60.0, 40.0)


def _infer_shape_string(players_list: list[dict[str, Any]]) -> str:
    """선수들의 x 좌표 분포를 기반으로 3~4선 포메이션 문자열(예: 4-4-2, 3-2-4-1 등)을 추론합니다."""
    field_players = [p for p in players_list if p.get("position_id") != 1 and p.get("is_starter")]
    if len(field_players) < 8:
        field_players = [p for p in players_list if p.get("position_id") != 1][:10]

    if not field_players:
        return "4-3-3"

    sorted_p = sorted(field_players, key=lambda p: p["x"])
    # X 좌표 간격 기반 라인 군집화
    lines: list[list[dict[str, Any]]] = []
    current_line = [sorted_p[0]]

    for p in sorted_p[1:]:
        if p["x"] - current_line[-1]["x"] > 12.0:
            lines.append(current_line)
            current_line = [p]
        else:
            current_line.append(p)
    lines.append(current_line)

    line_counts = [len(line) for line in lines]
    if sum(line_counts) == len(field_players) and len(line_counts) in (3, 4, 5):
        return "-".join(str(c) for c in line_counts)
    return "4-3-3"


def compute_formation_summary(
    events: list[dict[str, Any]],
    lineups: list[dict[str, Any]],
    team_id: int,
) -> dict[str, Any]:
    """팀의 3대 국면(수비/빌드업/공격)별 대형, 선수 평균 위치 및 컴팩트니스 지표를 산출합니다."""
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

    # 3대 국면별 위치 데이터 수집 버킷
    defensive_locations: dict[int, list[tuple[float, float]]] = defaultdict(list)
    buildup_locations: dict[int, list[tuple[float, float]]] = defaultdict(list)
    attacking_locations: dict[int, list[tuple[float, float]]] = defaultdict(list)
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
        type_name = ev.get("type", {}).get("name", "")

        # 1. 수비 국면: 상대팀 소유 또는 우리팀 수비 액션
        if poss_team_id != team_id or type_name in {
            "Pressure",
            "Tackle",
            "Interception",
            "Block",
            "Clearance",
            "Duel",
            "Foul Committed",
        }:
            defensive_locations[p_id].append((x, y))
        else:
            # 2 & 3. 우리팀 볼 소유
            if x < HALF_PITCH_X:
                buildup_locations[p_id].append((x, y))
            else:
                attacking_locations[p_id].append((x, y))

    def _calc_player_metrics(
        loc_map: dict[int, list[tuple[float, float]]],
        default_x_shift: float = 0.0,
    ) -> tuple[list[dict[str, Any]], float, float, float]:
        """선수별 평균 좌표, 라인 높이, 너비, 길이를 산출합니다."""
        result: list[dict[str, Any]] = []
        for p_id, p_info in players_meta.items():
            locs = loc_map.get(p_id, [])
            count = len(locs)
            anchor = get_position_anchor(p_info.get("primary_position_id"))

            if count > 0:
                avg_x = sum(pt[0] for pt in locs) / count
                avg_y = sum(pt[1] for pt in locs) / count
            else:
                # 데이터가 없는 경우 앵커 좌표에 오프셋 적용
                avg_x = max(2.0, min(118.0, anchor[0] + default_x_shift))
                avg_y = anchor[1]

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

        # 필드 플레이어(GK 제외) 선발 선수들 위치 기준 지표 산출
        field_starters = [
            p for p in result if p["is_starter"] and p.get("position_id") != 1
        ]
        if not field_starters:
            field_starters = [p for p in result if p.get("position_id") != 1][:10]

        if field_starters:
            xs = [p["x"] for p in field_starters]
            ys = [p["y"] for p in field_starters]
            length = round(max(xs) - min(xs), 2)
            width = round(max(ys) - min(ys), 2)

            # 수비 라인 높이: 수비수 포지션 선수들의 평균 x, 없으면 하위 30% x 평균
            defenders = [p for p in field_starters if p.get("position_id") in DEFENDER_POSITION_IDS]
            if defenders:
                line_height = round(sum(p["x"] for p in defenders) / len(defenders), 2)
            else:
                sorted_xs = sorted(xs)
                line_height = round(sum(sorted_xs[:3]) / min(3, len(sorted_xs)), 2)
        else:
            length = 35.0
            width = 45.0
            line_height = 35.0

        return result, line_height, width, length

    # 3대 국면 계산
    def_players, def_line, def_w, def_l = _calc_player_metrics(defensive_locations, default_x_shift=-10.0)
    bld_players, bld_line, bld_w, bld_l = _calc_player_metrics(buildup_locations, default_x_shift=0.0)
    att_players, att_line, att_w, att_l = _calc_player_metrics(attacking_locations, default_x_shift=15.0)

    # 전반적 지표 계산
    overall_players, overall_line, overall_w, overall_l = _calc_player_metrics(all_locations)

    starters = [p for p in overall_players if p["is_starter"]]
    substitutes = [p for p in overall_players if not p["is_starter"] and p["event_count"] > 0]
    all_played = starters + substitutes

    def_shape = _infer_shape_string(def_players)
    bld_shape = _infer_shape_string(bld_players)
    att_shape = _infer_shape_string(att_players)

    return {
        "team_id": team_id,
        "formation": formation_name,
        "formation_name": formation_name,
        "team_length": overall_l,
        "team_width": overall_w,
        "team_center_x": round(sum(p["x"] for p in (starters or overall_players)) / len(starters or overall_players), 2),
        "team_center_y": round(sum(p["y"] for p in (starters or overall_players)) / len(starters or overall_players), 2),
        "defensive": {
            "formation": def_shape,
            "line_height": def_line,
            "width": def_w,
            "length": def_l,
            "players": [p for p in def_players if p["is_starter"]] or def_players[:11],
            "all_players": def_players,
        },
        "buildup": {
            "formation": bld_shape,
            "line_height": bld_line,
            "width": bld_w,
            "length": bld_l,
            "players": [p for p in bld_players if p["is_starter"]] or bld_players[:11],
            "all_players": bld_players,
        },
        "attacking": {
            "formation": att_shape,
            "line_height": att_line,
            "width": att_w,
            "length": att_l,
            "players": [p for p in att_players if p["is_starter"]] or att_players[:11],
            "all_players": att_players,
        },
        "players": starters if starters else overall_players,
        "starters": starters,
        "substitutes": substitutes,
        "all_played_players": all_played,
        "players_overall": overall_players,
        "players_in_possession": bld_players,
        "players_out_of_possession": def_players,
    }
