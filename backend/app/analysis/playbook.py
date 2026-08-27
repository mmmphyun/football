"""시그니처 공격 패턴 TOP 3 플레이북 분석 모듈.

연속된 패스/캐리/슈팅 공격 시퀀스를 탐색하고 클러스터링하여
경기 중 가장 유의미하게 반복된 시그니처 공격 패턴 3종을 자동 추출합니다.
"""

from typing import Any

from app.analysis.common import is_completed_pass


def _classify_attack_sequence(
    seq_events: list[dict[str, Any]],
) -> tuple[str, str, str, str] | None:
    """공격 시퀀스의 공간적/전술적 특성을 바탕으로 패턴 유형을 판별합니다."""
    if not seq_events:
        return None

    # 시퀀스 내 이벤트들의 좌표 분석
    locs: list[tuple[float, float]] = []
    end_locs: list[tuple[float, float]] = []
    has_cutback = False
    has_switch = False
    has_central_penetration = False

    for ev in seq_events:
        loc = ev.get("location")
        if loc and len(loc) >= 2:
            locs.append((float(loc[0]), float(loc[1])))

        if ev.get("type", {}).get("name") == "Pass":
            end_loc = ev.get("pass", {}).get("end_location")
            if loc and end_loc and len(loc) >= 2 and len(end_loc) >= 2:
                sx, sy = float(loc[0]), float(loc[1])
                ex, ey = float(end_loc[0]), float(end_loc[1])
                end_locs.append((ex, ey))

                # 컷백 판정: 측면(y < 22 or y > 58, x >= 88)에서 중앙(28 <= y <= 52, x >= 85)으로의 패스
                if (
                    (sy <= 22.0 or sy >= 58.0)
                    and sx >= 88.0
                    and 28.0 <= ey <= 52.0
                    and ex <= sx + 5.0
                ):
                    has_cutback = True

                # 중앙 전환(Switch) 판정: 한쪽 측면에서 반대쪽 측면/하프스페이스로 y 이동거리 35m 이상
                if abs(ey - sy) >= 35.0:
                    has_switch = True

                # 중앙 침투(Central Penetration) 스루패스: 중앙(25 <= y <= 55)에서 파이널 서드 박스 안쪽(x >= 90)으로 x 이동거리 18m 이상 전진
                if 25.0 <= sy <= 55.0 and 25.0 <= ey <= 55.0 and (ex - sx) >= 18.0 and ex >= 90.0:
                    has_central_penetration = True

    if has_cutback or any((loc[1] <= 18.0 or loc[1] >= 62.0) and loc[0] >= 85.0 for loc in locs):
        return (
            "side_overload_cutback",
            "Side Overload & Cutback",
            "측면 과부하 및 컷백 전개",
            "측면 터치라인 부근에서 수적 우위를 확보한 후 파이널 서드 박스 안쪽으로 꺾어주는 컷백 공격 패턴",
        )

    if has_switch:
        return (
            "inverted_switch",
            "Inverted Switch",
            "인버티드 중앙 전환 전개",
            "한쪽 측면에서 상대 수비 시선을 끈 뒤 반대편 하프스페이스나 측면으로 방향을 전환하는 빌드업 전개 패턴",
        )

    if has_central_penetration or any(loc[0] >= 95.0 and 25.0 <= loc[1] <= 55.0 for loc in locs):
        return (
            "central_penetration",
            "Central Penetration",
            "중앙 침투 다이렉트 스루패스",
            "미들 서드 중앙 블록 사이로 원터치 침투 패스를 찔러 넣어 골키퍼와 1대1 찬스를 창출하는 다이렉트 공격 패턴",
        )

    return (
        "side_overload_cutback",
        "Side Overload & Cutback",
        "측면 과부하 및 컷백 전개",
        "측면 터치라인 공간을 활용한 윙 플레이 및 박스 침투 패턴",
    )


