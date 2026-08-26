import { describe, expect, it } from "vitest";
import { predictPlayerPosition } from "./predict";

describe("predictPlayerPosition", () => {
  it("returns current position when velocity is missing", () => {
    const pos = predictPlayerPosition([50, 40]);
    expect(pos).toEqual([50, 40]);
  });

  it("extrapolates position along velocity vector for +2 seconds", () => {
    const pos = predictPlayerPosition([50, 40], [2, 1], { horizonSec: 2.0 });
    expect(pos[0]).toBeCloseTo(54);
    expect(pos[1]).toBeCloseTo(42);
  });

  it("clamps velocity to maxSpeed (8.0 m/s)", () => {
    // vx = 20 > 8
    const pos = predictPlayerPosition([50, 40], [20, 0], {
      horizonSec: 2.0,
      maxSpeedMps: 8.0,
    });
    // 50 + 8 * 2 = 66
    expect(pos[0]).toBeCloseTo(66);
    expect(pos[1]).toBeCloseTo(40);
  });

  it("clamps position to pitch boundaries [0..120, 0..80]", () => {
    const pos = predictPlayerPosition([115, 75], [5, 5], {
      horizonSec: 2.0,
      maxSpeedMps: 8.0,
    });
    expect(pos[0]).toBeLessThanOrEqual(120);
    expect(pos[1]).toBeLessThanOrEqual(80);
  });
});
