"""전술 분석 엔진(Analysis Engine) 패키지.

3대 국면 포메이션, 시그니처 플레이북, 압박 트랩, 전술 타임라인, 패스 네트워크,
점유 구역 및 공수 전환 등 10종 인터랙티브 전술 분석 모듈을 통합 관리합니다.
"""

from typing import Any

from app.analysis.buildup import compute_buildup_summary
from app.analysis.common import (
    build_lineup_maps,
    event_time,
    get_match_duration_min,
    get_opponent_team_id,
    get_team_ids,
    is_completed_pass,
    point_in_polygon,
)
from app.analysis.formation import POSITION_ANCHORS, compute_formation_summary, get_position_anchor
from app.analysis.passes import compute_pass_network
from app.analysis.playbook import compute_playbook_summary
from app.analysis.predict import (
    calculate_velocity,
    extrapolate_frame_players,
    extrapolate_player_position,
)
from app.analysis.pressure import compute_pressure_summary
from app.analysis.timeline import compute_timeline_summary
from app.analysis.transitions import compute_transitions_summary
from app.analysis.zones import compute_zones_summary

__all__ = [
    "POSITION_ANCHORS",
    "analyze_match",
    "build_lineup_maps",
    "calculate_velocity",
    "compute_buildup_summary",
    "compute_formation_summary",
    "compute_pass_network",
    "compute_playbook_summary",
    "compute_pressure_summary",
    "compute_timeline_summary",
    "compute_transitions_summary",
    "compute_zones_summary",
    "event_time",
    "extrapolate_frame_players",
    "extrapolate_player_position",
    "get_match_duration_min",
    "get_opponent_team_id",
    "get_position_anchor",
    "get_team_ids",
    "is_completed_pass",
    "point_in_polygon",
]


def analyze_match(
    events: list[dict[str, Any]],
    lineups: list[dict[str, Any]],
    three_sixty_frames: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """경기 전체 데이터(이벤트, 라인업, 360)에 대해 전술 지표를 양 팀별로 산출하여 통합 요약을 생성합니다."""
    team_ids = get_team_ids(events)
    lineup_maps = build_lineup_maps(lineups)
    match_duration = get_match_duration_min(events)

    teams_summary: dict[int, dict[str, Any]] = {}

    for t_id in team_ids:
        team_name = lineup_maps.get(t_id, {}).get("team_name", str(t_id))
        formation_data = compute_formation_summary(
            events, lineups, t_id, three_sixty_frames=three_sixty_frames
        )
        zones_data = compute_zones_summary(events, t_id, three_sixty_frames)
        passes_data = compute_pass_network(events, lineups, t_id)
        pressure_data = compute_pressure_summary(events, t_id)
        playbook_data = compute_playbook_summary(events, t_id)
        timeline_data = compute_timeline_summary(events, t_id, lineups=lineups)
        buildup_data = compute_buildup_summary(events, t_id)
        transitions_data = compute_transitions_summary(events, t_id)

        teams_summary[t_id] = {
            "team_id": t_id,
            "team_name": team_name,
            "formation": formation_data,
            "zones": zones_data,
            "passes": passes_data,
            "pressure": pressure_data,
            "playbook": playbook_data,
            "timeline": timeline_data,
            "buildup": buildup_data,
            "transitions": transitions_data,
        }

    return {
        "match_duration_min": match_duration,
        "team_ids": team_ids,
        "teams": teams_summary,
    }