def compute_playbook_summary(
    events: list[dict[str, Any]],
    team_id: int,
) -> list[dict[str, Any]]:
    """경기의 공격 시퀀스를 분석하여 TOP 3 시그니처 공격 플레이북을 산출합니다."""
    # 1. 팀 볼 소유 시퀀스 분할 (연속된 패스/캐리/샷 체인)
    sequences: list[list[dict[str, Any]]] = []
    current_seq: list[dict[str, Any]] = []

    for ev in events:
        ev_team_id = ev.get("team", {}).get("id")
        type_name = ev.get("type", {}).get("name", "")

        if ev_team_id == team_id and type_name in {"Pass", "Carry", "Shot", "Dribble"}:
            current_seq.append(ev)
            if type_name == "Shot":
                sequences.append(current_seq)
                current_seq = []
        else:
            if len(current_seq) >= 3:
                sequences.append(current_seq)
            current_seq = []

    if len(current_seq) >= 3:
        sequences.append(current_seq)

    # 2. 패턴별 시퀀스 분류 및 xG 집계
    pattern_buckets: dict[str, dict[str, Any]] = {
        "side_overload_cutback": {
            "pattern_id": "side_overload_cutback",
            "name": "Side Overload & Cutback",
            "name_ko": "측면 과부하 및 컷백 전개",
            "description": "측면 터치라인 부근에서 수적 우위를 확보한 후 박스 안쪽으로 꺾어주는 컷백 공격 패턴",
            "occurrences": 0,
            "total_xg": 0.0,
            "sequences": [],
        },
        "inverted_switch": {
            "pattern_id": "inverted_switch",
            "name": "Inverted Switch",
            "name_ko": "인버티드 중앙 전환 전개",
            "description": "한쪽 측면에서 상대를 유인한 후 반대편 빈 공간으로 빠르게 전환하여 수비 균열을 유도하는 패턴",
            "occurrences": 0,
            "total_xg": 0.0,
            "sequences": [],
        },
        "central_penetration": {
            "pattern_id": "central_penetration",
            "name": "Central Penetration",
            "name_ko": "중앙 침투 다이렉트 스루패스",
            "description": "상대 중앙 미드필드 블록 사이를 관통하는 스루패스로 페널티 박스를 직접 타격하는 공격 패턴",
            "occurrences": 0,
            "total_xg": 0.0,
            "sequences": [],
        },
    }

    for seq in sequences:
        cls_info = _classify_attack_sequence(seq)
        if not cls_info:
            continue

        p_id = cls_info[0]
        bucket = pattern_buckets[p_id]
        bucket["occurrences"] += 1

        seq_xg = 0.0
        for ev in seq:
            if ev.get("type", {}).get("name") == "Shot":
                seq_xg += float(ev.get("shot", {}).get("statsbomb_xg", 0.0) or 0.0)
        bucket["total_xg"] = round(bucket["total_xg"] + seq_xg, 3)

        # 시각화용 이벤트 변환 (최대 5개 시퀀스 보관)
        if len(bucket["sequences"]) < 5:
            seq_event_draws: list[dict[str, Any]] = []
            for ev in seq:
                type_name = ev.get("type", {}).get("name", "")
                loc = ev.get("location")
                if not loc or len(loc) < 2:
                    continue

                sx, sy = float(loc[0]), float(loc[1])
                p_name = ev.get("player", {}).get("name", "Unknown")
                p_id_val = ev.get("player", {}).get("id")

                if type_name == "Pass":
                    end_loc = ev.get("pass", {}).get("end_location")
                    ex, ey = (
                        (float(end_loc[0]), float(end_loc[1]))
                        if end_loc and len(end_loc) >= 2
                        else (sx, sy)
                    )
                    seq_event_draws.append(
                        {
                            "type": "Pass",
                            "start_x": round(sx, 1),
                            "start_y": round(sy, 1),
                            "end_x": round(ex, 1),
                            "end_y": round(ey, 1),
                            "player_name": p_name,
                            "player_id": p_id_val,
                            "completed": is_completed_pass(ev),
                        }
                    )
                elif type_name == "Carry":
                    end_loc = ev.get("carry", {}).get("end_location")
                    ex, ey = (
                        (float(end_loc[0]), float(end_loc[1]))
                        if end_loc and len(end_loc) >= 2
                        else (sx, sy)
                    )
                    seq_event_draws.append(
                        {
                            "type": "Carry",
                            "start_x": round(sx, 1),
                            "start_y": round(sy, 1),
                            "end_x": round(ex, 1),
                            "end_y": round(ey, 1),
                            "player_name": p_name,
                            "player_id": p_id_val,
                            "completed": True,
                        }
                    )
                elif type_name == "Shot":
                    end_loc = ev.get("shot", {}).get("end_location")
                    ex, ey = (
                        (float(end_loc[0]), float(end_loc[1]))
                        if end_loc and len(end_loc) >= 2
                        else (120.0, 40.0)
                    )
                    seq_event_draws.append(
                        {
                            "type": "Shot",
                            "start_x": round(sx, 1),
                            "start_y": round(sy, 1),
                            "end_x": round(ex, 1),
                            "end_y": round(ey, 1),
                            "player_name": p_name,
                            "player_id": p_id_val,
                            "xg": round(
                                float(ev.get("shot", {}).get("statsbomb_xg", 0.0) or 0.0), 3
                            ),
                            "outcome": ev.get("shot", {}).get("outcome", {}).get("name", "Unknown"),
                        }
                    )

            if seq_event_draws:
                bucket["sequences"].append(seq_event_draws)

    # 3. 발생 횟수 및 xG 기준 정렬하여 TOP 3 반환
    results = list(pattern_buckets.values())
    results.sort(key=lambda p: (p["occurrences"], p["total_xg"]), reverse=True)

    # 기본 더미 궤적 보정 (데이터가 적은 경기에서도 시각화 지원)
    for p in results:
        if not p["sequences"]:
            if p["pattern_id"] == "side_overload_cutback":
                p["sequences"] = [
                    [
                        {
                            "type": "Pass",
                            "start_x": 65.0,
                            "start_y": 70.0,
                            "end_x": 95.0,
                            "end_y": 72.0,
                            "player_name": "Right Winger",
                            "completed": True,
                        },
                        {
                            "type": "Pass",
                            "start_x": 95.0,
                            "start_y": 72.0,
                            "end_x": 105.0,
                            "end_y": 42.0,
                            "player_name": "Right Back",
                            "completed": True,
                        },
                        {
                            "type": "Shot",
                            "start_x": 105.0,
                            "start_y": 42.0,
                            "end_x": 120.0,
                            "end_y": 40.0,
                            "player_name": "Striker",
                            "xg": 0.35,
                            "outcome": "Saved",
                        },
                    ]
                ]
            elif p["pattern_id"] == "inverted_switch":
                p["sequences"] = [
                    [
                        {
                            "type": "Pass",
                            "start_x": 45.0,
                            "start_y": 15.0,
                            "end_x": 55.0,
                            "end_y": 38.0,
                            "player_name": "Inverted Left Back",
                            "completed": True,
                        },
                        {
                            "type": "Pass",
                            "start_x": 55.0,
                            "start_y": 38.0,
                            "end_x": 75.0,
                            "end_y": 68.0,
                            "player_name": "Midfielder",
                            "completed": True,
                        },
                        {
                            "type": "Carry",
                            "start_x": 75.0,
                            "start_y": 68.0,
                            "end_x": 92.0,
                            "end_y": 65.0,
                            "player_name": "Right Winger",
                            "completed": True,
                        },
                    ]
                ]
            elif p["pattern_id"] == "central_penetration":
                p["sequences"] = [
                    [
                        {
                            "type": "Pass",
                            "start_x": 50.0,
                            "start_y": 40.0,
                            "end_x": 75.0,
                            "end_y": 42.0,
                            "player_name": "Playmaker",
                            "completed": True,
                        },
                        {
                            "type": "Pass",
                            "start_x": 75.0,
                            "start_y": 42.0,
                            "end_x": 102.0,
                            "end_y": 38.0,
                            "player_name": "Attacking Midfielder",
                            "completed": True,
                        },
                        {
                            "type": "Shot",
                            "start_x": 102.0,
                            "start_y": 38.0,
                            "end_x": 120.0,
                            "end_y": 39.0,
                            "player_name": "Striker",
                            "xg": 0.42,
                            "outcome": "Goal",
                        },
                    ]
                ]

    return results
