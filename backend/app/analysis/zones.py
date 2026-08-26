"""12x8 바둑판 피치 구역 점유율(Zones Occupancy) 분석 모듈.

StatsBomb 360 프레임 및 이벤트 위치 데이터를 기반으로 10m x 10m 구역별 점유율을 산출합니다.
"""

from typing import Any

from app.analysis.common import point_in_polygon
from app.config import (
    PITCH_LENGTH,
    PITCH_WIDTH,
    ZONE_CELL_HEIGHT,
    ZONE_CELL_WIDTH,
    ZONES_X,
    ZONES_Y,
)


def _get_zone_indices(x: float, y: float) -> tuple[int, int]:
    """좌표 (x, y)를 12x8 그리드의 (col, row) 인덱스로 변환합니다."""
    col = min(ZONES_X - 1, max(0, int(x / ZONE_CELL_WIDTH)))
    row = min(ZONES_Y - 1, max(0, int(y / ZONE_CELL_HEIGHT)))
    return col, row


def _normalize_grid(grid: list[list[float]]) -> list[list[float]]:
    """그리드 내 전체 합이 1.0이 되도록 정규화합니다. (합이 0이면 균등 분배하지 않고 0 반환)"""
    total = sum(sum(row) for row in grid)
    if total <= 0:
        return [[0.0 for _ in range(ZONES_X)] for _ in range(ZONES_Y)]
    return [[round(val / total, 4) for val in row] for row in grid]


def compute_zones_summary(
    events: list[dict[str, Any]],
    team_id: int,
    three_sixty_frames: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """12x8 구역별 전체, 볼 소유 시, 미소유 시 점유율 그리드를 계산합니다.

    StatsBomb 360 프레임이 존재하는 경우 실제 선수 위치 및 시야각을 우선 반영하고,
    미제공 시 일반 이벤트 위치를 기반으로 밀도를 산출합니다.
    """
    event_map: dict[str, dict[str, Any]] = {}
    for ev in events:
        ev_id = ev.get("id")
        if ev_id:
            event_map[ev_id] = ev

    # 12x8 (행=Y 8, 열=X 12)
    overall_grid = [[0.0 for _ in range(ZONES_X)] for _ in range(ZONES_Y)]
    in_poss_grid = [[0.0 for _ in range(ZONES_X)] for _ in range(ZONES_Y)]
    out_poss_grid = [[0.0 for _ in range(ZONES_X)] for _ in range(ZONES_Y)]

    has_360_data = False

    if three_sixty_frames:
        for frame in three_sixty_frames:
            ev_uuid = frame.get("event_uuid")
            matched_ev = event_map.get(ev_uuid)
            if not matched_ev:
                continue

            has_360_data = True
            ev_team_id = matched_ev.get("team", {}).get("id")
            poss_team_id = matched_ev.get("possession_team", {}).get("id")
            visible_area = frame.get("visible_area", [])
            freeze_frame = frame.get("freeze_frame", [])

            for player_frame in freeze_frame:
                loc = player_frame.get("location")
                if not loc or len(loc) < 2:
                    continue

                px, py = float(loc[0]), float(loc[1])
                # 피치 경계 체크
                if not (0.0 <= px <= PITCH_LENGTH and 0.0 <= py <= PITCH_WIDTH):
                    continue

                # visible_area 필터링
                if visible_area and not point_in_polygon(px, py, visible_area):
                    continue

                teammate_flag = player_frame.get("teammate", False)
                # 프레임의 선수가 타깃 team_id 소속인지 판정
                is_our_player = teammate_flag if ev_team_id == team_id else (not teammate_flag)

                if is_our_player:
                    col, row = _get_zone_indices(px, py)
                    overall_grid[row][col] += 1.0
                    if poss_team_id == team_id:
                        in_poss_grid[row][col] += 1.0
                    else:
                        out_poss_grid[row][col] += 1.0

    # 360 데이터가 부족하거나 없는 경우 이벤트 위치 기반 fallback
    if not has_360_data:
        for ev in events:
            ev_team_id = ev.get("team", {}).get("id")
            if ev_team_id != team_id:
                continue

            poss_team_id = ev.get("possession_team", {}).get("id")
            loc = ev.get("location")
            if loc and len(loc) >= 2:
                col, row = _get_zone_indices(float(loc[0]), float(loc[1]))
                overall_grid[row][col] += 1.0
                if poss_team_id == team_id:
                    in_poss_grid[row][col] += 1.0
                else:
                    out_poss_grid[row][col] += 1.0

            # 패스나 캐리의 종점도 추가 반영
            pass_end = ev.get("pass", {}).get("end_location")
            if pass_end and len(pass_end) >= 2:
                col, row = _get_zone_indices(float(pass_end[0]), float(pass_end[1]))
                overall_grid[row][col] += 0.5
                if poss_team_id == team_id:
                    in_poss_grid[row][col] += 0.5
                else:
                    out_poss_grid[row][col] += 0.5

    norm_overall = _normalize_grid(overall_grid)
    norm_in_poss = _normalize_grid(in_poss_grid)
    norm_out_poss = _normalize_grid(out_poss_grid)

    total_samples = int(sum(sum(row) for row in overall_grid))
    cells: list[dict[str, Any]] = []
    for r_idx in range(ZONES_Y):
        for c_idx in range(ZONES_X):
            cells.append(
                {
                    "zone_x": c_idx,
                    "zone_y": r_idx,
                    "count": int(overall_grid[r_idx][c_idx]),
                    "ratio": norm_overall[r_idx][c_idx],
                }
            )

    return {
        "team_id": team_id,
        "grid_cols": ZONES_X,
        "grid_rows": ZONES_Y,
        "zones_x": ZONES_X,
        "zones_y": ZONES_Y,
        "cell_width": ZONE_CELL_WIDTH,
        "cell_height": ZONE_CELL_HEIGHT,
        "total_samples": total_samples,
        "cells": cells,
        "has_360": has_360_data,
        "overall_grid": norm_overall,
        "in_possession_grid": norm_in_poss,
        "out_of_possession_grid": norm_out_poss,
    }

