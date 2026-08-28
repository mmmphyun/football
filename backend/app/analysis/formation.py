"""포메이션 및 선수별 평균 위치 분석 모듈.

UEFA 코칭 라이선스 표준의 6대 서브 국면(후방 빌드업/중원 전개/기회 창출/전방 압박/미들 블록/로우 블록)에서
하드코딩된 앵커 블렌딩을 전면 제거하고 100% 실측 원시 이벤트 데이터를 기반으로
선수별 평균 위치, 실측 기반 전술적 역할(tactical_role), 포메이션 대형(Shape) 및 컴팩트니스 지표를 산출합니다.
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

# StatsBomb 포지션 ID 기준 기본 앵커 좌표 (x: 0~120, y: 0~80) - 이벤트 0건 시 폴백용으로만 사용
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
    """포지션 ID에 대응하는 표준 앵커 좌표를 반환합니다 (실측 데이터 부재 시 폴백 전용)."""
    if position_id is not None and position_id in POSITION_ANCHORS:
        return POSITION_ANCHORS[position_id]
    return (60.0, 40.0)


def determine_tactical_role(
    position_id: int | None,
    position_name: str | None,
    avg_x: float,
    avg_y: float,
    actions_count: int,
) -> tuple[str, str, str]:
    """선수의 선발 포지션과 실제 경기 실측 평균 위치를 바탕으로 실측 전술 역할을 판정합니다.

    Returns:
        tuple[str, str, str]: (role_en, role_ko, role_desc)
    """
    pos_id = position_id or 0

    # 1. 골키퍼
    if pos_id == 1:
        if avg_x >= 10.5:
            return (
                "Sweeper Keeper",
                "스위퍼 키퍼",
                "페널티 박스 바깥까지 전진하여 후방 수비 라인 배후를 커버하고 빌드업에 적극 기여",
            )
        return (
            "Traditional Goalkeeper",
            "클래식 골키퍼",
            "골문 및 페널티 박스 영역 방어와 안정적인 후방 선방에 집중",
        )

    # 2. 풀백 / 윙백
    if pos_id in {2, 6, 7, 8}:
        if avg_x >= 55.0 and (avg_y <= 18.0 or avg_y >= 62.0):
            return (
                "Overlapping Fullback",
                "오버래핑 공격형 풀백",
                "터치라인을 따라 하프라인 위로 고전진하여 공격 폭을 확보하고 측면 전개를 주도",
            )
        elif avg_x >= 50.0 and (22.0 <= avg_y <= 58.0):
            return (
                "Inverted Fullback",
                "인버티드 풀백",
                "측면에서 중앙 및 하프스페이스로 좁혀 들어와 중원 볼 순환과 미드필드 수적 우위 형성",
            )
        else:
            return (
                "Defensive Fullback",
                "수비형 풀백",
                "후방 수비 밸런스를 유지하며 상대 측면 공격 차단 및 안정적 빌드업 지원",
            )

    # 3. 센터백
    if pos_id in {3, 4, 5}:
        if avg_x >= 41.0:
            return (
                "Ball-Playing Center Back",
                "볼플레잉 센터백",
                "높은 수비 라인을 유지하며 최후방에서 전진 패스 및 빌드업 전개를 적극 주도",
            )
        elif avg_y <= 27.0 or avg_y >= 53.0:
            return (
                "Wide Build-up Center Back",
                "와이드 빌드업 센터백",
                "빌드업 시 좌우 측면으로 넓게 벌려서서 풀백 전진을 지원하고 후방 볼 순환 담당",
            )
        else:
            return (
                "Stopper Center Back",
                "스토퍼 센터백",
                "페널티 박스 중앙을 단단히 방어하며 상대 공격수 차단 및 클리어링 전담",
            )

    # 4. 미드필더
    if pos_id in {9, 10, 11}:
        # 수비형 미드필더
        if avg_x <= 58.0:
            return (
                "Deep-lying Playmaker",
                "딥라잉 플레이메이커 (레지스타)",
                "최후방 수비 라인 바로 앞에서 중원 볼 배급과 경기 템포 조율을 지휘",
            )
        else:
            return (
                "Holding Midfielder",
                "홀딩 미드필더",
                "센터백 앞 공간을 보호하고 상대 2선 침투 차단 및 수비 밸런스 유지",
            )
    elif pos_id in {12, 13, 14, 15, 16, 18, 19, 20}:
        # 중앙 / 공격형 미드필더
        if avg_x >= 65.0 and (18.0 <= avg_y <= 32.0 or 48.0 <= avg_y <= 62.0):
            return (
                "Half-space Playmaker",
                "하프스페이스 플레이메이커",
                "상대 수비-미드필더 사이 하프스페이스 공간을 타격하며 킬패스 및 침투 주도",
            )
        elif avg_x >= 60.0:
            return (
                "Box-to-Box Midfielder",
                "박스투박스 미드필더",
                "공격 가담과 수비 복귀를 쉼 없이 오가며 중원 에너지와 압박에 기여",
            )
        else:
            return (
                "Central Controller",
                "센트럴 컨트롤러",
                "중원에서 안정적인 볼 키핑과 패스 연결로 팀의 경기 장악력 지원",
            )

    # 5. 윙어
    if pos_id in {17, 21}:
        if avg_y <= 18.0 or avg_y >= 62.0:
            return (
                "Touchline Winger",
                "클래식 터치라인 윙어",
                "터치라인에 밀착하여 측면을 넓히고 1:1 드리블 돌파 및 크로스 전개",
            )
        elif 22.0 <= avg_y <= 58.0:
            return (
                "Inside Playmaker",
                "인사이드 플레이메이커",
                "측면에서 중앙 2선 및 하프스페이스로 좁혀 들어와 찬스 메이킹과 슈팅에 기여",
            )
        else:
            return (
                "Attacking Winger",
                "어태킹 윙어",
                "파이널 서드에서 빠른 공간 침투와 박스 타격을 노리는 측면 공격수",
            )

    # 6. 스트라이커 / 포워드
    if pos_id in {22, 23, 24, 25}:
        if avg_x < 85.0:
            return (
                "False 9",
                "가짜 9번 (펄스 나인)",
                "최전방에 머물지 않고 2선으로 내려와 중원 연계와 공간 창출을 지원",
            )
        elif avg_x >= 88.0 and (30.0 <= avg_y <= 50.0):
            return (
                "Advanced Target Striker",
                "어드밴스드 타겟 스트라이커",
                "상대 페널티 박스 중앙에 앵커링하여 크로스 마무리 및 박스 타격 전담",
            )
        else:
            return (
                "Pressing Forward",
                "프레싱 포워드",
                "전방에서부터 강한 압박으로 상대 빌드업을 방해하고 배후 공간을 침투",
            )

    # 기본 폴백
    return (
        position_name or "Player",
        position_name or "선수",
        "팀의 전술적 지시에 따라 포지션 역할을 수행",
    )


def _infer_shape_string(players_list: list[dict[str, Any]]) -> str:
    """실측 X좌표 클러스터링을 바탕으로 팀의 3~4선 포메이션 대형(예: 4-3-3, 3-2-4-1, 4-4-2 등)을 추론합니다."""
    field_players = [p for p in players_list if p.get("position_id") != 1 and p.get("is_starter")]
    if len(field_players) < 8:
        field_players = [p for p in players_list if p.get("position_id") != 1][:10]

    if not field_players:
        return "4-3-3"

    sorted_p = sorted(field_players, key=lambda p: p["x"])

    # 선수 간 X좌표 갭 기반 적응형 라인 분할 (8.0m 이상 차이나면 새 라인으로 분리)
    lines: list[list[dict[str, Any]]] = []
    current_line = [sorted_p[0]]

    for p in sorted_p[1:]:
        if p["x"] - current_line[-1]["x"] > 8.5:
            lines.append(current_line)
            current_line = [p]
        else:
            current_line.append(p)
    lines.append(current_line)

    line_counts = [len(line) for line in lines]

    # 3선 ~ 5선 구조가 10명과 일치하면 해당 포메이션 반환
    if sum(line_counts) == len(field_players) and len(line_counts) in (3, 4, 5):
        return "-".join(str(c) for c in line_counts)

    # 2선이나 6선 이상으로 과분할/과소분할된 경우 3선(DF/MF/FW) 포지션 ID 기준으로 클러스터링
    df_count = sum(1 for p in field_players if p.get("position_id") in DEFENDER_POSITION_IDS)
    mf_count = sum(1 for p in field_players if p.get("position_id") in MIDFIELDER_POSITION_IDS)
    fw_count = sum(1 for p in field_players if p.get("position_id") in FORWARD_POSITION_IDS)

    if df_count > 0 and (df_count + mf_count + fw_count == len(field_players)):
        return f"{df_count}-{mf_count}-{fw_count}"

    return "4-3-3"


def compute_formation_summary(
    events: list[dict[str, Any]],
    lineups: list[dict[str, Any]],
    team_id: int,
    three_sixty_frames: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """팀의 UEFA 6대 서브 국면 및 기본 국면별 실측 대형, 선수 평균 위치, 전술 역할, 컴팩트니스 지표를 산출합니다."""
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

    # 6대 서브 국면별 실측 위치 수집 버킷
    # 1. 볼 소유 국면 (In-Possession)
    buildup_locs: dict[int, list[tuple[float, float]]] = defaultdict(list)
    progression_locs: dict[int, list[tuple[float, float]]] = defaultdict(list)
    final_third_locs: dict[int, list[tuple[float, float]]] = defaultdict(list)

    # 2. 볼 미소유 국면 (Out-of-Possession)
    high_press_locs: dict[int, list[tuple[float, float]]] = defaultdict(list)
    mid_block_locs: dict[int, list[tuple[float, float]]] = defaultdict(list)
    low_block_locs: dict[int, list[tuple[float, float]]] = defaultdict(list)

    all_locations: dict[int, list[tuple[float, float]]] = defaultdict(list)

    # 순수 이벤트 스트림 기반 실측 위치 수집 (반전 없이 0->120 그대로 사용)
    for ev in events:
        ev_team_id = ev.get("team", {}).get("id")
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
            # 우리 팀 볼 소유 국면
            if x < SUBPHASE_BUILDUP_MAX_X:
                buildup_locs[p_id].append((x, y))
            elif x < SUBPHASE_PROGRESSION_MAX_X:
                progression_locs[p_id].append((x, y))
            else:
                final_third_locs[p_id].append((x, y))
        else:
            # 우리 팀 볼 미소유 국면 (우리 팀 선수가 수행한 수비 액션 등)
            if ev_team_id == team_id:
                if x >= SUBPHASE_HIGH_PRESS_MIN_X:
                    high_press_locs[p_id].append((x, y))
                elif x >= SUBPHASE_MID_BLOCK_MIN_X:
                    mid_block_locs[p_id].append((x, y))
                else:
                    low_block_locs[p_id].append((x, y))

    def _calc_player_metrics(
        loc_map: dict[int, list[tuple[float, float]]],
        phase_type: str = "overall",
    ) -> tuple[list[dict[str, Any]], float, float, float]:
        """선수별 실측 평균 좌표 및 컴팩트니스(라인 높이, 너비, 길이)를 산출합니다.

        국면별 실측 이벤트가 존재하는 선수는 100% 실측 평균을 그대로 사용하고,
        해당 국면 데이터가 0건인 경우에만 국면의 공간적 전술 정의(phase fallback)를 적용합니다.
        """
        # 국면별 폴백 X축 델타 (데이터 부재 시에만 적용)
        phase_dx_map = {
            "buildup": -6.0,
            "progression": 0.0,
            "final_third": 8.0,
            "high_press": 7.0,
            "mid_block": 0.0,
            "low_block": -10.0,
            "overall": 0.0,
        }
        phase_dx = phase_dx_map.get(phase_type, 0.0)

        result: list[dict[str, Any]] = []
        for p_id, p_info in players_meta.items():
            locs = loc_map.get(p_id, [])
            overall_locs = all_locations.get(p_id, [])
            count = len(locs)
            pos_id = p_info.get("primary_position_id")
            anchor = get_position_anchor(pos_id)

            if count >= 1:
                # 100% 순수 실측 평균
                avg_x = sum(pt[0] for pt in locs) / count
                avg_y = sum(pt[1] for pt in locs) / count
            elif len(overall_locs) >= 1:
                base_x = sum(pt[0] for pt in overall_locs) / len(overall_locs)
                base_y = sum(pt[1] for pt in overall_locs) / len(overall_locs)
                avg_x = base_x + phase_dx
                avg_y = base_y
            else:
                avg_x = anchor[0] + phase_dx
                avg_y = anchor[1]

            # 피치 영역 클램핑 (StatsBomb 규격 120 x 80)
            avg_x = max(0.0, min(120.0, avg_x))
            avg_y = max(0.0, min(80.0, avg_y))

            disp_name = p_info.get("player_nickname") or p_info.get("player_name", "Unknown")
            pos_name = p_info.get("primary_position", "Player")

            # 실측 기반 전술 역할 판정
            role_en, role_ko, role_desc = determine_tactical_role(
                position_id=pos_id,
                position_name=pos_name,
                avg_x=avg_x,
                avg_y=avg_y,
                actions_count=count or len(overall_locs),
            )

            result.append(
                {
                    "player_id": p_id,
                    "player_name": disp_name,
                    "player_nickname": p_info.get("player_nickname"),
                    "full_name": p_info.get("player_name"),
                    "jersey_number": p_info.get("jersey_number"),
                    "position": pos_name,
                    "position_id": pos_id,
                    "tactical_role": role_en,
                    "tactical_role_ko": role_ko,
                    "tactical_role_desc": role_desc,
                    "is_starter": p_id in starting_xi,
                    "event_count": count or len(overall_locs),
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

            line_height = max(10.0, min(85.0, line_height))
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

    def _extract_eleven(p_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
        starters = [p for p in p_list if p["is_starter"]]
        if len(starters) == 11:
            return starters
        if len(starters) > 11:
            return starters[:11]
        others = [p for p in p_list if not p["is_starter"]]
        return (starters + others)[:11]

    starters = _extract_eleven(overall_players)
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
            "players": _extract_eleven(bld_players),
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
            "players": _extract_eleven(prg_players),
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
            "players": _extract_eleven(fin_players),
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
            "players": _extract_eleven(hp_players),
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
            "players": _extract_eleven(mb_players),
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
            "players": _extract_eleven(lb_players),
            "all_players": lb_players,
        },
    }

    return {
        "team_id": team_id,
        "formation": formation_name,
        "formation_name": formation_name,
        "team_length": overall_l,
        "team_width": overall_w,
        "team_center_x": round(sum(p["x"] for p in starters) / len(starters), 2)
        if starters
        else 60.0,
        "team_center_y": round(sum(p["y"] for p in starters) / len(starters), 2)
        if starters
        else 40.0,
        "subphases": subphases_data,
        "defensive": subphases_data["mid_block"],
        "buildup": subphases_data["buildup"],
        "attacking": subphases_data["final_third"],
        "players": starters,
        "starters": starters,
        "substitutes": substitutes,
        "all_played_players": all_played,
        "players_overall": starters,
        "players_in_possession": _extract_eleven(prg_players),
        "players_out_of_possession": _extract_eleven(mb_players),
    }
