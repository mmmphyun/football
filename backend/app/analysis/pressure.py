"""압박 및 PPDA (Passes Allowed Per Defensive Action) 분석 모듈.

StatsBomb 표준 PPDA 공식(상대팀 자진영 40% 이하 패스 수 / 수비팀 상대 진영 60% 이상 수비 액션 수) 및
실측 다인 압박 트랩 핫스팟 클러스터링을 산출합니다.
"""

from typing import Any

from app.analysis.common import event_time, get_match_duration_min, get_opponent_team_id
from app.config import (
    DEFENSIVE_THIRD_X,
    MIDDLE_THIRD_X,
    PRESSURE_TRAP_MIN_PLAYERS,
    PRESSURE_TRAP_TIME_WINDOW_SEC,
)

# PPDA 계산에 포함되는 StatsBomb 표준 전방 수비 액션
PPDA_DEFENSIVE_ACTIONS = {
    "Pressure",
    "Tackle",
    "Interception",
    "Foul Committed",
    "Block",
}

# StatsBomb 표준 PPDA 피치 분할 기준선 (40% vs 60%, 120m * 0.4 = 48.0m)
PPDA_PITCH_THRESHOLD_X: float = 48.0


def _classify_trap_zone(x: float, y: float) -> str:
    """압박 좌표 기반 트랩 구역 이름을 판별합니다."""
    if y <= 20.0:
        return "Left Touchline Trap"
    elif y >= 60.0:
        return "Right Touchline Trap"
    elif x >= 80.0:
        return "High Final-Third Press Trap"
    elif x >= 45.0:
        return "Midfield Half-Space Trap"
    return "Low Defensive Block Trap"


def compute_pressure_summary(
    events: list[dict[str, Any]],
    team_id: int,
) -> dict[str, Any]:
    """팀의 압박 강도, 분당 압박 횟수, 표준 PPDA 및 실측 압박 트랩 핫스팟을 산출합니다."""
    duration_min = get_match_duration_min(events)
    opponent_id = get_opponent_team_id(team_id, events)

    total_pressures = 0
    defensive_third_pressures = 0
    middle_third_pressures = 0
    attacking_third_pressures = 0

    total_defensive_actions = 0
    high_press_defensive_actions = 0  # x >= 48.0 (상대 진영 60%)에서의 수비 액션
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

        if type_name in PPDA_DEFENSIVE_ACTIONS:
            total_defensive_actions += 1
            is_high_press = x >= PPDA_PITCH_THRESHOLD_X
            if is_high_press:
                high_press_defensive_actions += 1

            if type_name == "Pressure":
                pressure_events.append(
                    {
                        "x": round(x, 1),
                        "y": round(y, 1),
                        "type": type_name,
                        "is_high_press": is_high_press,
                        "minute": ev.get("minute", 0),
                        "second": ev.get("second", 0),
                    }
                )

    # 상대팀의 자진영 40% (상대팀 기준 x <= 48.0)에서의 패스 시도 횟수
    opponent_passes_in_buildup = 0
    if opponent_id is not None:
        for ev in events:
            if ev.get("team", {}).get("id") != opponent_id:
                continue
            if ev.get("type", {}).get("name") != "Pass":
                continue

            loc = ev.get("location")
            if loc and len(loc) >= 1 and float(loc[0]) <= PPDA_PITCH_THRESHOLD_X:
                opponent_passes_in_buildup += 1

    # StatsBomb 표준 PPDA = 상대팀 수비 진영 40% 패스 수 / 우리팀 전방 수비 액션 수
    if high_press_defensive_actions > 0:
        ppda = round(opponent_passes_in_buildup / high_press_defensive_actions, 2)
    else:
        ppda = 0.0

    pressures_per_min = round(total_pressures / duration_min, 2) if duration_min > 0 else 0.0

    # 압박 트랩 핫스팟 탐지 (3초 이내 2인 이상 압박 + 턴오버 유발 실측 구역)
    trap_clusters: dict[str, dict[str, Any]] = {}
    n_events = len(events)

    for i in range(n_events):
        ev1 = events[i]
        if ev1.get("team", {}).get("id") != team_id:
            continue
        if ev1.get("type", {}).get("name") != "Pressure":
            continue

        loc1 = ev1.get("location")
        if not loc1 or len(loc1) < 2:
            continue

        t1 = event_time(ev1)
        p1 = ev1.get("player", {}).get("id")
        pressuring_players = {p1} if p1 else set()
        turnover_forced = False
        trap_x, trap_y = float(loc1[0]), float(loc1[1])

        # 3초 윈도우 내 후속 이벤트 탐색
        for j in range(i + 1, min(i + 8, n_events)):
            ev2 = events[j]
            t2 = event_time(ev2)
            if t2 - t1 > PRESSURE_TRAP_TIME_WINDOW_SEC:
                break

            t2_team = ev2.get("team", {}).get("id")
            t2_type = ev2.get("type", {}).get("name", "")

            if t2_team == team_id and t2_type in PPDA_DEFENSIVE_ACTIONS:
                p2 = ev2.get("player", {}).get("id")
                if p2:
                    pressuring_players.add(p2)

            # 상대팀의 실책(Dispossessed/Miscontrol/Pass 미스) 또는 우리팀의 탈취(Recovery/Interception/Tackle)
            if (t2_team != team_id and t2_type in {"Dispossessed", "Miscontrol"}) or (
                t2_team == team_id and t2_type in {"Ball Recovery", "Interception", "Tackle"}
            ):
                turnover_forced = True

        if len(pressuring_players) >= PRESSURE_TRAP_MIN_PLAYERS and turnover_forced:
            zone_name = _classify_trap_zone(trap_x, trap_y)
            if zone_name not in trap_clusters:
                trap_clusters[zone_name] = {
                    "name": zone_name,
                    "count": 0,
                    "xs": [],
                    "ys": [],
                }
            trap_clusters[zone_name]["count"] += 1
            trap_clusters[zone_name]["xs"].append(trap_x)
            trap_clusters[zone_name]["ys"].append(trap_y)

    pressure_traps: list[dict[str, Any]] = []
    for zone_name, info in sorted(
        trap_clusters.items(), key=lambda item: item[1]["count"], reverse=True
    ):
        avg_x = round(sum(info["xs"]) / len(info["xs"]), 1)
        avg_y = round(sum(info["ys"]) / len(info["ys"]), 1)
        pressure_traps.append(
            {
                "zone": zone_name,
                "count": info["count"],
                "x": avg_x,
                "y": avg_y,
                "intensity": min(1.0, round(info["count"] / max(1, total_pressures * 0.1), 2)),
            }
        )

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
        "pressure_traps": pressure_traps,
        "pressure_events": pressure_events[:100],
    }
