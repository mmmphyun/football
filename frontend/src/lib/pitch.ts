/**
 * StatsBomb 120x80 피치 좌표계 및 SVG 렌더링 헬퍼 모듈.
 */

export const PITCH_WIDTH = 120;
export const PITCH_HEIGHT = 80;

export interface PitchDimensions {
  width: number;
  height: number;
  margin: number;
}

export function clamp(val: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, val));
}

/**
 * 120x80 StatsBomb 좌표를 지정된 SVG 너비/높이 픽셀 좌표로 변환합니다.
 */
export function toSvgCoords(
  x: number,
  y: number,
  viewWidth: number,
  viewHeight: number,
  margin = 20
): [number, number] {
  const innerWidth = viewWidth - margin * 2;
  const innerHeight = viewHeight - margin * 2;

  const scaleX = innerWidth / PITCH_WIDTH;
  const scaleY = innerHeight / PITCH_HEIGHT;

  const svgX = margin + x * scaleX;
  const svgY = margin + y * scaleY;

  return [svgX, svgY];
}

/**
 * [x1, y1, x2, y2, ...] 형태의 1차원 visible_area 배열을 SVG polygon points 문자열로 변환합니다.
 */
export function formatPolygonPoints(
  coords: number[],
  viewWidth: number,
  viewHeight: number,
  margin = 20
): string {
  if (!coords || coords.length < 6) return "";

  const points: string[] = [];
  for (let i = 0; i < coords.length; i += 2) {
    const x = coords[i];
    const y = coords[i + 1];
    if (x !== undefined && y !== undefined) {
      const [sx, sy] = toSvgCoords(x, y, viewWidth, viewHeight, margin);
      points.push(`${sx.toFixed(1)},${sy.toFixed(1)}`);
    }
  }
  return points.join(" ");
}

/**
 * 12x8 그리드 셀의 픽셀 좌표 바운딩 박스를 계산합니다.
 */
export function getZoneRect(
  col: number, // 0..11
  row: number, // 0..7
  viewWidth: number,
  viewHeight: number,
  margin = 20
): { x: number; y: number; width: number; height: number } {
  const cellW = PITCH_WIDTH / 12; // 10
  const cellH = PITCH_HEIGHT / 8; // 10

  const [x, y] = toSvgCoords(col * cellW, row * cellH, viewWidth, viewHeight, margin);
  const [x2, y2] = toSvgCoords(
    (col + 1) * cellW,
    (row + 1) * cellH,
    viewWidth,
    viewHeight,
    margin
  );

  return {
    x,
    y,
    width: x2 - x,
    height: y2 - y,
  };
}
