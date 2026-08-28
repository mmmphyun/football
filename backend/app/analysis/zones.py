"""12x8 바둑판 피치 구역 점유율(Zones Occupancy) 분석 모듈.

StatsBomb 원시 이벤트 스트림 및 360 프레임 데이터를 기반으로 10m x 10m 구역별 점유율을 정밀 산출합니다.
"""

from typing import Any

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
    """12x8 구역별 전체, 볼 소유 시, 미소유 시 점유율 그리드를 계산합니다."""
    # 12x8 (행=Y 8, 열=X 12)
    overall_grid = [[0.0 for _ in range(ZONES_X)] for _ in range(ZONES_Y)]
    in_poss_grid = [[0.0 for _ in range(ZONES_X)] for _ in range(ZONES_Y)]
    out_poss_grid = [[0.0 for _ in range(ZONES_X)] for _ in range(ZONES_Y)]

    # 1. 팀의 자체 이벤트 기반 실측 점유 집계 (0 -> 120 방향)
    for ev in events:
        ev_team_id = ev.get("team", {}).get("id")
        if ev_team_id != team_id:
            continue

        poss_team_id = ev.get("possession_team", {}).get("id")
        loc = ev.get("location")
        if loc and len(loc) >= 2:
            lx, ly = float(loc[0]), float(loc[1])
            if 0.0 <= lx <= PITCH_LENGTH and 0.0 <= ly <= PITCH_WIDTH:
                col, row = _get_zone_indices(lx, ly)
                overall_grid[row][col] += 1.0
                if poss_team_id == team_id:
                    in_poss_grid[row][col] += 1.0
                else:
                    out_poss_grid[row][col] += 1.0

        # 패스나 캐리의 도달 종점도 공간 점유로 추가 반영 (0.5 가중치)
        pass_end = ev.get("pass", {}).get("end_location")
        if pass_end and len(pass_end) >= 2:
            ex, ey = float(pass_end[0]), float(pass_end[1])
            if 0.0 <= ex <= PITCH_LENGTH and 0.0 <= ey <= PITCH_WIDTH:
                col, row = _get_zone_indices(ex, ey)
                overall_grid[row][col] += 0.5
                if poss_team_id == team_id:
                    in_poss_grid[row][col] += 0.5
                else:
                    out_poss_grid[row][col] += 0.5

        carry_end = ev.get("carry", {}).get("end_location")
        if carry_end and len(carry_end) >= 2:
            cx, cy = float(carry_end[0]), float(carry_end[1])
            if 0.0 <= cx <= PITCH_LENGTH and 0.0 <= cy <= PITCH_WIDTH:
                col, row = _get_zone_indices(cx, cy)
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
        "has_360": bool(three_sixty_frames and len(three_sixty_frames) > 0),
        "overall_grid": norm_overall,
        "in_possession_grid": norm_in_poss,
        "out_of_possession_grid": norm_out_poss,
    }
