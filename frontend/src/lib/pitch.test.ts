import { describe, expect, it } from "vitest";
import {
  PITCH_HEIGHT,
  PITCH_WIDTH,
  clamp,
  formatPolygonPoints,
  getZoneRect,
  toSvgCoords,
} from "./pitch";

describe("pitch utility", () => {
  it("clamp clamps values correctly", () => {
    expect(clamp(50, 0, 120)).toBe(50);
    expect(clamp(-10, 0, 120)).toBe(0);
    expect(clamp(150, 0, 120)).toBe(120);
  });

  it("toSvgCoords maps boundary corners", () => {
    const [x0, y0] = toSvgCoords(0, 0, 1240, 840, 20);
    expect(x0).toBe(20);
    expect(y0).toBe(20);

    const [xMax, yMax] = toSvgCoords(PITCH_WIDTH, PITCH_HEIGHT, 1240, 840, 20);
    expect(xMax).toBe(1220);
    expect(yMax).toBe(820);
  });

  it("formatPolygonPoints converts 1D coordinates to SVG points", () => {
    const coords = [0, 0, 60, 40, 120, 80];
    const points = formatPolygonPoints(coords, 1240, 840, 20);
    expect(points).toContain("20.0,20.0");
    expect(points).toContain("620.0,420.0");
    expect(points).toContain("1220.0,820.0");
  });

  it("getZoneRect computes correct grid cell rectangles", () => {
    const rect = getZoneRect(0, 0, 1240, 840, 20);
    expect(rect.x).toBe(20);
    expect(rect.y).toBe(20);
    expect(rect.width).toBeCloseTo(100, 1);
    expect(rect.height).toBeCloseTo(100, 1);
  });
});
