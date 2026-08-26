"""전술 분석 엔진 공통 유틸리티 및 도메인 헬퍼 모듈.

StatsBomb 좌표계($x=0 \\to 120, y=0 \\to 80$) 및 이벤트 데이터 구조를 지원합니다.
"""

from typing import Any


def event_time(event: dict[str, Any]) -> float:
    """이벤트 발생 시간을 경기 시작 기준 누적 초(second) 단위로 반환합니다.

    (period - 1) * 3600과 같은 임의의 시간 오프셋은 가산하지 않습니다.
    """
    minute = event.get("minute", 0)
    second = event.get("second", 0)
    return float(minute * 60 + second)


def get_match_duration_min(events: list[dict[str, Any]]) -> float:
    """경기 이벤트 목록에서 실제 최대 누적 경기 시간(분)을 산출합니다."""
    if not events:
        return 90.0
    max_min = max((event.get("minute", 0) for event in events), default=90)
    return float(max(90, max_min))


def is_completed_pass(event: dict[str, Any]) -> bool:
    """성공한 일반 패스인지 판별합니다.

    StatsBomb 스펙에서 pass.outcome이 None인 경우가 성공한 패스입니다.
    (Incomplete, Out, Pass Offside 등은 실패 처리)
    """
    if event.get("type", {}).get("name") != "Pass":
        return False
    pass_data = event.get("pass", {})
    return pass_data.get("outcome") is None


def get_team_ids(events: list[dict[str, Any]]) -> list[int]:
    """경기 이벤트 목록에서 두 팀의 고유 team_id를 추출합니다."""
    seen_ids: list[int] = []
    for ev in events:
        t_id = ev.get("team", {}).get("id")
        if t_id is not None and t_id not in seen_ids:
            seen_ids.append(t_id)
            if len(seen_ids) == 2:
                break
    return seen_ids


def get_opponent_team_id(team_id: int, events: list[dict[str, Any]]) -> int | None:
    """주어진 team_id의 상대팀 team_id를 반환합니다."""
    for t_id in get_team_ids(events):
        if t_id != team_id:
            return t_id
    return None


def point_in_polygon(x: float, y: float, polygon_coords: list[float]) -> bool:
    """StatsBomb 360의 [x1, y1, x2, y2, ...] 형식 폴리곤 내에 점 (x, y)가 포함되는지 검사합니다.

    Ray Casting (Even-Odd) 알고리즘을 사용합니다.
    """
    if not polygon_coords or len(polygon_coords) < 6:
        return True  # visible_area 정보가 없는 경우 전체 영역 포함으로 간주

    vertices: list[tuple[float, float]] = []
    for i in range(0, len(polygon_coords) - 1, 2):
        vertices.append((polygon_coords[i], polygon_coords[i + 1]))

    n = len(vertices)
    inside = False

    p1x, p1y = vertices[0]
    for i in range(n + 1):
        p2x, p2y = vertices[i % n]
        if min(p1y, p2y) < y <= max(p1y, p2y) and x <= max(p1x, p2x):
            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x if p1y != p2y else p1x
            if p1x == p2x or x <= xinters:
                inside = not inside
        p1x, p1y = p2x, p2y

    return inside


def build_lineup_maps(lineups: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    """lineups.json 데이터로부터 팀별 선수 맵, 선발 명단, 등번호 및 포지션 앵커 정보를 구성합니다."""
    result: dict[int, dict[str, Any]] = {}
    for team_entry in lineups:
        team_id = team_entry.get("team_id")
        if team_id is None:
            continue

        team_name = team_entry.get("team_name", "")
        players_map: dict[int, dict[str, Any]] = {}
        starting_xi_ids: list[int] = []

        for p in team_entry.get("lineup", []):
            p_id = p.get("player_id")
            if p_id is None:
                continue

            positions = p.get("positions", [])
            is_starter = any(pos.get("start_reason") == "Starting XI" for pos in positions)
            if is_starter:
                starting_xi_ids.append(p_id)

            primary_position = positions[0].get("position") if positions else None
            primary_position_id = positions[0].get("position_id") if positions else None

            players_map[p_id] = {
                "player_id": p_id,
                "player_name": p.get("player_name", ""),
                "player_nickname": p.get("player_nickname"),
                "jersey_number": p.get("jersey_number"),
                "is_starter": is_starter,
                "primary_position": primary_position,
                "primary_position_id": primary_position_id,
                "positions": positions,
            }

        result[team_id] = {
            "team_id": team_id,
            "team_name": team_name,
            "players": players_map,
            "starting_xi": starting_xi_ids,
        }
    return result
