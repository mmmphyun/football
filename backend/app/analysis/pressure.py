"""압박 및 PPDA (Passes Allowed Per Defensive Action) 분석 모듈.

분당 압박 횟수, 상대 진영(x >= 40) PPDA 지표 및 3분할 진영별 수비 액션 분포를 산출합니다.
"""

from typing import Any

from app.analysis.common import get_match_duration_min, get_opponent_team_id
from app.config import DEFENSIVE_THIRD_X, MIDDLE_THIRD_X

# PPDA 계산에 포함되는 수비 액션 이벤트 타입
DEFENSIVE_ACTION_TYPES = {
    "Pressure",
    "Tackle",
    "Interception",
    "Block",
    "Foul Committed",
    "Clearance",
}


def compute_pressure_summary(
    events: list[dict[str, Any]],
    team_id: int,
) -> dict[str, Any]:
    """팀의 압박 강도, 분당 압박 횟수, 상대 진영 PPDA 및 구역별 수비 액션 지표를 산출합니다."""
    duration_min = get_match_duration_min(events)
    opponent_id = get_opponent_team_id(team_id, events)

    total_pressures = 0
    defensive_third_pressures = 0
    middle_third_pressures = 0
    attacking_third_pressures = 0

    total_defensive_actions = 0
    high_press_defensive_actions = 0  # x >= 40 (미들 서드 + 어태킹 서드)에서의 수비 액션
    pressure_events: list[dict[str, Any]] = []

    for ev in events:
        ev_team_id = ev.get("team", {}).get("id")
        if ev_team_id != team_id:
            continue

        type_name = ev.get("type", {}).get("name", "")
        loc = ev.get("location")
        x = float(loc[0]) if loc and len(loc) >= 1 else 60.0
        y = float(loc[1]) if loc and len(loc) >= 2 else 40.0

        if type_name == "Pressure":
            total_pressures += 1
            if x < DEFENSIVE_THIRD_X:
                defensive_third_pressures += 1
            elif x < MIDDLE_THIRD_X:
                middle_third_pressures += 1
            else:
                attacking_third_pressures += 1

        if type_name in DEFENSIVE_ACTION_TYPES:
            total_defensive_actions += 1
            is_high_press = x >= DEFENSIVE_THIRD_X
            if is_high_press:
                high_press_defensive_actions += 1

            pressure_events.append(
                {
                    "x": round(x, 1),
                    "y": round(y, 1),
                    "type": type_name,
                    "is_high_press": is_high_press,
                }
            )

    # 상대팀의 백 60% 진영(상대팀 기준 x < 80)에서의 패스 시도 횟수
    opponent_passes_in_buildup = 0
    if opponent_id is not None:
        for ev in events:
            if ev.get("team", {}).get("id") != opponent_id:
                continue
            if ev.get("type", {}).get("name") != "Pass":
                continue

            loc = ev.get("location")
            if loc and len(loc) >= 1 and float(loc[0]) < MIDDLE_THIRD_X:
                opponent_passes_in_buildup += 1

    # PPDA = 상대팀 패스 수 / 우리팀 전방 수비 액션 수
    if high_press_defensive_actions > 0:
        ppda = round(opponent_passes_in_buildup / high_press_defensive_actions, 2)
    else:
        ppda = 0.0

    pressures_per_min = round(total_pressures / duration_min, 2) if duration_min > 0 else 0.0

    return {
        "team_id": team_id,
        "duration_min": duration_min,
        "total_pressures": total_pressures,
        "total_pressure_events": total_pressures,
        "pressures_per_min": pressures_per_min,
        "ppda": ppda,
        "high_press_events": high_press_defensive_actions,
        "high_press_defensive_actions": high_press_defensive_actions,
        "turnovers_forced_att_third": attacking_third_pressures,
        "opponent_passes_in_buildup": opponent_passes_in_buildup,
        "pressures_by_third": {
            "defensive_third": defensive_third_pressures,
            "middle_third": middle_third_pressures,
            "attacking_third": attacking_third_pressures,
        },
        "pressure_events": pressure_events[:100],
    }

