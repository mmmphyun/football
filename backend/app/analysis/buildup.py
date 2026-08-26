"""빌드업 및 전진 전개(Buildup & Progression) 분석 모듈.

3분할 진영별 빌드업 시작 위치, 전진 패스 및 캐리 비율, 포제션 시퀀스 특성을 산출합니다.
"""

from collections import defaultdict
from typing import Any

from app.config import DEFENSIVE_THIRD_X, MIDDLE_THIRD_X


def compute_buildup_summary(
    events: list[dict[str, Any]],
    team_id: int,
) -> dict[str, Any]:
    """팀의 빌드업 시작 지점 분포, 전진 패스/캐리 통계 및 포제션 체인 지표를 산출합니다."""
    # 포제션 시퀀스별 이벤트 그룹화
    possession_events: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for ev in events:
        poss_num = ev.get("possession")
        if poss_num is not None:
            possession_events[poss_num].append(ev)

    defensive_third_starts = 0
    middle_third_starts = 0
    attacking_third_starts = 0
    team_possession_count = 0
    total_possession_passes = 0
    long_buildup_sequences = 0  # 패스 4회 이상 연속 빌드업 시퀀스

    for _poss_num, p_events in possession_events.items():
        if not p_events:
            continue

        # 해당 포제션의 주도 팀 판별
        first_ev = p_events[0]
        poss_team_id = first_ev.get("possession_team", {}).get("id")
        if poss_team_id != team_id:
            continue

        team_possession_count += 1
        loc = first_ev.get("location")
        start_x = float(loc[0]) if loc and len(loc) >= 1 else 40.0

        if start_x < DEFENSIVE_THIRD_X:
            defensive_third_starts += 1
        elif start_x < MIDDLE_THIRD_X:
            middle_third_starts += 1
        else:
            attacking_third_starts += 1

        seq_passes = sum(
            1
            for ev in p_events
            if ev.get("type", {}).get("name") == "Pass" and ev.get("team", {}).get("id") == team_id
        )
        total_possession_passes += seq_passes
        if seq_passes >= 4:
            long_buildup_sequences += 1

    # 전진 패스 및 전진 캐리 집계
    total_passes = 0
    prog_passes = 0
    total_carries = 0
    prog_carries = 0

    for ev in events:
        if ev.get("team", {}).get("id") != team_id:
            continue

        type_name = ev.get("type", {}).get("name")
        loc = ev.get("location")

        if type_name == "Pass":
            total_passes += 1
            end_loc = ev.get("pass", {}).get("end_location")
            if (
                loc
                and end_loc
                and len(loc) >= 2
                and len(end_loc) >= 2
                and float(end_loc[0]) - float(loc[0]) >= 10.0
            ):
                prog_passes += 1

        elif type_name == "Carry":
            total_carries += 1
            end_loc = ev.get("carry", {}).get("end_location")
            if (
                loc
                and end_loc
                and len(loc) >= 2
                and len(end_loc) >= 2
                and float(end_loc[0]) - float(loc[0]) >= 5.0
            ):
                prog_carries += 1

    avg_passes_per_possession = (
        round(total_possession_passes / team_possession_count, 2)
        if team_possession_count > 0
        else 0.0
    )

    def_ratio = (
        round(defensive_third_starts / team_possession_count, 3)
        if team_possession_count > 0
        else 0.0
    )
    mid_ratio = (
        round(middle_third_starts / team_possession_count, 3) if team_possession_count > 0 else 0.0
    )
    att_ratio = (
        round(attacking_third_starts / team_possession_count, 3)
        if team_possession_count > 0
        else 0.0
    )
    prog_pass_ratio = round(prog_passes / total_passes, 3) if total_passes > 0 else 0.0
    prog_carry_ratio = round(prog_carries / total_carries, 3) if total_carries > 0 else 0.0

    return {
        "team_id": team_id,
        "total_possessions": team_possession_count,
        "avg_passes_per_possession": avg_passes_per_possession,
        "long_buildup_sequences": long_buildup_sequences,
        "defensive_third_pct": round(def_ratio * 100, 1),
        "middle_third_pct": round(mid_ratio * 100, 1),
        "attacking_third_pct": round(att_ratio * 100, 1),
        "progressive_pass_ratio": round(prog_pass_ratio * 100, 1),
        "progressive_carry_ratio": round(prog_carry_ratio * 100, 1),
        "buildup_start_distribution": {
            "defensive_third": defensive_third_starts,
            "middle_third": middle_third_starts,
            "attacking_third": attacking_third_starts,
            "defensive_third_ratio": def_ratio,
            "middle_third_ratio": mid_ratio,
            "attacking_third_ratio": att_ratio,
        },
        "progression": {
            "total_passes": total_passes,
            "progressive_passes": prog_passes,
            "progressive_pass_ratio": prog_pass_ratio,
            "total_carries": total_carries,
            "progressive_carries": prog_carries,
            "progressive_carry_ratio": prog_carry_ratio,
        },
    }
