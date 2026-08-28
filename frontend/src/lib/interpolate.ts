/**
 * 백엔드 10Hz 사전 보간 데이터셋을 위한 60fps 경량 렌더러 프레임 룩업 엔진.
 */

import { Frame, FramePlayer, PassingLane } from "../types";

export interface InterpolatedFrame {
  timestamp_sec: number;
  ball_location?: [number, number];
  visible_area?: number[];
  players: FramePlayer[];
  passing_lanes?: PassingLane[];
  description?: string;
  minute: number;
  second: number;
}

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

/**
 * 주어진 현재 시간(currentSec)에 해당하는 프레임 상태를 고속 룩업 및 미세 보간(Micro-Lerp)합니다.
 */
export function interpolateFrames(
  frames: Frame[],
  currentSec: number
): InterpolatedFrame | null {
  if (!frames || frames.length === 0) return null;

  if (frames.length === 1 || currentSec <= frames[0].timestamp_sec) {
    const f = frames[0];
    return {
      timestamp_sec: f.timestamp_sec,
      ball_location: f.ball_location,
      visible_area: f.visible_area,
      players: f.players,
      passing_lanes: f.passing_lanes,
      description: f.description,
      minute: f.minute,
      second: f.second,
    };
  }

  const lastFrame = frames[frames.length - 1];
  if (currentSec >= lastFrame.timestamp_sec) {
    return {
      timestamp_sec: lastFrame.timestamp_sec,
      ball_location: lastFrame.ball_location,
      visible_area: lastFrame.visible_area,
      players: lastFrame.players,
      passing_lanes: lastFrame.passing_lanes,
      description: lastFrame.description,
      minute: lastFrame.minute,
      second: lastFrame.second,
    };
  }

  // 이진 탐색(Binary Search)을 통한 O(log N) 고속 인접 프레임 탐색
  let low = 0;
  let high = frames.length - 1;
  let idx = 0;

  while (low <= high) {
    const mid = Math.floor((low + high) / 2);
    if (frames[mid].timestamp_sec <= currentSec) {
      idx = mid;
      low = mid + 1;
    } else {
      high = mid - 1;
    }
  }

  const f1 = frames[idx];
  const f2 = idx + 1 < frames.length ? frames[idx + 1] : f1;

  if (f1 === f2) {
    return {
      timestamp_sec: f1.timestamp_sec,
      ball_location: f1.ball_location,
      visible_area: f1.visible_area,
      players: f1.players,
      passing_lanes: f1.passing_lanes,
      description: f1.description,
      minute: f1.minute,
      second: f1.second,
    };
  }

  const dt = f2.timestamp_sec - f1.timestamp_sec;
  const alpha = dt > 0 ? Math.max(0, Math.min(1, (currentSec - f1.timestamp_sec) / dt)) : 0;

  // 1. 공 위치 미세 보간
  let ballLoc: [number, number] | undefined = undefined;
  if (f1.ball_location && f2.ball_location) {
    ballLoc = [
      lerp(f1.ball_location[0], f2.ball_location[0], alpha),
      lerp(f1.ball_location[1], f2.ball_location[1], alpha),
    ];
  } else {
    ballLoc = f1.ball_location || f2.ball_location;
  }

  // 2. 선수 위치 1:1 보간 (10Hz 데이터셋 기준 동일 인덱스 또는 ID 매칭)
  const f2Map = new Map<any, FramePlayer>();
  for (const p of f2.players) {
    const key = p.player_id ?? (p as any).uid ?? p.name;
    f2Map.set(key, p);
  }

  const interpolatedPlayers: FramePlayer[] = [];
  for (const p1 of f1.players) {
    const key = p1.player_id ?? (p1 as any).uid ?? p1.name;
    const p2 = f2Map.get(key);

    if (p2) {
      interpolatedPlayers.push({
        ...p1,
        location: [
          lerp(p1.location[0], p2.location[0], alpha),
          lerp(p1.location[1], p2.location[1], alpha),
        ],
        opacity: lerp(p1.opacity ?? 1.0, p2.opacity ?? 1.0, alpha),
      });
    } else {
      interpolatedPlayers.push(p1);
    }
  }

  return {
    timestamp_sec: currentSec,
    ball_location: ballLoc,
    visible_area: alpha < 0.5 ? f1.visible_area : f2.visible_area,
    players: interpolatedPlayers,
    passing_lanes: alpha < 0.5 ? f1.passing_lanes : f2.passing_lanes,
    description: alpha < 0.5 ? f1.description : f2.description,
    minute: alpha < 0.5 ? f1.minute : f2.minute,
    second: alpha < 0.5 ? f1.second : f2.second,
  };
}


