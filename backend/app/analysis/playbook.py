"""학계 연구 기반 5대 시그니처 공격 패턴 플레이북 분석 모듈.

연속된 패스/캐리/슈팅 공격 시퀀스를 포제션(Possession) 체인 단위로 분할하고,
패스 완료 무결성을 검증하여 5대 시그니처 공격 전개 패턴을 엄밀하게 자동 추출합니다.
"""

from collections import defaultdict
from typing import Any

from app.analysis.common import event_time, is_completed_pass
from app.config import (
    CUTBACK_FLANK_X_MIN,
    CUTBACK_FLANK_Y_BOTTOM,
    CUTBACK_FLANK_Y_TOP,
    CUTBACK_TARGET_X_MIN,
    CUTBACK_TARGET_Y_MAX,
    CUTBACK_TARGET_Y_MIN,
    DEEP_LINEBREAK_END_MIN_X,
    DEEP_LINEBREAK_MIN_DX,
    DEEP_LINEBREAK_START_MAX_X,
    HALFSPACE_X_MAX,
    HALFSPACE_X_MIN,
    HALFSPACE_Y_LEFT_MAX,
    HALFSPACE_Y_LEFT_MIN,
    HALFSPACE_Y_RIGHT_MAX,
    HALFSPACE_Y_RIGHT_MIN,
    HIGHTURNOVER_MAX_TIME_SEC,
    HIGHTURNOVER_RECOVERY_MIN_X,
    POCKET_X_MAX,
    POCKET_X_MIN,
    POCKET_Y_MAX,
    POCKET_Y_MIN,
)

# 3자 연계 판정 현실적 시간 윈도우 (초)
THIRD_MAN_WINDOW_SEC: float = 4.0


