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
    """실측 X좌표의 최적 3~4선 1차원 군집화(Line Clustering)를 통해 국면별 실제 전술 대형을 도출합니다."""
    field_players = [p for p in players_list if p.get("position_id") != 1 and p.get("is_starter")]
    if len(field_players) < 8:
        field_players = [p for p in players_list if p.get("position_id") != 1][:10]

    if len(field_players) != 10:
        return "4-3-3"

    sorted_p = sorted(field_players, key=lambda p: p["x"])
    xs = [p["x"] for p in sorted_p]

    best_shape = "4-3-3"
    min_variance = float("inf")

    # 1. 4선 분할 탐색 (예: 3-2-4-1, 4-2-3-1, 2-3-4-1, 3-3-3-1 등 현대 축구 빌드업/전개 대형)
    for c1 in range(2, 6):  # 1선: 수비 라인 (2~5명)
        for c2 in range(1, 4):  # 2선: 수비형/후방 미드필더 (1~3명)
            for c3 in range(1, 5):  # 3선: 2선 공격/윙어 (1~4명)
                c4 = 10 - (c1 + c2 + c3)  # 4선: 최전방 스트라이커 (1~3명)
                if 1 <= c4 <= 3:
                    g1 = xs[:c1]
                    g2 = xs[c1 : c1 + c2]
                    g3 = xs[c1 + c2 : c1 + c2 + c3]
                    g4 = xs[c1 + c2 + c3 :]

                    gap1 = min(g2) - max(g1)
                    gap2 = min(g3) - max(g2)
                    gap3 = min(g4) - max(g3)

                    if gap1 >= 3.0 and gap2 >= 3.0 and gap3 >= 3.0:
                        var1 = sum((x - sum(g1) / len(g1)) ** 2 for x in g1)
                        var2 = sum((x - sum(g2) / len(g2)) ** 2 for x in g2)
                        var3 = sum((x - sum(g3) / len(g3)) ** 2 for x in g3)
                        var4 = sum((x - sum(g4) / len(g4)) ** 2 for x in g4)
                        total_var = var1 + var2 + var3 + var4
                        if total_var < min_variance:
                            min_variance = total_var
                            best_shape = f"{c1}-{c2}-{c3}-{c4}"

    # 2. 4선 분할에서 갭을 못 찾은 경우 3선 분할 탐색 (예: 4-3-3, 4-4-2, 3-5-2, 5-3-2 등)
    if min_variance == float("inf"):
        for c1 in range(2, 6):
            for c2 in range(2, 6):
                c3 = 10 - (c1 + c2)
                if 1 <= c3 <= 4:
                    g1 = xs[:c1]
                    g2 = xs[c1 : c1 + c2]
                    g3 = xs[c1 + c2 :]

                    gap1 = min(g2) - max(g1)
                    gap2 = min(g3) - max(g2)

                    if gap1 >= 2.5 and gap2 >= 2.5:
                        var1 = sum((x - sum(g1) / len(g1)) ** 2 for x in g1)
                        var2 = sum((x - sum(g2) / len(g2)) ** 2 for x in g2)
                        var3 = sum((x - sum(g3) / len(g3)) ** 2 for x in g3)
                        total_var = var1 + var2 + var3
                        if total_var < min_variance:
                            min_variance = total_var
                            best_shape = f"{c1}-{c2}-{c3}"

    return best_shape


def _trimmed_mean(values: list[float], trim_ratio: float = 0.15) -> float:
    """상하위 trim_ratio 비율의 세트피스 잔여 및 극단 아웃라이어를 제거한 절사 평균을 계산합니다."""
    if not values:
        return 0.0
    n = len(values)
    if n <= 4:
        return sum(values) / n
    sorted_v = sorted(values)
    k = int(n * trim_ratio)
    if k > 0 and 2 * k < n:
        trimmed = sorted_v[k : n - k]
        return sum(trimmed) / len(trimmed)
    return sum(values) / n


