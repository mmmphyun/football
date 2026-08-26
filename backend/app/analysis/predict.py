"""단기(+2초) 이동 궤적 외삽 및 물리 예측 엔진 모듈.

최대 스프린트 속도 상한(8.0m/s), 속도 감쇠율, 포메이션 앵커 복원력 및
피치 경계 클램핑을 적용하여 현실적인 미래 위치를 산출합니다.
"""

import math
from typing import Any

from app.config import (
    EXTRAPOLATION_DECAY,
    EXTRAPOLATION_MAX_SPEED,
    EXTRAPOLATION_TIME,
    PITCH_LENGTH,
    PITCH_WIDTH,
)


def calculate_velocity(
    loc_from: tuple[float, float] | list[float],
    loc_to: tuple[float, float] | list[float],
    dt: float,
) -> tuple[float, float]:
    """두 위치와 시간 간격(초)으로부터 속도 벡터 (vx, vy)를 계산합니다."""
    if dt <= 0.001:
        return (0.0, 0.0)

    vx = (float(loc_to[0]) - float(loc_from[0])) / dt
    vy = (float(loc_to[1]) - float(loc_from[1])) / dt

    speed = math.sqrt(vx * vx + vy * vy)
    if speed > EXTRAPOLATION_MAX_SPEED:
        scale = EXTRAPOLATION_MAX_SPEED / speed
        vx *= scale
        vy *= scale

    return (round(vx, 3), round(vy, 3))


def extrapolate_player_position(
    x: float,
    y: float,
    vx: float,
    vy: float,
    dt: float = EXTRAPOLATION_TIME,
    anchor_x: float | None = None,
    anchor_y: float | None = None,
    anchor_pull_weight: float = 0.08,
) -> tuple[float, float]:
    """단일 선수의 현재 위치와 속도 벡터를 기반으로 dt초 후의 예측 위치를 산출합니다."""
    speed = math.sqrt(vx * vx + vy * vy)

    # 1. 최대 속도 제한
    if speed > EXTRAPOLATION_MAX_SPEED:
        scale = EXTRAPOLATION_MAX_SPEED / speed
        vx *= scale
        vy *= scale
        speed = EXTRAPOLATION_MAX_SPEED

    # 2. 속도 감쇠 적용 (선형 외삽 오차 완화)
    decay_factor = max(0.0, 1.0 - EXTRAPOLATION_DECAY * dt)
    eff_vx = vx * decay_factor
    eff_vy = vy * decay_factor

    # 3. 기본 이동 거리
    pred_x = x + eff_vx * dt
    pred_y = y + eff_vy * dt

    # 4. 포메이션 앵커 복원력 적용 (전술적 위치 이탈 방지)
    if anchor_x is not None and anchor_y is not None:
        pull_x = (anchor_x - pred_x) * anchor_pull_weight * dt
        pull_y = (anchor_y - pred_y) * anchor_pull_weight * dt
        pred_x += pull_x
        pred_y += pull_y

    # 5. 피치 경계 클램핑 (0 <= x <= 120, 0 <= y <= 80)
    clamped_x = min(PITCH_LENGTH, max(0.0, pred_x))
    clamped_y = min(PITCH_WIDTH, max(0.0, pred_y))

    return (round(clamped_x, 2), round(clamped_y, 2))


def extrapolate_frame_players(
    players: list[dict[str, Any]],
    dt: float = EXTRAPOLATION_TIME,
) -> list[dict[str, Any]]:
    """프레임 내 모든 선수에 대해 속도 벡터와 +dt초 외삽 위치(pred_x, pred_y)를 계산하여 추가합니다."""
    result: list[dict[str, Any]] = []

    for p in players:
        loc = p.get("location", [60.0, 40.0])
        x = float(loc[0]) if len(loc) >= 1 else 60.0
        y = float(loc[1]) if len(loc) >= 2 else 40.0

        vx = float(p.get("vx", 0.0))
        vy = float(p.get("vy", 0.0))
        anchor_x = p.get("anchor_x")
        anchor_y = p.get("anchor_y")

        pred_x, pred_y = extrapolate_player_position(
            x=x,
            y=y,
            vx=vx,
            vy=vy,
            dt=dt,
            anchor_x=anchor_x,
            anchor_y=anchor_y,
        )

        p_copy = dict(p)
        p_copy["pred_x"] = pred_x
        p_copy["pred_y"] = pred_y
        p_copy["pred_location"] = [pred_x, pred_y]
        result.append(p_copy)

    return result
