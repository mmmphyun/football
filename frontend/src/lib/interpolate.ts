/**
 * 하이라이트 재생 시 프레임 간 60fps 부드러운 위치 보간(Lerp) 엔진.
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
 * 다각형의 무게중심을 계산합니다.
 */
function getPolygonCenter(poly: number[]): [number, number] {
  let sumX = 0;
  let sumY = 0;
  const count = poly.length / 2;
  for (let i = 0; i < poly.length; i += 2) {
    sumX += poly[i];
    sumY += poly[i + 1];
  }
  return [sumX / count, sumY / count];
}

/**
 * 다각형 꼭짓점들을 중심점 기준 각도순으로 정렬하여 회전 꼬임을 방지합니다.
 */
function sortPolygonPointsByAngle(poly: number[]): number[] {
  if (poly.length < 6) return poly;
  const [cx, cy] = getPolygonCenter(poly);
  const pts: Array<{ x: number; y: number; angle: number }> = [];

  for (let i = 0; i < poly.length; i += 2) {
    const x = poly[i];
    const y = poly[i + 1];
    const angle = Math.atan2(y - cy, x - cx);
    pts.push({ x, y, angle });
  }

  pts.sort((a, b) => a.angle - b.angle);

  const res: number[] = [];
  for (const p of pts) {
    res.push(p.x, p.y);
  }
  return res;
}

/**
 * 카메라 시야각 다각형(Visible Area Polygon)을 꼬임 없이 연속 보간합니다.
 */
function interpolatePolygon(
  p1?: number[],
  p2?: number[],
  alpha: number = 0.5
): number[] | undefined {
  if (!p1 && !p2) return undefined;
  if (!p1 || p1.length < 6) return p2;
  if (!p2 || p2.length < 6) return p1;

  // 두 다각형의 시작 각도를 일치시키기 위해 중심점 기준 각도 정렬
  const sorted1 = sortPolygonPointsByAngle(p1);
  const sorted2 = sortPolygonPointsByAngle(p2);

  const count1 = sorted1.length / 2;
  const count2 = sorted2.length / 2;
  const targetCount = Math.max(count1, count2);
  const res: number[] = new Array(targetCount * 2);

  for (let i = 0; i < targetCount; i++) {
    const idx1 = Math.min(Math.floor((i / targetCount) * count1), count1 - 1) * 2;
    const idx2 = Math.min(Math.floor((i / targetCount) * count2), count2 - 1) * 2;

    res[i * 2] = lerp(sorted1[idx1], sorted2[idx2], alpha);
    res[i * 2 + 1] = lerp(sorted1[idx1 + 1], sorted2[idx2 + 1], alpha);
  }

  return res;
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

  // 2. 선수 위치 보간 (선수 증식 완전 차단: 팀당 11명 상한)
  const f2PlayerMap = new Map<number, FramePlayer>();
  const f2Anonymous: FramePlayer[] = [];

  for (const p of f2.players) {
    if (p.player_id !== undefined && p.player_id !== null) {
      f2PlayerMap.set(p.player_id, p);
    } else {
      f2Anonymous.push(p);
    }
  }

  const rawInterpolated: FramePlayer[] = [];
  const processedF2Ids = new Set<number>();
  const f1Anonymous: FramePlayer[] = [];

  // 2-1. player_id 기준 1:1 매칭
  for (const p1 of f1.players) {
    if (
      p1.player_id !== undefined &&
      p1.player_id !== null &&
      f2PlayerMap.has(p1.player_id)
    ) {
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

      rawInterpolated.push({
        ...p1,
        location: loc,
        pred_location: predLoc,
      });
    } else if (p1.player_id === undefined || p1.player_id === null) {
      f1Anonymous.push(p1);
    } else {
      // f2에 없는 선수는 alpha < 0.5일 때만 유지
      if (clampedAlpha < 0.5) {
        rawInterpolated.push(p1);
      }
    }
  }

  // 2-2. 익명 선수 간 최근접 거리 매칭
  const usedF2AnonIdx = new Set<number>();

  for (const p1 of f1Anonymous) {
    let bestIdx = -1;
    let minDist = 12.0;

    for (let j = 0; j < f2Anonymous.length; j++) {
      if (usedF2AnonIdx.has(j)) continue;
      const p2 = f2Anonymous[j];

      if (p1.is_teammate !== p2.is_teammate || p1.is_keeper !== p2.is_keeper) {
        continue;
      }

      const dist = Math.hypot(
        p1.location[0] - p2.location[0],
        p1.location[1] - p2.location[1]
      );

      if (dist < minDist) {
        minDist = dist;
        bestIdx = j;
      }
    }

    if (bestIdx !== -1) {
      usedF2AnonIdx.add(bestIdx);
      const p2 = f2Anonymous[bestIdx];
      const loc: [number, number] = [
        lerp(p1.location[0], p2.location[0], clampedAlpha),
        lerp(p1.location[1], p2.location[1], clampedAlpha),
      ];

      rawInterpolated.push({
        ...p1,
        location: loc,
      });
    } else if (clampedAlpha < 0.5) {
      rawInterpolated.push(p1);
    }
  }

  // 2-3. f2에 새로 등장한 선수는 alpha >= 0.5일 때 추가
  if (clampedAlpha >= 0.5) {
    for (const p2 of f2.players) {
      if (
        p2.player_id !== undefined &&
        p2.player_id !== null &&
        !processedF2Ids.has(p2.player_id)
      ) {
        rawInterpolated.push(p2);
      }
    }
    for (let j = 0; j < f2Anonymous.length; j++) {
      if (!usedF2AnonIdx.has(j)) {
        rawInterpolated.push(f2Anonymous[j]);
      }
    }
  }

  // 2-4. 팀당 11명(총 22명) 엄격한 상한 필터링 (선수 증식 완벽 방지)
  const tmPlayers = rawInterpolated.filter((p) => p.is_teammate).slice(0, 11);
  const oppPlayers = rawInterpolated.filter((p) => !p.is_teammate).slice(0, 11);
  const finalInterpolatedPlayers = [...tmPlayers, ...oppPlayers];

  // 3. 카메라 시야각 다각형 연속 보간
  const interpolatedVisArea = interpolatePolygon(
    f1.visible_area,
    f2.visible_area,
    clampedAlpha
  );

  return {
    timestamp_sec: currentSec,
    ball_location: ballLoc,
    visible_area: interpolatedVisArea,
    players: finalInterpolatedPlayers,
    passing_lanes: clampedAlpha < 0.5 ? f1.passing_lanes : f2.passing_lanes,
    description: clampedAlpha < 0.5 ? f1.description : f2.description,
    minute: clampedAlpha < 0.5 ? f1.minute : f2.minute,
    second: clampedAlpha < 0.5 ? f1.second : f2.second,
  };
}

