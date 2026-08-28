"""다중 벤치마크 경기 대상 전술 분석 새 엔진 검증 스크립트."""

import sys
from typing import Any

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from app.analysis.formation import compute_formation_summary
from app.analysis.playbook import compute_playbook_summary
from app.analysis.pressure import compute_pressure_summary
from app.analysis.zones import compute_zones_summary
from app.downloader import StatsBombDownloader


def verify_match(match_id: int, match_label: str, target_team_name: str) -> dict[str, Any]:
    print("=" * 90)
    print(f"VERIFYING MATCH: {match_label} (Match ID: {match_id})")
    print("=" * 90)

    dl = StatsBombDownloader()
    bundle = dl.fetch_full_match_bundle(match_id)
    events = bundle["events"]
    lineups = bundle["lineups"]

    target_team_id = next(
        ev["team"]["id"]
        for ev in events
        if ev.get("team") and target_team_name.lower() in ev["team"]["name"].lower()
    )

    # 1. 포메이션 및 전술 역할
    form = compute_formation_summary(events, lineups, target_team_id, None)
    print(f"\n[1. FORMATION & ROLES] Team: {target_team_name} ({target_team_id})")
    print(
        f"  Starting Formation: {form['formation']}, Length: {form['team_length']}m, Width: {form['team_width']}m"
    )
    print("  Subphase Shapes:")
    for sp_k, sp_v in form["subphases"].items():
        print(
            f"    - {sp_k:12s} ({sp_v['name']}): shape={sp_v['formation']:7s}, line_height={sp_v['line_height']:5.2f}m, length={sp_v['length']:5.2f}m"
        )

    print("\n  Starters Tactical Roles & Empirical Coordinates:")
    for p in form["starters"]:
        print(
            f"    #{p['jersey_number']:<2d} {p['player_name']:<24s} | Pos: {p['position']:<22s} | Role: {p['tactical_role']:<26s} ({p['tactical_role_ko']}) | Coords: ({p['x']:5.2f}, {p['y']:5.2f}) [Events: {p['event_count']}]"
        )

    # 2. 5대 시그니처 공격 플레이북
    playbook = compute_playbook_summary(events, target_team_id)
    print(f"\n[2. PLAYBOOK SIGNATURE PATTERNS] Found {len(playbook)} patterns:")
    for pat in playbook:
        print(
            f"  * {pat['name']} ({pat['name_ko']}): {pat['occurrences']} occurrences, Total xG: {pat['total_xg']}, Sequences Stored: {len(pat['sequences'])}"
        )
        if pat["sequences"]:
            seq = pat["sequences"][0]
            print(
                f"    Sample ({len(seq)} steps): "
                + " -> ".join(f"{s['type']} by {s['player_name']}" for s in seq)
            )

    # 3. 압박 & PPDA
    pressure = compute_pressure_summary(events, target_team_id)
    print("\n[3. PRESSURE & PPDA]")
    print(f"  Total Pressures: {pressure['total_pressures']} ({pressure['pressures_per_min']}/min)")
    print(f"  Standard PPDA: {pressure['ppda']}")
    print(f"  High Press Defensive Actions (x>=48): {pressure['high_press_defensive_actions']}")
    print(f"  Opponent Passes in def 40% (x<=48): {pressure['opponent_passes_in_buildup']}")
    print(f"  Pressure Traps Found: {len(pressure['pressure_traps'])}")
    for trap in pressure["pressure_traps"]:
        print(
            f"    - {trap['zone']}: {trap['count']} times at ({trap['x']}, {trap['y']}) [Intensity: {trap['intensity']}]"
        )

    # 4. 구역 점유율
    zones = compute_zones_summary(events, target_team_id, None)
    print(f"\n[4. ZONES OCCUPANCY] Total Samples: {zones['total_samples']}")

    return {
        "formation": form,
        "playbook": playbook,
        "pressure": pressure,
        "zones": zones,
    }


def run_all_verifications() -> None:
    # Match 1: 2022 World Cup Final (Argentina vs France)
    verify_match(3869685, "2022 World Cup Final: Argentina vs France", "Argentina")

    # Match 2: 2022 World Cup Group Stage (Spain vs Costa Rica)
    verify_match(3857291, "2022 World Cup: Spain vs Costa Rica", "Spain")

    # Match 3: Euro 2020 (Ukraine vs North Macedonia)
    verify_match(3788758, "Euro 2020: Ukraine vs North Macedonia", "Ukraine")

    print("\n" + "=" * 90)
    print("ALL BENCHMARK MATCH VERIFICATIONS COMPLETED SUCCESSFULLY!")
    print("=" * 90)


if __name__ == "__main__":
    run_all_verifications()
