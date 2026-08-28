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

  it("matches players using uid or name for smooth transition", () => {
    const anonFrames: Frame[] = [
      {
        frame_index: 0,
        timestamp_sec: 10.0,
        minute: 0,
        second: 10,
        players: [
          { player_id: 101, is_teammate: true, is_actor: false, is_keeper: false, location: [10.0, 20.0] },
          { player_id: 201, is_teammate: false, is_actor: false, is_keeper: false, location: [80.0, 60.0] },
        ],
      },
      {
        frame_index: 1,
        timestamp_sec: 20.0,
        minute: 0,
        second: 20,
        players: [
          { player_id: 101, is_teammate: true, is_actor: false, is_keeper: false, location: [14.0, 22.0] },
          { player_id: 201, is_teammate: false, is_actor: false, is_keeper: false, location: [82.0, 62.0] },
        ],
      },
    ];

    const res = interpolateFrames(anonFrames, 15.0);
    expect(res).not.toBeNull();
    expect(res?.players.length).toBe(2);

    const tm = res?.players.find((p) => p.is_teammate);
    const opp = res?.players.find((p) => !p.is_teammate);

    expect(tm?.location[0]).toBeCloseTo(12.0);
    expect(tm?.location[1]).toBeCloseTo(21.0);
    expect(opp?.location[0]).toBeCloseTo(81.0);
    expect(opp?.location[1]).toBeCloseTo(61.0);
  });

  it("selects visible_area based on time interval", () => {
    const polygonFrames: Frame[] = [
      {
        frame_index: 0,
        timestamp_sec: 10.0,
        minute: 0,
        second: 10,
        visible_area: [0.0, 0.0, 40.0, 0.0, 40.0, 40.0, 0.0, 40.0],
        players: [],
      },
      {
        frame_index: 1,
        timestamp_sec: 20.0,
        minute: 0,
        second: 20,
        visible_area: [20.0, 0.0, 60.0, 0.0, 60.0, 40.0, 20.0, 40.0],
        players: [],
      },
    ];

    const res = interpolateFrames(polygonFrames, 12.0);
    expect(res).not.toBeNull();
    expect(res?.visible_area).toEqual(polygonFrames[0].visible_area);
  });
});