def _classify_attack_sequence(
    seq_events: list[dict[str, Any]],
) -> tuple[str, str, str, str] | None:
    """공격 시퀀스의 공간적/전술적 특성을 바탕으로 5대 시그니처 패턴 유형을 판별합니다."""
    if len(seq_events) < 2:
        return None

    # 1) 전방 압박 탈취 즉시 속공 슛 (High-turnover Direct Strike)
    first_ev = seq_events[0]
    first_type = first_ev.get("type", {}).get("name", "")
    first_loc = first_ev.get("location")
    if (
        first_type in {"Ball Recovery", "Interception", "Tackle", "Duel", "Dispossessed"}
        and first_loc
        and len(first_loc) >= 1
        and float(first_loc[0]) >= HIGHTURNOVER_RECOVERY_MIN_X
    ):
        last_ev = seq_events[-1]
        if last_ev.get("type", {}).get("name") == "Shot":
            duration = event_time(last_ev) - event_time(first_ev)
            if duration <= HIGHTURNOVER_MAX_TIME_SEC + 1.0 and len(seq_events) <= 6:
                return (
                    "high_turnover_strike",
                    "High-turnover Direct Strike",
                    "전방 압박 탈취 속공 슛",
                    "상대 진영에서 볼을 즉시 탈취한 후 빠른 템포로 페널티 박스를 직접 타격하는 역습 패턴",
                )

    has_cutback = False
    has_pocket_third_man = False
    has_halfspace_underlap = False
    has_deep_linebreak = False

    n = len(seq_events)
    for i, ev in enumerate(seq_events):
        type_name = ev.get("type", {}).get("name", "")
        loc = ev.get("location")
        if not loc or len(loc) < 2:
            continue

        sx, sy = float(loc[0]), float(loc[1])

        if type_name == "Pass":
            # 패스가 성공하지 못한 중간 패스는 패턴 기점으로 불인정
            if not is_completed_pass(ev):
                continue

            end_loc = ev.get("pass", {}).get("end_location")
            if not end_loc or len(end_loc) < 2:
                continue

            ex, ey = float(end_loc[0]), float(end_loc[1])
            dx = ex - sx

            # 4) 후방 딥 라인브레이킹 종패스 판정
            if (
                sx <= DEEP_LINEBREAK_START_MAX_X
                and ex >= DEEP_LINEBREAK_END_MIN_X
                and dx >= DEEP_LINEBREAK_MIN_DX
            ):
                has_deep_linebreak = True

            # 1) 측면 과부하 & 컷백 판정 (음의 패스: ex <= sx + 3.0)
            in_flank = (sy <= CUTBACK_FLANK_Y_TOP or sy >= CUTBACK_FLANK_Y_BOTTOM) and sx >= CUTBACK_FLANK_X_MIN
            target_in_box = CUTBACK_TARGET_Y_MIN <= ey <= CUTBACK_TARGET_Y_MAX and ex >= CUTBACK_TARGET_X_MIN
            is_negative_pass = ex <= sx + 3.0
            if in_flank and target_in_box and is_negative_pass:
                has_cutback = True

            # 2) 포켓(Zone 14) 3자 연계 침투 판정
            if (
                POCKET_X_MIN <= ex <= POCKET_X_MAX
                and POCKET_Y_MIN <= ey <= POCKET_Y_MAX
                and i + 1 < n
            ):
                next_ev = seq_events[i + 1]
                t_diff = event_time(next_ev) - event_time(ev)
                if t_diff <= THIRD_MAN_WINDOW_SEC:
                    has_pocket_third_man = True

            # 3) 하프스페이스 언더래핑 & 얼리크로스 판정
            in_left_hs = HALFSPACE_Y_LEFT_MIN <= sy <= HALFSPACE_Y_LEFT_MAX
            in_right_hs = HALFSPACE_Y_RIGHT_MIN <= sy <= HALFSPACE_Y_RIGHT_MAX
            if (
                (in_left_hs or in_right_hs)
                and HALFSPACE_X_MIN <= sx <= HALFSPACE_X_MAX
                and ex >= 95.0
                and 24.0 <= ey <= 56.0
            ):
                has_halfspace_underlap = True

    # 우선순위 부여 (특화 패턴 우선)
    if has_cutback:
        return (
            "side_overload_cutback",
            "Side Overload & Cutback",
            "측면 과부하 및 컷백 전개",
            "측면 터치라인 부근에서 수적 우위를 확보한 후 박스 안 중앙으로 꺾어주는 컷백 공격 패턴",
        )

    if has_pocket_third_man:
        return (
            "pocket_third_man",
            "Pocket Play & Third-man Run",
            "포켓(Zone 14) 3자 연계 침투",
            "상대 수비-미드필드 사이 포켓 공간에 볼을 투입 후 쇄도하는 3자 공격수에게 연결하는 침투 패턴",
        )

    if has_halfspace_underlap:
        return (
            "halfspace_underlap",
            "Half-space Underlap & Early Cross",
            "하프스페이스 언더래핑 크로스",
            "윙어가 측면을 벌리고 풀백/메짤라가 하프스페이스로 침투하여 박스로 연결하는 대각선 얼리 크로스 패턴",
        )

    if has_deep_linebreak:
        return (
            "deep_line_break",
            "Deep Line-breaking Penetrative Pass",
            "후방 딥 라인브레이킹 종패스",
            "최후방 빌드업 라인에서 상대 미드필드 블록을 한 번에 관통하여 2선으로 연결하는 다이렉트 롱패스",
        )

    return None


