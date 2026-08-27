"""포메이션 및 선수별 평균 위치 분석 모듈.

UEFA 코칭 라이선스 표준의 6대 서브 국면(후방 빌드업/중원 전개/기회 창출/전방 압박/미들 블록/로우 블록)에서
선수별 평균 위치, 포메이션 앵커 좌표 및 팀 전술 컴팩트니스/라인높이 지표를 산출합니다.
"""

from collections import defaultdict
from typing import Any

from app.analysis.common import build_lineup_maps
from app.config import (
    SUBPHASE_BUILDUP_MAX_X,
    SUBPHASE_HIGH_PRESS_MIN_X,
    SUBPHASE_MID_BLOCK_MIN_X,
    SUBPHASE_PROGRESSION_MAX_X,
)

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
    three_sixty_frames: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """팀의 UEFA 6대 서브 국면 및 기본 국면별 대형, 선수 평균 위치, 컴팩트니스 지표를 산출합니다."""
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

    # 6대 서브 국면별 위치 수집 버킷
    # 1. 볼 소유 국면 (In-Possession)
    buildup_locs: dict[int, list[tuple[float, float]]] = defaultdict(list)
    progression_locs: dict[int, list[tuple[float, float]]] = defaultdict(list)
    final_third_locs: dict[int, list[tuple[float, float]]] = defaultdict(list)

    # 2. 볼 미소유 국면 (Out-of-Possession)
    high_press_locs: dict[int, list[tuple[float, float]]] = defaultdict(list)
    mid_block_locs: dict[int, list[tuple[float, float]]] = defaultdict(list)
    low_block_locs: dict[int, list[tuple[float, float]]] = defaultdict(list)

    all_locations: dict[int, list[tuple[float, float]]] = defaultdict(list)

    defensive_action_types = {
        "Pressure",
        "Tackle",
        "Interception",
        "Block",
        "Clearance",
        "Duel",
        "Foul Committed",
    }

    # 이벤트별 6대 서브 국면 매핑
    ev_subphase_map: dict[str, str] = {}
    for ev in events:
        ev_id = ev.get("id", "")
        poss_team_id = ev.get("possession_team", {}).get("id")
        type_name = ev.get("type", {}).get("name", "")
        loc = ev.get("location")
        x = float(loc[0]) if loc and len(loc) >= 1 else 60.0

        if poss_team_id != team_id or type_name in defensive_action_types:
            if x >= SUBPHASE_HIGH_PRESS_MIN_X:
                ev_subphase_map[ev_id] = "high_press"
            elif x >= SUBPHASE_MID_BLOCK_MIN_X:
                ev_subphase_map[ev_id] = "mid_block"
            else:
                ev_subphase_map[ev_id] = "low_block"
        else:
            if x < SUBPHASE_BUILDUP_MAX_X:
                ev_subphase_map[ev_id] = "buildup"
            elif x < SUBPHASE_PROGRESSION_MAX_X:
                ev_subphase_map[ev_id] = "progression"
            else:
                ev_subphase_map[ev_id] = "final_third"

    # 1. 360 프레임 데이터가 있는 경우 실측 위치 집계
    if three_sixty_frames:
        for f360 in three_sixty_frames:
            ev_uuid = f360.get("event_uuid")
            subphase = ev_subphase_map.get(ev_uuid, "progression")
            freeze_players = f360.get("freeze_frame", [])

            for fp in freeze_players:
                if not fp.get("teammate"):
                    continue
                loc = fp.get("location")
                if not loc or len(loc) < 2:
                    continue
                fx, fy = float(loc[0]), float(loc[1])
                is_actor = fp.get("actor", False)

                if is_actor:
                    for ev in events:
                        if ev.get("id") == ev_uuid:
                            p_id = ev.get("player", {}).get("id")
                            if p_id and p_id in players_meta:
                                all_locations[p_id].append((fx, fy))
                                if subphase == "buildup":
                                    buildup_locs[p_id].append((fx, fy))
                                elif subphase == "progression":
                                    progression_locs[p_id].append((fx, fy))
                                elif subphase == "final_third":
                                    final_third_locs[p_id].append((fx, fy))
                                elif subphase == "high_press":
                                    high_press_locs[p_id].append((fx, fy))
                                elif subphase == "mid_block":
                                    mid_block_locs[p_id].append((fx, fy))
                                elif subphase == "low_block":
                                    low_block_locs[p_id].append((fx, fy))
                            break

    # 2. 일반 이벤트 데이터 집계
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

        if poss_team_id != team_id or type_name in defensive_action_types:
            if x >= SUBPHASE_HIGH_PRESS_MIN_X:
                high_press_locs[p_id].append((x, y))
            elif x >= SUBPHASE_MID_BLOCK_MIN_X:
                mid_block_locs[p_id].append((x, y))
            else:
                low_block_locs[p_id].append((x, y))
        else:
            if x < SUBPHASE_BUILDUP_MAX_X:
                buildup_locs[p_id].append((x, y))
            elif x < SUBPHASE_PROGRESSION_MAX_X:
                progression_locs[p_id].append((x, y))
            else:
                final_third_locs[p_id].append((x, y))

    def _calc_player_metrics(
        loc_map: dict[int, list[tuple[float, float]]],
        phase_type: str = "overall",
    ) -> tuple[list[dict[str, Any]], float, float, float]:
        """선수별 평균 좌표, 라인 높이, 너비, 길이를 6대 서브 국면별 특성을 반영하여 산출합니다."""
        result: list[dict[str, Any]] = []
        for p_id, p_info in players_meta.items():
            locs = loc_map.get(p_id, [])
            overall_locs = all_locations.get(p_id, [])
            count = len(locs)
            pos_id = p_info.get("primary_position_id")
            anchor = get_position_anchor(pos_id)

            is_def = pos_id in DEFENDER_POSITION_IDS
            is_mid = pos_id in MIDFIELDER_POSITION_IDS
            is_gk = pos_id == 1

            if phase_type == "buildup":
                # 후방 빌드업: 센터백 벌림, 풀백 전진, 안정적 후방 볼 순환
                if is_gk:
                    dx, dy_scale = 2.0, 1.0
                elif is_def:
                    dx, dy_scale = 3.0, 1.20
                elif is_mid:
                    dx, dy_scale = 2.0, 1.05
                else:
                    dx, dy_scale = -4.0, 1.0
            elif phase_type == "progression":
                # 중원 전개: 3-2-4-1 대형, 풀백 인버티드 전진, 메짤라 하프스페이스 위치
                if is_gk:
                    dx, dy_scale = 5.0, 1.0
                elif is_def:
                    dx, dy_scale = 8.0, 1.10
                elif is_mid:
                    dx, dy_scale = 10.0, 1.05
                else:
                    dx, dy_scale = 8.0, 1.0
            elif phase_type == "final_third" or phase_type == "attacking":
                # 기회 창출 / 공격: 2-3-5 박스 타격, 최후방 잔류 수비 (Rest Defense)
                if is_gk:
                    dx, dy_scale = 8.0, 1.0
                elif is_def:
                    dx, dy_scale = 16.0, 1.15
                elif is_mid:
                    dx, dy_scale = 20.0, 1.15
                else:
                    dx, dy_scale = 16.0, 1.10
            elif phase_type == "high_press":
                # 전방 압박: 최전방부터 압박 라인을 올리고 대인 압박 대형 형성
                if is_gk:
                    dx, dy_scale = 6.0, 1.0
                elif is_def:
                    dx, dy_scale = 10.0, 0.90
                elif is_mid:
                    dx, dy_scale = 14.0, 0.85
                else:
                    dx, dy_scale = 16.0, 0.85
            elif phase_type == "mid_block" or phase_type == "defensive":
                # 미들 블록: 중원 콤팩트 두 줄 수비 (4-4-2 / 5-3-2)
                if is_gk:
                    dx, dy_scale = -2.0, 1.0
                elif is_def:
                    dx, dy_scale = -5.0, 0.80
                elif is_mid:
                    dx, dy_scale = -8.0, 0.80
                else:
                    dx, dy_scale = -10.0, 0.80
            elif phase_type == "low_block":
                # 로우 블록: 페널티 박스 보호 5-4-1 밀집 수비
                if is_gk:
                    dx, dy_scale = -3.0, 1.0
                elif is_def:
                    dx, dy_scale = -12.0, 0.75
                elif is_mid:
                    dx, dy_scale = -16.0, 0.75
                else:
                    dx, dy_scale = -18.0, 0.75
            else:
                dx, dy_scale = 0.0, 1.0

            if count >= 3:
                raw_avg_x = sum(pt[0] for pt in locs) / count
                raw_avg_y = sum(pt[1] for pt in locs) / count
                avg_x = 0.7 * raw_avg_x + 0.3 * (anchor[0] + dx)
                avg_y = 0.7 * raw_avg_y + 0.3 * (40.0 + (anchor[1] - 40.0) * dy_scale)
            elif len(overall_locs) >= 3:
                base_x = sum(pt[0] for pt in overall_locs) / len(overall_locs)
                base_y = sum(pt[1] for pt in overall_locs) / len(overall_locs)
                avg_x = base_x + dx
                avg_y = 40.0 + (base_y - 40.0) * dy_scale
            else:
                avg_x = anchor[0] + dx
                avg_y = 40.0 + (anchor[1] - 40.0) * dy_scale

            # 피치 영역 클램핑
            avg_x = max(3.0, min(117.0, avg_x))
            avg_y = max(4.0, min(76.0, avg_y))

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

        field_starters = [p for p in result if p["is_starter"] and p.get("position_id") != 1]
        if not field_starters:
            field_starters = [p for p in result if p.get("position_id") != 1][:10]

        if field_starters:
            xs = [p["x"] for p in field_starters]
            ys = [p["y"] for p in field_starters]
            length = round(max(xs) - min(xs), 2)
            width = round(max(ys) - min(ys), 2)

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

    # 6대 서브 국면 지표 산출
    bld_players, bld_line, bld_w, bld_l = _calc_player_metrics(buildup_locs, phase_type="buildup")
    prg_players, prg_line, prg_w, prg_l = _calc_player_metrics(
        progression_locs, phase_type="progression"
    )
    fin_players, fin_line, fin_w, fin_l = _calc_player_metrics(
        final_third_locs, phase_type="final_third"
    )
    hp_players, hp_line, hp_w, hp_l = _calc_player_metrics(high_press_locs, phase_type="high_press")
    mb_players, mb_line, mb_w, mb_l = _calc_player_metrics(mid_block_locs, phase_type="mid_block")
    lb_players, lb_line, lb_w, lb_l = _calc_player_metrics(low_block_locs, phase_type="low_block")

    # 전반적 지표 계산
    overall_players, overall_line, overall_w, overall_l = _calc_player_metrics(
        all_locations, phase_type="overall"
    )

    starters = [p for p in overall_players if p["is_starter"]]
    substitutes = [p for p in overall_players if not p["is_starter"] and p["event_count"] > 0]
    all_played = starters + substitutes

    subphases_data = {
        "buildup": {
            "name": "후방 빌드업",
            "name_en": "Build-up",
            "category": "in_possession",
            "formation": _infer_shape_string(bld_players),
            "line_height": bld_line,
            "width": bld_w,
            "length": bld_l,
            "players": [p for p in bld_players if p["is_starter"]] or bld_players[:11],
            "all_players": bld_players,
        },
        "progression": {
            "name": "중원 전개",
            "name_en": "Progression",
            "category": "in_possession",
            "formation": _infer_shape_string(prg_players),
            "line_height": prg_line,
            "width": prg_w,
            "length": prg_l,
            "players": [p for p in prg_players if p["is_starter"]] or prg_players[:11],
            "all_players": prg_players,
        },
        "final_third": {
            "name": "기회 창출",
            "name_en": "Final Third",
            "category": "in_possession",
            "formation": _infer_shape_string(fin_players),
            "line_height": fin_line,
            "width": fin_w,
            "length": fin_l,
            "players": [p for p in fin_players if p["is_starter"]] or fin_players[:11],
            "all_players": fin_players,
        },
        "high_press": {
            "name": "전방 압박",
            "name_en": "High Press",
            "category": "out_of_possession",
            "formation": _infer_shape_string(hp_players),
            "line_height": hp_line,
            "width": hp_w,
            "length": hp_l,
            "players": [p for p in hp_players if p["is_starter"]] or hp_players[:11],
            "all_players": hp_players,
        },
        "mid_block": {
            "name": "미들 블록",
            "name_en": "Mid-Block",
            "category": "out_of_possession",
            "formation": _infer_shape_string(mb_players),
            "line_height": mb_line,
            "width": mb_w,
            "length": mb_l,
            "players": [p for p in mb_players if p["is_starter"]] or mb_players[:11],
            "all_players": mb_players,
        },
        "low_block": {
            "name": "로우 블록",
            "name_en": "Low-Block",
            "category": "out_of_possession",
            "formation": _infer_shape_string(lb_players),
            "line_height": lb_line,
            "width": lb_w,
            "length": lb_l,
            "players": [p for p in lb_players if p["is_starter"]] or lb_players[:11],
            "all_players": lb_players,
        },
    }

    return {
        "team_id": team_id,
        "formation": formation_name,
        "formation_name": formation_name,
        "team_length": overall_l,
        "team_width": overall_w,
        "team_center_x": round(
            sum(p["x"] for p in (starters or overall_players)) / len(starters or overall_players), 2
        ),
        "team_center_y": round(
            sum(p["y"] for p in (starters or overall_players)) / len(starters or overall_players), 2
        ),
        "subphases": subphases_data,
        "defensive": subphases_data["mid_block"],
        "buildup": subphases_data["buildup"],
        "attacking": subphases_data["final_third"],
        "players": starters if starters else overall_players,
        "starters": starters,
        "substitutes": substitutes,
        "all_played_players": all_played,
        "players_overall": overall_players,
        "players_in_possession": prg_players,
        "players_out_of_possession": mb_players,
    }

