/**
 * 하이라이트 재생 시 프레임 간 60fps 부드러운 위치 보간(Lerp) 엔진.
 */

import { Frame, FramePlayer } from "../types";

export interface InterpolatedFrame {
  timestamp_sec: number;
  ball_location?: [number, number];
  visible_area?: number[];
  players: FramePlayer[];
  description?: string;
  minute: number;
  second: number;
}

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

/**
 * 주어진 현재 시간(currentSec)에 해당하는 보간된 프레임 상태를 생성합니다.
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
      description: lastFrame.description,
      minute: lastFrame.minute,
      second: lastFrame.second,
    };
  }

  // 현재 시간에 인접한 이전/이후 프레임 탐색
  let f1 = frames[0];
  let f2 = frames[1];

  for (let i = 0; i < frames.length - 1; i++) {
    if (
      currentSec >= frames[i].timestamp_sec &&
      currentSec <= frames[i + 1].timestamp_sec
    ) {
      f1 = frames[i];
      f2 = frames[i + 1];
      break;
    }
  }

  const duration = f2.timestamp_sec - f1.timestamp_sec;
  const alpha = duration > 0 ? (currentSec - f1.timestamp_sec) / duration : 0;
  const clampedAlpha = Math.max(0, Math.min(1, alpha));

  // 1. 공 위치 보간
  let ballLoc: [number, number] | undefined = undefined;
  if (f1.ball_location && f2.ball_location) {
    ballLoc = [
      lerp(f1.ball_location[0], f2.ball_location[0], clampedAlpha),
      lerp(f1.ball_location[1], f2.ball_location[1], clampedAlpha),
    ];
  } else {
    ballLoc = f1.ball_location || f2.ball_location;
  }

  // 2. 선수 위치 보간 (player_id 매핑 기반)
  const f2PlayerMap = new Map<number, FramePlayer>();
  for (const p of f2.players) {
    if (p.player_id !== undefined) {
      f2PlayerMap.set(p.player_id, p);
    }
  }

  const interpolatedPlayers: FramePlayer[] = [];
  const processedF2Ids = new Set<number>();

  for (const p1 of f1.players) {
    if (p1.player_id !== undefined && f2PlayerMap.has(p1.player_id)) {
      const p2 = f2PlayerMap.get(p1.player_id)!;
      processedF2Ids.add(p1.player_id);

      const loc: [number, number] = [
        lerp(p1.location[0], p2.location[0], clampedAlpha),
        lerp(p1.location[1], p2.location[1], clampedAlpha),
      ];

      let predLoc: [number, number] | undefined = undefined;
      if (p1.pred_location && p2.pred_location) {
        predLoc = [
          lerp(p1.pred_location[0], p2.pred_location[0], clampedAlpha),
          lerp(p1.pred_location[1], p2.pred_location[1], clampedAlpha),
        ];
      } else {
        predLoc = p1.pred_location || p2.pred_location;
      }

      interpolatedPlayers.push({
        ...p1,
        location: loc,
        pred_location: predLoc,
      });
    } else {
      // f2에 매칭 선수가 없으면 f1 상태 유지
      interpolatedPlayers.push(p1);
    }
  }

  // f2에 새로 등장한 선수 추가
  for (const p2 of f2.players) {
    if (p2.player_id !== undefined && !processedF2Ids.has(p2.player_id)) {
      interpolatedPlayers.push(p2);
    }
  }

  return {
    timestamp_sec: currentSec,
    ball_location: ballLoc,
    visible_area: clampedAlpha < 0.5 ? f1.visible_area : f2.visible_area,
    players: interpolatedPlayers,
    description: clampedAlpha < 0.5 ? f1.description : f2.description,
    minute: clampedAlpha < 0.5 ? f1.minute : f2.minute,
    second: clampedAlpha < 0.5 ? f1.second : f2.second,
  };
}
