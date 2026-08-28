"""Euro 2020 3788758 경기 전술 분석 원시 데이터 vs 현재 analysis 모듈 출력 대조 진단 스크립트."""

from collections import Counter, defaultdict

from app.analysis.common import build_lineup_maps
from app.analysis.formation import compute_formation_summary
from app.analysis.playbook import compute_playbook_summary
from app.analysis.pressure import compute_pressure_summary
from app.analysis.zones import compute_zones_summary
from app.downloader import StatsBombDownloader


def run_diagnosis() -> None:
    dl = StatsBombDownloader()
    bundle = dl.fetch_full_match_bundle(3788758)
    events = bundle["events"]
    lineups = bundle["lineups"]
    three_sixty = bundle["three_sixty"]

    print("=" * 80)
    print("MATCH 3788758 TACTICAL DATA DIAGNOSIS REPORT")
    print("=" * 80)

    # 1. 경기 기본 정보
    ukr_id = 911
    mkd_id = 2358

    print(f"Teams: Ukraine ({ukr_id}), North Macedonia ({mkd_id})")
    print(f"Total Events: {len(events)}, 360 Frames: {len(three_sixty) if three_sixty else 0}")
    print("-" * 80)

    # -------------------------------------------------------------
    # DIAGNOSIS 1: 포메이션 및 6대 국면 (FORMATION & SUBPHASES)
    # -------------------------------------------------------------
    print("\n[DIAGNOSIS 1] 포메이션 및 선수 위치 / 6대 국면 분석 대조 (Ukraine 기준)")
    lineup_maps = build_lineup_maps(lineups)
    ukr_starters_meta = lineup_maps[ukr_id]["players"]
    ukr_starter_ids = set(lineup_maps[ukr_id]["starting_xi"])

    # (A) 원시 데이터 집계
    raw_in_poss_locs = defaultdict(list)
    raw_out_poss_locs = defaultdict(list)
    raw_phase_events = Counter()

    for ev in events:
        p_id = ev.get("player", {}).get("id")
        poss_team = ev.get("possession_team", {}).get("id")
        loc = ev.get("location")
        if not loc or len(loc) < 2:
            continue
        x, y = float(loc[0]), float(loc[1])

        if poss_team == ukr_id:
            if x < 40.0:
                raw_phase_events["ukr_buildup"] += 1
            elif x < 75.0:
                raw_phase_events["ukr_progression"] += 1
            else:
                raw_phase_events["ukr_final_third"] += 1
            if p_id in ukr_starter_ids:
                raw_in_poss_locs[p_id].append((x, y))
        else:
            if ev.get("team", {}).get("id") == ukr_id:
                if x >= 65.0:
                    raw_phase_events["ukr_high_press"] += 1
                elif x >= 40.0:
                    raw_phase_events["ukr_mid_block"] += 1
                else:
                    raw_phase_events["ukr_low_block"] += 1
                if p_id in ukr_starter_ids:
                    raw_out_poss_locs[p_id].append((x, y))

    print("\n--- (A) Raw Event Counts by Subphase (Ukraine) ---")
    for phase, cnt in raw_phase_events.items():
        print(f"  {phase}: {cnt} events")

    # 360 프레임의 실제 선수 위치 커버리지 확인
    t360_actor_count = 0
    t360_teammates_total = 0
    t360_opponents_total = 0
    for f in three_sixty or []:
        for fp in f.get("freeze_frame", []):
            if fp.get("actor"):
                t360_actor_count += 1
            if fp.get("teammate"):
                t360_teammates_total += 1
            else:
                t360_opponents_total += 1

    print("\n--- 360 Freeze Frame Player Statistics ---")
    print(f"  Total 360 Frames: {len(three_sixty)}")
    print(f"  Actor Players in 360: {t360_actor_count}")
    print(f"  Teammate Positions in 360: {t360_teammates_total}")
    print(f"  Opponent Positions in 360: {t360_opponents_total}")
    print(
        f"  Average players visible per frame: {(t360_teammates_total + t360_opponents_total) / max(1, len(three_sixty)):.1f}"
    )

    # (B) 현재 formation.py 모듈 결과 실행
    curr_form = compute_formation_summary(events, lineups, ukr_id, three_sixty)
    print("\n--- (B) Current formation.py Output vs Raw Data ---")
    print(f"  Reported Formation: {curr_form['formation']}")
    print(f"  Reported Team Length: {curr_form['team_length']}, Width: {curr_form['team_width']}")
    print("  Subphase Shapes reported:")
    for sp_key, sp_val in curr_form["subphases"].items():
        print(
            f"    [{sp_key}] formation: {sp_val['formation']}, line_height: {sp_val['line_height']}, width: {sp_val['width']}, length: {sp_val['length']}"
        )

    # 대표 선수 5명에 대해 원시 평균 좌표 vs 모듈 출력 좌표 비교
    print("\n  Sample Starters Coordinate Comparison:")
    curr_players_map = {p["player_id"]: p for p in curr_form["players"]}
    for pid in list(ukr_starter_ids)[:5]:
        p_name = ukr_starters_meta[pid]["player_name"]
        curr_p = curr_players_map.get(pid, {})
        raw_in = raw_in_poss_locs.get(pid, [])
        raw_in_x = sum(pt[0] for pt in raw_in) / len(raw_in) if raw_in else 0
        raw_in_y = sum(pt[1] for pt in raw_in) / len(raw_in) if raw_in else 0

        fin_p = next(
            (p for p in curr_form["subphases"]["final_third"]["players"] if p["player_id"] == pid),
            None,
        )
        fin_mod_x = fin_p["x"] if fin_p else None

        print(f"    Player: {p_name} (Pos: {ukr_starters_meta[pid]['primary_position']})")
        print(f"      Raw In-Possession Avg: ({raw_in_x:.1f}, {raw_in_y:.1f}) [n={len(raw_in)}]")
        print(
            f"      Current Overall Output: ({curr_p.get('x')}, {curr_p.get('y')}) [Anchor: ({curr_p.get('anchor_x')}, {curr_p.get('anchor_y')})]"
        )
        print(f"      Current Final-Third Output X: {fin_mod_x}")

    # -------------------------------------------------------------
    # DIAGNOSIS 2: 5대 시그니처 공격 플레이북 (PLAYBOOK)
    # -------------------------------------------------------------
    print("\n" + "=" * 80)
    print("[DIAGNOSIS 2] 5대 시그니처 공격 플레이북 분석 대조 (Ukraine 기준)")
    curr_playbook = compute_playbook_summary(events, ukr_id)

    print("\n--- (A) Raw Pattern Detection vs (B) Current Module Output ---")
    for pat in curr_playbook:
        print(f"  Pattern: {pat['pattern_id']} ({pat['name_ko']})")
        print(
            f"    Occurrences: {pat['occurrences']}, Total xG: {pat['total_xg']}, Sequences Stored: {len(pat['sequences'])}"
        )
        if pat["sequences"]:
            first_seq = pat["sequences"][0]
            print(f"    Sample sequence events ({len(first_seq)} steps):")
            for step in first_seq:
                print(
                    f"      - {step.get('type')}: ({step.get('start_x')}, {step.get('start_y')}) -> ({step.get('end_x')}, {step.get('end_y')}) by {step.get('player_name')}"
                )

    # -------------------------------------------------------------
    # DIAGNOSIS 3: 압박 및 PPDA / 압박 트랩 (PRESSURE)
    # -------------------------------------------------------------
    print("\n" + "=" * 80)
    print("[DIAGNOSIS 3] 압박 강도, PPDA 및 압박 트랩 핫스팟 대조 (Ukraine 기준)")
    curr_pressure = compute_pressure_summary(events, ukr_id)

    ukr_pressures = [
        ev
        for ev in events
        if ev.get("team", {}).get("id") == ukr_id and ev.get("type", {}).get("name") == "Pressure"
    ]
    mkd_pressures = [
        ev
        for ev in events
        if ev.get("team", {}).get("id") == mkd_id and ev.get("type", {}).get("name") == "Pressure"
    ]

    mkd_passes_opp_third = [
        ev
        for ev in events
        if ev.get("team", {}).get("id") == mkd_id
        and ev.get("type", {}).get("name") == "Pass"
        and (ev.get("location") and ev.get("location")[0] < 80.0)
    ]
    mkd_passes_own_half = [
        ev
        for ev in events
        if ev.get("team", {}).get("id") == mkd_id
        and ev.get("type", {}).get("name") == "Pass"
        and (ev.get("location") and ev.get("location")[0] < 60.0)
    ]
    mkd_passes_def_third = [
        ev
        for ev in events
        if ev.get("team", {}).get("id") == mkd_id
        and ev.get("type", {}).get("name") == "Pass"
        and (ev.get("location") and ev.get("location")[0] < 40.0)
    ]

    print(f"  Raw Pressures: Ukraine={len(ukr_pressures)}, North Macedonia={len(mkd_pressures)}")
    print(
        f"  MKD Passes in x<80: {len(mkd_passes_opp_third)}, in x<60: {len(mkd_passes_own_half)}, in x<40: {len(mkd_passes_def_third)}"
    )
    print(f"  Current Module PPDA: {curr_pressure['ppda']}")
    print(f"  Current Module High Press Actions: {curr_pressure['high_press_defensive_actions']}")
    print(f"  Current Module Traps Found: {len(curr_pressure['pressure_traps'])}")
    for trap in curr_pressure["pressure_traps"]:
        print(
            f"    Trap: {trap['zone']}, Count: {trap['count']}, Center: ({trap['x']}, {trap['y']}), Intensity: {trap['intensity']}"
        )

    # -------------------------------------------------------------
    # DIAGNOSIS 4: 구역 점유율 (ZONES OCCUPANCY)
    # -------------------------------------------------------------
    print("\n" + "=" * 80)
    print("[DIAGNOSIS 4] 12x8 구역 점유율 및 좌표계 변환 대조 (Ukraine 기준)")
    curr_zones = compute_zones_summary(events, ukr_id, three_sixty)

    opp_frame_ukr_xs = []
    own_frame_ukr_xs = []
    for f in three_sixty or []:
        ev_id = f.get("event_uuid")
        matching_ev = next((ev for ev in events if ev.get("id") == ev_id), None)
        if not matching_ev:
            continue
        ev_team = matching_ev.get("team", {}).get("id")
        for fp in f.get("freeze_frame", []):
            loc = fp.get("location")
            if not loc or len(loc) < 2:
                continue
            is_tm = fp.get("teammate", False)
            if ev_team == ukr_id and is_tm:
                own_frame_ukr_xs.append(float(loc[0]))
            elif ev_team == mkd_id and not is_tm:
                opp_frame_ukr_xs.append(float(loc[0]))

    print(
        f"  Own-event 360 Ukraine players avg X: {sum(own_frame_ukr_xs) / len(own_frame_ukr_xs):.2f} (n={len(own_frame_ukr_xs)})"
    )
    print(
        f"  Opponent-event 360 Ukraine players (without coordinate flip) avg X: {sum(opp_frame_ukr_xs) / len(opp_frame_ukr_xs):.2f} (n={len(opp_frame_ukr_xs)})"
    )
    print(
        f"  Opponent-event 360 Ukraine players (WITH coordinate flip 120-x) avg X: {sum(120.0 - x for x in opp_frame_ukr_xs) / len(opp_frame_ukr_xs):.2f}"
    )
    print(f"  Current Zone Total Samples: {curr_zones['total_samples']}")

    print("\n" + "=" * 80)
    print("DIAGNOSIS COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    run_diagnosis()
