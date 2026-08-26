"""공수 전환(Transitions) 속도 및 속공/지공 분석 모듈.

공 회수(Ball Recovery, Interception, Tackle) 후 8초 이내 전개 속도,
속공(Fast Transition) 및 지공(Slow Transition) 비율을 산출합니다.
"""

from typing import Any

from app.analysis.common import event_time
from app.config import ATTACKING_THIRD_X

# 공 회수 및 전환 기점 이벤트
TURNOVER_RECOVERY_TYPES = {
    "Ball Recovery",
    "Interception",
    "Tackle",
}
TRANSITION_WINDOW_SEC = 8.0


def compute_transitions_summary(
    events: list[dict[str, Any]],
    team_id: int,
) -> dict[str, Any]:
    """공 회수 후 8초 이내의 속공/지공 전환 지표 및 평균 전진 속도를 산출합니다."""
    sorted_events = sorted(events, key=event_time)

    total_recoveries = 0
    fast_transitions = 0
    slow_transitions = 0
    transition_speeds: list[float] = []
    transition_durations: list[float] = []

    n = len(sorted_events)
    for i in range(n):
        ev = sorted_events[i]
        ev_team_id = ev.get("team", {}).get("id")
        if ev_team_id != team_id:
            continue

        type_name = ev.get("type", {}).get("name", "")
        if type_name not in TURNOVER_RECOVERY_TYPES:
            continue

        total_recoveries += 1
        t_start = event_time(ev)
        loc_start = ev.get("location")
        start_x = float(loc_start[0]) if loc_start and len(loc_start) >= 1 else 40.0

        reached_final_third = False
        attempted_shot = False
        max_end_x = start_x
        last_t = t_start

        # 회수 후 8초 이내 시퀀스 추적
        for j in range(i + 1, n):
            next_ev = sorted_events[j]
            t_next = event_time(next_ev)
            if t_next - t_start > TRANSITION_WINDOW_SEC:
                break

            if next_ev.get("team", {}).get("id") != team_id:
                # 8초 이내에 상대에게 다시 공을 빼앗긴 경우
                break

            next_type = next_ev.get("type", {}).get("name", "")
            next_loc = next_ev.get("location")
            if next_loc and len(next_loc) >= 1:
                cur_x = float(next_loc[0])
                if cur_x > max_end_x:
                    max_end_x = cur_x
                if cur_x >= ATTACKING_THIRD_X:
                    reached_final_third = True

            # 패스나 캐리의 종점 확인
            pass_end = next_ev.get("pass", {}).get("end_location")
            if pass_end and len(pass_end) >= 1:
                end_x = float(pass_end[0])
                if end_x > max_end_x:
                    max_end_x = end_x
                if end_x >= ATTACKING_THIRD_X:
                    reached_final_third = True

            carry_end = next_ev.get("carry", {}).get("end_location")
            if carry_end and len(carry_end) >= 1:
                end_x = float(carry_end[0])
                if end_x > max_end_x:
                    max_end_x = end_x
                if end_x >= ATTACKING_THIRD_X:
                    reached_final_third = True

            if next_type == "Shot":
                attempted_shot = True
                reached_final_third = True

            last_t = t_next

        delta_x = max(0.0, max_end_x - start_x)
        elapsed_sec = max(0.5, last_t - t_start)
        speed = delta_x / elapsed_sec
        transition_speeds.append(speed)

        # 8초 내 파이널 서드 진입 또는 슈팅 시도 또는 빠른 전진 속도(>= 4.0m/s)인 경우 속공 판정
        if reached_final_third or attempted_shot or speed >= 4.0:
            fast_transitions += 1

        if reached_final_third or attempted_shot:
            transition_durations.append(last_t - t_start)
        else:
            slow_transitions += 1

    avg_speed = (
        round(sum(transition_speeds) / len(transition_speeds), 2) if transition_speeds else 0.0
    )
    avg_sec = (
        round(sum(transition_durations) / len(transition_durations), 2)
        if transition_durations
        else None
    )
    fast_ratio = round(fast_transitions / total_recoveries, 3) if total_recoveries > 0 else 0.0

    return {
        "team_id": team_id,
        "turnovers_won": total_recoveries,
        "fast_transitions_to_att_third": fast_transitions,
        "avg_transition_sec": avg_sec,
        "total_recoveries": total_recoveries,
        "fast_transitions": fast_transitions,
        "slow_transitions": slow_transitions,
        "fast_transition_ratio": fast_ratio,
        "avg_transition_speed_mps": avg_speed,
    }
