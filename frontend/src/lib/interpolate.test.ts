import { describe, expect, it } from "vitest";
import { Frame } from "../types";
import { interpolateFrames } from "./interpolate";

describe("interpolateFrames", () => {
  const sampleFrames: Frame[] = [
    {
      frame_index: 0,
      timestamp_sec: 10.0,
      minute: 0,
      second: 10,
      ball_location: [10.0, 20.0],
      players: [
        {
          player_id: 1,
          is_teammate: true,
          is_actor: true,
          is_keeper: false,
          location: [10.0, 20.0],
        },
      ],
    },
    {
      frame_index: 1,
      timestamp_sec: 20.0,
      minute: 0,
      second: 20,
      ball_location: [30.0, 40.0],
      players: [
        {
          player_id: 1,
          is_teammate: true,
          is_actor: true,
          is_keeper: false,
          location: [30.0, 40.0],
        },
      ],
    },
  ];

  it("returns null for empty frames", () => {
    expect(interpolateFrames([], 15.0)).toBeNull();
  });

  it("returns exact frame for t <= first frame", () => {
    const res = interpolateFrames(sampleFrames, 5.0);
    expect(res?.ball_location).toEqual([10.0, 20.0]);
  });

  it("returns exact frame for t >= last frame", () => {
    const res = interpolateFrames(sampleFrames, 25.0);
    expect(res?.ball_location).toEqual([30.0, 40.0]);
  });

  it("interpolates linearly at midpoint (alpha = 0.5)", () => {
    const res = interpolateFrames(sampleFrames, 15.0);
    expect(res).not.toBeNull();
    expect(res?.ball_location?.[0]).toBeCloseTo(20.0);
    expect(res?.ball_location?.[1]).toBeCloseTo(30.0);
    expect(res?.players[0].location[0]).toBeCloseTo(20.0);
    expect(res?.players[0].location[1]).toBeCloseTo(30.0);
  });
});