def compute_playbook_summary(
    events: list[dict[str, Any]],
    team_id: int,
) -> list[dict[str, Any]]:
    """경기의 공격 시퀀스를 포제션 체인 단위로 분석하여 5대 시그니처 공격 플레이북을 산출합니다."""
    # 1. 포제션(Possession) 번호 기반 시퀀스 그룹화
    possession_groups: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for ev in events:
        poss_id = ev.get("possession")
        if poss_id is not None:
            possession_groups[poss_id].append(ev)

    # 2. 팀의 유효 공격 시퀀스 체인 추출 (미완료 패스 시 체인 분리)
    sequences: list[list[dict[str, Any]]] = []

    for _poss_id, p_events in sorted(possession_groups.items()):
        current_seq: list[dict[str, Any]] = []

        for ev in p_events:
            ev_team_id = ev.get("team", {}).get("id")
            type_name = ev.get("type", {}).get("name", "")

            if ev_team_id == team_id and type_name in {
                "Pass",
                "Carry",
                "Shot",
                "Dribble",
                "Ball Recovery",
                "Interception",
                "Tackle",
            }:
                if type_name == "Pass":
                    if is_completed_pass(ev):
                        current_seq.append(ev)
                    else:
                        # 패스 실패 시 해당 패스를 끝으로 시퀀스 종료
                        current_seq.append(ev)
                        if len(current_seq) >= 2:
                            sequences.append(current_seq)
                        current_seq = []
                elif type_name == "Shot":
                    current_seq.append(ev)
                    if len(current_seq) >= 2:
                        sequences.append(current_seq)
                    current_seq = []
                else:
                    current_seq.append(ev)
            else:
                if len(current_seq) >= 2:
                    sequences.append(current_seq)
                current_seq = []

        if len(current_seq) >= 2:
            sequences.append(current_seq)

    # 3. 5대 패턴 버킷 초기화
    pattern_buckets: dict[str, dict[str, Any]] = {
        "side_overload_cutback": {
            "pattern_id": "side_overload_cutback",
            "name": "Side Overload & Cutback",
            "name_ko": "측면 과부하 및 컷백 전개",
            "description": "측면 터치라인 부근에서 수적 우위를 확보한 후 박스 안 중앙으로 꺾어주는 컷백 공격 패턴",
            "occurrences": 0,
            "total_xg": 0.0,
            "sequences": [],
        },
        "pocket_third_man": {
            "pattern_id": "pocket_third_man",
            "name": "Pocket Play & Third-man Run",
            "name_ko": "포켓(Zone 14) 3자 연계 침투",
            "description": "상대 수비-미드필드 사이 포켓 공간에 볼을 투입 후 쇄도하는 3자 공격수에게 연결하는 침투 패턴",
            "occurrences": 0,
            "total_xg": 0.0,
            "sequences": [],
        },
        "halfspace_underlap": {
            "pattern_id": "halfspace_underlap",
            "name": "Half-space Underlap & Early Cross",
            "name_ko": "하프스페이스 언더래핑 크로스",
            "description": "윙어가 측면을 벌리고 풀백/메짤라가 하프스페이스로 침투하여 박스로 연결하는 대각선 얼리 크로스 패턴",
            "occurrences": 0,
            "total_xg": 0.0,
            "sequences": [],
        },
        "deep_line_break": {
            "pattern_id": "deep_line_break",
            "name": "Deep Line-breaking Penetrative Pass",
            "name_ko": "후방 딥 라인브레이킹 종패스",
            "description": "최후방 빌드업 라인에서 상대 미드필드 블록을 한 번에 관통하여 2선으로 연결하는 다이렉트 롱패스",
            "occurrences": 0,
            "total_xg": 0.0,
            "sequences": [],
        },
        "high_turnover_strike": {
            "pattern_id": "high_turnover_strike",
            "name": "High-turnover Direct Strike",
            "name_ko": "전방 압박 탈취 속공 슛",
            "description": "상대 진영에서 볼을 즉시 탈취한 후 빠른 템포로 페널티 박스를 직접 타격하는 역습 패턴",
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
        if p_id not in pattern_buckets:
            continue

        bucket = pattern_buckets[p_id]
        bucket["occurrences"] += 1

        seq_xg = 0.0
        for ev in seq:
            if ev.get("type", {}).get("name") == "Shot":
                seq_xg += float(ev.get("shot", {}).get("statsbomb_xg", 0.0) or 0.0)
        bucket["total_xg"] = round(bucket["total_xg"] + seq_xg, 3)

        # 시각화용 실측 이벤트 변환 (최대 5개 시퀀스 보관)
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
                elif type_name in {"Ball Recovery", "Interception", "Tackle"}:
                    seq_event_draws.append(
                        {
                            "type": type_name,
                            "start_x": round(sx, 1),
                            "start_y": round(sy, 1),
                            "end_x": round(sx, 1),
                            "end_y": round(sy, 1),
                            "player_name": p_name,
                            "player_id": p_id_val,
                            "completed": True,
                        }
                    )

            if seq_event_draws:
                bucket["sequences"].append(seq_event_draws)

    # 4. 실측 발생 패턴(occurrences > 0)만 추출하여 발생 횟수 및 xG 기준 정렬
    results = [b for b in pattern_buckets.values() if b["occurrences"] > 0]
    results.sort(key=lambda p: (p["occurrences"], p["total_xg"]), reverse=True)

    # 발생한 패턴이 0개인 경우 전체 5개 패턴 템플릿 반환
    if not results:
        results = list(pattern_buckets.values())

    return results
