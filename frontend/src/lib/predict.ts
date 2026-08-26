/**
 * 선수 위치 단기(+2초) 외삽 및 이동 벡터 계산 모듈.
 */

import { PITCH_HEIGHT, PITCH_WIDTH, clamp } from "./pitch";

export const MAX_SPEED_MPS = 8.0;
export const PREDICTION_HORIZON_SEC = 2.0;
export const ANCHOR_ATTRACTION_RATE = 0.15;

export interface ExtrapolateOptions {
  horizonSec?: number;
  maxSpeedMps?: number;
  anchor?: [number, number];
  attractionRate?: number;
}

/**
 * 선수 현재 위치와 속도 벡터를 기반으로 t초 후 예측 위치를 산출합니다.
 */
export function predictPlayerPosition(
  location: [number, number],
  velocity?: [number, number],
  options: ExtrapolateOptions = {}
): [number, number] {
  const horizon = options.horizonSec ?? PREDICTION_HORIZON_SEC;
  const maxSpeed = options.maxSpeedMps ?? MAX_SPEED_MPS;
  const anchor = options.anchor;
  const attractionRate = options.attractionRate ?? ANCHOR_ATTRACTION_RATE;

  const [x, y] = location;
  if (!velocity) return [x, y];

  let [vx, vy] = velocity;
  const speed = Math.hypot(vx, vy);

  // 최대 속도 클램프
  if (speed > maxSpeed && speed > 0) {
    const scale = maxSpeed / speed;
    vx *= scale;
    vy *= scale;
  }

  // 외삽 위치 계산
  let predX = x + vx * horizon;
  let predY = y + vy * horizon;

  // 앵커 인력 적용
  if (anchor) {
    const [ax, ay] = anchor;
    predX = predX * (1 - attractionRate) + ax * attractionRate;
    predY = predY * (1 - attractionRate) + ay * attractionRate;
  }

  // 피치 경계 클램프
  predX = clamp(predX, 0, PITCH_WIDTH);
  predY = clamp(predY, 0, PITCH_HEIGHT);

  return [predX, predY];
}
