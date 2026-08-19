"""Deterministic short-term movement extrapolation (shared with the frontend)."""

import math
from typing import Any

from .. import config


def extrapolate(
    pos: tuple[float, float],
    vel: tuple[float, float],
    max_speed: float,
    anchor: tuple[float, float] | None,
    t_sec: float,
    pull: float = config.PREDICT_PULL,
    bounds: tuple[float, float, float, float] = (0.0, config.PITCH_W, 0.0, config.PITCH_H),
) -> tuple[float, float]:
    """Predict a player position t_sec seconds ahead.

    Constant velocity, clamped to max_speed, pulled toward the player's anchor
    position, then clamped to pitch bounds. Fully deterministic.
    """
    vx, vy = vel
    speed = math.hypot(vx, vy)
    if max_speed and max_speed > 0 and speed > max_speed:
        scale = max_speed / speed
        vx, vy = vx * scale, vy * scale
    x = pos[0] + vx * t_sec
    y = pos[1] + vy * t_sec
    if anchor is not None:
        weight = min(1.0, pull * t_sec)
        x += (anchor[0] - x) * weight
        y += (anchor[1] - y) * weight
    x = max(bounds[0], min(bounds[1], x))
    y = max(bounds[2], min(bounds[3], y))
    return (round(x, 2), round(y, 2))