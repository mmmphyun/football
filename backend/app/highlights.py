"""골 및 고xG 슈팅 하이라이트 추출 및 포제션 윈도우 클리핑 모듈."""

from typing import Any

from app.analysis.common import event_time
from app.config import (
    MAX_POSSESSION_WINDOW_SEC,
    MIN_HIGHLIGHT_XG,
    POST_WINDOW_SEC,
    PRE_WINDOW_SEC,
)


def is_goal_event(event: dict[str, Any]) -> bool:
    """이벤트가 득점(골 또는 자책골)인지 판별합니다."""
    type_name = event.get("type", {}).get("name", "")
    if type_name == "Shot":
        outcome_name = event.get("shot", {}).get("outcome", {}).get("name", "")
        return outcome_name == "Goal"
    return type_name in ("Own Goal Against", "Own Goal For")


def is_high_xg_shot(event: dict[str, Any], min_xg: float = MIN_HIGHLIGHT_XG) -> bool:
    """이벤트가 지정된 임계값 이상의 고xG 슈팅인지 판별합니다."""
    if event.get("type", {}).get("name") != "Shot":
        return False
    xg = event.get("shot", {}).get("statsbomb_xg", 0.0)
    return float(xg) >= min_xg


def extract_highlights(
    events: list[dict[str, Any]],
    min_xg: float = MIN_HIGHLIGHT_XG,
) -> list[dict[str, Any]]:
    """경기 이벤트 목록에서 골 및 고xG 슈팅 이벤트를 추출하고 전후 포제션 윈도우를 계산합니다.

    각 하이라이트 항목은 시작/종료 이벤트 인덱스와 시간 범위를 포함합니다.
    """
    highlights: list[dict[str, Any]] = []

    # 전체 이벤트의 시간 및 포제션 매핑 준비
    event_times = [event_time(ev) for ev in events]

    for idx, ev in enumerate(events):
        is_goal = is_goal_event(ev)
        high_xg = is_high_xg_shot(ev, min_xg=min_xg)

        if not (is_goal or high_xg):
            continue

        team_info = ev.get("team", {})
        team_id = team_info.get("id", 0)
        team_name = team_info.get("name", "")
        event_type_name = ev.get("type", {}).get("name", "")

        if is_goal:
            hl_type = "Goal" if event_type_name == "Shot" else "Own Goal"
        else:
            hl_type = "High xG Shot"

        xg_val = (
            float(ev.get("shot", {}).get("statsbomb_xg", 0.0)) if event_type_name == "Shot" else 0.0
        )
        t_target = event_times[idx]
        target_period = ev.get("period", 1)
        target_possession = ev.get("possession")

        # 동일 포제션 체인의 시작 시점 탐색 (동일 period 내)
        poss_start_time = t_target
        if target_possession is not None:
            for p_idx in range(idx, -1, -1):
                p_ev = events[p_idx]
                if p_ev.get("period") != target_period:
                    break
                if p_ev.get("possession") == target_possession:
                    poss_start_time = event_times[p_idx]
                else:
                    break

        # 윈도우 시작 시각: 포제션 시작점과 기본 프리 윈도우 중 이전 시점으로 확장하되 최대 제한 적용
        min_allowed_start = max(0.0, t_target - MAX_POSSESSION_WINDOW_SEC)
        candidate_start = min(poss_start_time, t_target - PRE_WINDOW_SEC)
        window_start_sec = max(min_allowed_start, candidate_start)
        window_end_sec = t_target + POST_WINDOW_SEC

        # 윈도우 범위에 포함되는 이벤트 인덱스 탐색 (동일 period 우선)
        start_idx = idx
        for i in range(idx, -1, -1):
            if events[i].get("period") == target_period and event_times[i] >= window_start_sec:
                start_idx = i
            elif events[i].get("period") != target_period or event_times[i] < window_start_sec:
                break

        end_idx = idx
        for i in range(idx, len(events)):
            if events[i].get("period") == target_period and event_times[i] <= window_end_sec:
                end_idx = i
            elif events[i].get("period") != target_period or event_times[i] > window_end_sec:
                break

        highlights.append(
            {
                "team_id": team_id,
                "team_name": team_name,
                "type": hl_type,
                "minute": ev.get("minute", 0),
                "second": ev.get("second", 0),
                "xg": round(xg_val, 4),
                "start_event": start_idx,
                "end_event": end_idx,
                "event_index": idx,
                "event_id": ev.get("id", ""),
                "window_start_sec": round(window_start_sec, 2),
                "window_end_sec": round(window_end_sec, 2),
                "period": target_period,
            }
        )

    return highlights