def compute_formation_summary(
    events: list[dict[str, Any]],
    lineups: list[dict[str, Any]],
    team_id: int,
    three_sixty_frames: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """팀의 UEFA 6대 서브 국면 및 기본 국면별 하이브리드 대형, 선수 위치, 전술 역할, 컴팩트니스 지표를 산출합니다."""
    lineup_maps = build_lineup_maps(lineups)
    team_meta = lineup_maps.get(team_id, {"players": {}, "starting_xi": []})
    players_meta = team_meta.get("players", {})
    starting_xi = set(team_meta.get("starting_xi", []))

    # 기본 선발 포메이션 식별 (StatsBomb tactics)
    formation_name = "4-3-3"
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

    # 6대 서브 국면별 오픈 플레이(Regular Play) 실측 위치 수집 버킷
    # 1. 볼 소유 국면 (In-Possession)
    buildup_locs: dict[int, list[tuple[float, float]]] = defaultdict(list)
    progression_locs: dict[int, list[tuple[float, float]]] = defaultdict(list)
    final_third_locs: dict[int, list[tuple[float, float]]] = defaultdict(list)

    # 2. 볼 미소유 국면 (Out-of-Possession)
    high_press_locs: dict[int, list[tuple[float, float]]] = defaultdict(list)
    mid_block_locs: dict[int, list[tuple[float, float]]] = defaultdict(list)
    low_block_locs: dict[int, list[tuple[float, float]]] = defaultdict(list)

    all_openplay_locations: dict[int, list[tuple[float, float]]] = defaultdict(list)

    # 순수 오픈 플레이(Regular Play) 이벤트만 추출하여 세트피스 노이즈 완전 배제
    for ev in events:
        play_pattern = ev.get("play_pattern", {}).get("name", "")
        if play_pattern != "Regular Play":
            continue

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
        all_openplay_locations[p_id].append((x, y))

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
            # 우리 팀 볼 미소유 국면 (수비 액션)
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
        """선발 포지션 구조적 앵커와 실측 오픈플레이 전술 변위를 결합한 하이브리드 좌표 및 컴팩트니스를 산출합니다."""
        # 국면별 기준 베이스 X축 오프셋
        phase_offset_map = {
            "buildup": -12.0,
            "progression": 0.0,
            "final_third": 14.0,
            "high_press": 10.0,
            "mid_block": -2.0,
            "low_block": -16.0,
            "overall": 0.0,
        }
        phase_offset = phase_offset_map.get(phase_type, 0.0)

        result: list[dict[str, Any]] = []
        for p_id, p_info in players_meta.items():
            locs = loc_map.get(p_id, [])
            overall_locs = all_openplay_locations.get(p_id, [])
            count = len(locs)
            pos_id = p_info.get("primary_position_id")
            anchor = get_position_anchor(pos_id)

            if count >= 3:
                raw_trim_x = _trimmed_mean([pt[0] for pt in locs], trim_ratio=0.15)
                raw_trim_y = _trimmed_mean([pt[1] for pt in locs], trim_ratio=0.15)
            elif len(overall_locs) >= 3:
                raw_trim_x = (
                    _trimmed_mean([pt[0] for pt in overall_locs], trim_ratio=0.15) + phase_offset
                )
                raw_trim_y = _trimmed_mean([pt[1] for pt in overall_locs], trim_ratio=0.15)
            else:
                raw_trim_x = anchor[0] + phase_offset
                raw_trim_y = anchor[1]

            # 하이브리드 블렌딩: 기본 전술 앵커(구조적 뼈대) 45% + 실측 오픈플레이 전술 변위 55%
            if pos_id == 1:
                # 골키퍼는 골문 앞 안정적 보호 (5.5m ~ 16.0m)
                hybrid_x = max(5.5, min(16.0, 0.6 * anchor[0] + 0.4 * raw_trim_x))
                hybrid_y = max(34.0, min(46.0, 0.7 * anchor[1] + 0.3 * raw_trim_y))
            else:
                base_x = anchor[0] + phase_offset
                hybrid_x = 0.45 * base_x + 0.55 * raw_trim_x
                hybrid_y = 0.40 * anchor[1] + 0.60 * raw_trim_y

            # 피치 영역 클램핑 (StatsBomb 규격 120 x 80)
            hybrid_x = max(3.0, min(116.0, hybrid_x))
            hybrid_y = max(4.0, min(76.0, hybrid_y))

            disp_name = p_info.get("player_nickname") or p_info.get("player_name", "Unknown")
            pos_name = p_info.get("primary_position", "Player")

            # 실측 기반 전술 역할 판정 (하이브리드 실측 좌표 기준)
            role_en, role_ko, role_desc = determine_tactical_role(
                position_id=pos_id,
                position_name=pos_name,
                avg_x=hybrid_x,
                avg_y=hybrid_y,
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
                    "x": round(hybrid_x, 2),
                    "y": round(hybrid_y, 2),
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
            length = max(10.0, round(max(xs) - min(xs), 2))
            width = max(15.0, round(max(ys) - min(ys), 2))

            defenders = [p for p in field_starters if p.get("position_id") in DEFENDER_POSITION_IDS]
            if defenders:
                line_height = round(sum(p["x"] for p in defenders) / len(defenders), 2)
            else:
                sorted_xs = sorted(xs)
                line_height = round(sum(sorted_xs[:3]) / min(3, len(sorted_xs)), 2)

            line_height = max(10.0, min(85.0, line_height))
        else:
            length = 30.0
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
        all_openplay_locations, phase_type="overall"
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
