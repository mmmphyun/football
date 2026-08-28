"""2022 World Cup Match 3857291 (Spain vs Costa Rica 7-0) Tactical Data Diagnosis Script."""

import sys
from collections import Counter, defaultdict

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from app.analysis.common import build_lineup_maps
from app.analysis.formation import compute_formation_summary
from app.analysis.playbook import compute_playbook_summary
from app.analysis.pressure import compute_pressure_summary
from app.analysis.zones import compute_zones_summary
from app.downloader import StatsBombDownloader


def run_spain_diagnosis() -> None:
    dl = StatsBombDownloader()
    bundle = dl.fetch_full_match_bundle(3857291)
    events = bundle["events"]
    lineups = bundle["lineups"]

    print("=" * 80)
    print("MATCH 3857291 (Spain vs Costa Rica 7-0) TACTICAL DATA DIAGNOSIS")
    print("=" * 80)

    # 1. 팀 ID 확인
    team_names = {}
    for ev in events:
        t = ev.get("team")
        if t and t.get("id"):
            team_names[t["id"]] = t.get("name")

    esp_id = next(tid for tid, name in team_names.items() if "Spain" in name)
    crc_id = next(tid for tid, name in team_names.items() if "Costa Rica" in name)

    print(f"Teams: Spain ({esp_id}), Costa Rica ({crc_id})")
    print(f"Total Events: {len(events)} (Spain: {sum(1 for ev in events if ev.get('team', {}).get('id') == esp_id)}, Costa Rica: {sum(1 for ev in events if ev.get('team', {}).get('id') == crc_id)})")
    print("-" * 80)

    lineup_maps = build_lineup_maps(lineups)
    esp_starters_meta = lineup_maps[esp_id]["players"]
    esp_starter_ids = set(lineup_maps[esp_id]["starting_xi"])

    # -------------------------------------------------------------
    # DIAGNOSIS 1: 포메이션 및 6대 국면 (FORMATION & SUBPHASES)
    # -------------------------------------------------------------
    print("\n[DIAGNOSIS 1] 포메이션 및 선수 위치 / 6대 국면 대조 (Spain 기준)")

    # (A) 원시 이벤트 집계 (스페인 기준 x: 0=스페인골대 -> 120=코스타리카골대)
    raw_in_poss_locs = defaultdict(list)
    raw_out_poss_locs = defaultdict(list)
    raw_phase_events = Counter()

    for ev in events:
        ev_team_id = ev.get("team", {}).get("id")
        p_id = ev.get("player", {}).get("id")
        poss_team = ev.get("possession_team", {}).get("id")
        loc = ev.get("location")
        if not loc or len(loc) < 2:
            continue
        x, y = float(loc[0]), float(loc[1])

        if poss_team == esp_id:
            # 스페인 볼 소유 국면 (x는 스페인 공격 방향 0->120)
            if x < 40.0:
                raw_phase_events["esp_buildup"] += 1
            elif x < 75.0:
                raw_phase_events["esp_progression"] += 1
            else:
                raw_phase_events["esp_final_third"] += 1

            if ev_team_id == esp_id and p_id in esp_starter_ids:
                raw_in_poss_locs[p_id].append((x, y))
        else:
            # 스페인 볼 미소유 국면 중 스페인의 자체 수비 액션 (ev_team_id == esp_id)
            if ev_team_id == esp_id:
                # 스페인 수비 액션 이벤트의 x좌표는 스페인 기준 (0=스페인골대, 120=상대골대)
                if x >= 65.0:
                    raw_phase_events["esp_high_press"] += 1
                elif x >= 40.0:
                    raw_phase_events["esp_mid_block"] += 1
                else:
                    raw_phase_events["esp_low_block"] += 1

                if p_id in esp_starter_ids:
                    raw_out_poss_locs[p_id].append((x, y))

    print("\n--- (A) Raw Event Counts by Subphase (Spain) ---")
    for phase, cnt in sorted(raw_phase_events.items()):
        print(f"  {phase}: {cnt} events")

    # (B) 현재 formation.py 모듈 결과 실행
    curr_form = compute_formation_summary(events, lineups, esp_id, None)
    print("\n--- (B) Current formation.py Output vs Raw Data ---")
    print(f"  Reported Starting Formation: {curr_form['formation']}")
    print(f"  Reported Team Length: {curr_form['team_length']}, Width: {curr_form['team_width']}")
    print("  Subphase Shapes reported:")
    for sp_key, sp_val in curr_form["subphases"].items():
        print(f"    [{sp_key:12s}] formation: {sp_val['formation']:6s}, line_height: {sp_val['line_height']:5.2f}, width: {sp_val['width']:5.2f}, length: {sp_val['length']:5.2f}")

    print("\n  Starters Coordinate Comparison (Raw In-Possession vs Current Output):")
    curr_players_map = {p["player_id"]: p for p in curr_form["players"]}
    for pid in list(esp_starter_ids):
        p_info = esp_starters_meta[pid]
        p_name = p_info["player_name"]
        pos_name = p_info["primary_position"]
        curr_p = curr_players_map.get(pid, {})
        raw_in = raw_in_poss_locs.get(pid, [])
        raw_in_x = sum(pt[0] for pt in raw_in)/len(raw_in) if raw_in else 0.0
        raw_in_y = sum(pt[1] for pt in raw_in)/len(raw_in) if raw_in else 0.0

        # final_third 국면에서의 모듈 값
        fin_p = next((p for p in curr_form["subphases"]["final_third"]["players"] if p["player_id"] == pid), None)
        fin_mod_x = fin_p["x"] if fin_p else None

        print(f"    {p_name:<24s} ({pos_name:<22s}) | Raw Avg: ({raw_in_x:5.1f}, {raw_in_y:5.1f}) [n={len(raw_in):3d}] | Curr Overall: ({curr_p.get('x', 0):5.1f}, {curr_p.get('y', 0):5.1f}) | Final-Third X: {fin_mod_x}")

    # -------------------------------------------------------------
    # DIAGNOSIS 2: 5대 시그니처 공격 플레이북 (PLAYBOOK)
    # -------------------------------------------------------------
    print("\n" + "=" * 80)
    print("[DIAGNOSIS 2] 5대 시그니처 공격 플레이북 분석 대조 (Spain 기준)")
    curr_playbook = compute_playbook_summary(events, esp_id)

    print("\n--- Current Playbook Output ---")
    for pat in curr_playbook:
        print(f"  Pattern: {pat['pattern_id']} ({pat['name_ko']})")
        print(f"    Occurrences: {pat['occurrences']}, Total xG: {pat['total_xg']}, Sequences Stored: {len(pat['sequences'])}")
        if pat["sequences"]:
            first_seq = pat["sequences"][0]
            print(f"    Sample sequence ({len(first_seq)} steps):")
            for step in first_seq:
                print(f"      - {step.get('type')}: ({step.get('start_x')}, {step.get('start_y')}) -> ({step.get('end_x')}, {step.get('end_y')}) by {step.get('player_name')}")

    # -------------------------------------------------------------
    # DIAGNOSIS 3: 압박 및 PPDA / 압박 트랩 (PRESSURE)
    # -------------------------------------------------------------
    print("\n" + "=" * 80)
    print("[DIAGNOSIS 3] 압박 강도, PPDA 및 압박 트랩 핫스팟 대조 (Spain 기준)")
    curr_pressure = compute_pressure_summary(events, esp_id)

    esp_pressures = [ev for ev in events if ev.get("team", {}).get("id") == esp_id and ev.get("type", {}).get("name") == "Pressure"]
    crc_pressures = [ev for ev in events if ev.get("team", {}).get("id") == crc_id and ev.get("type", {}).get("name") == "Pressure"]

    crc_passes_total = [ev for ev in events if ev.get("team", {}).get("id") == crc_id and ev.get("type", {}).get("name") == "Pass"]
    crc_passes_def_40 = [ev for ev in events if ev.get("team", {}).get("id") == crc_id and ev.get("type", {}).get("name") == "Pass" and (ev.get("location") and ev.get("location")[0] <= 48.0)]
    esp_def_actions_att_60 = [ev for ev in events if ev.get("team", {}).get("id") == esp_id and ev.get("type", {}).get("name") in {"Pressure", "Tackle", "Interception", "Foul Committed"} and (ev.get("location") and ev.get("location")[0] >= 48.0)]

    print(f"  Raw Pressures: Spain={len(esp_pressures)}, Costa Rica={len(crc_pressures)}")
    print(f"  CRC Total Passes: {len(crc_passes_total)}, CRC Passes in def 40% (x<=48): {len(crc_passes_def_40)}")
    print(f"  Spain High Def Actions (x>=48): {len(esp_def_actions_att_60)}")
    std_ppda = round(len(crc_passes_def_40) / max(1, len(esp_def_actions_att_60)), 2)
    print(f"  Standard StatsBomb PPDA: {std_ppda}")
    print(f"  Current Module Reported PPDA: {curr_pressure['ppda']}")
    print(f"  Current Module High Press Actions: {curr_pressure['high_press_defensive_actions']}")
    print(f"  Current Module Traps Found: {len(curr_pressure['pressure_traps'])}")
    for trap in curr_pressure["pressure_traps"]:
        print(f"    Trap: {trap['zone']}, Count: {trap['count']}, Center: ({trap['x']}, {trap['y']}), Intensity: {trap['intensity']}")

    # -------------------------------------------------------------
    # DIAGNOSIS 4: 구역 점유율 (ZONES OCCUPANCY)
    # -------------------------------------------------------------
    print("\n" + "=" * 80)
    print("[DIAGNOSIS 4] 12x8 구역 점유율 대조 (Spain 기준)")
    curr_zones = compute_zones_summary(events, esp_id, None)
    print(f"  Zone Total Samples: {curr_zones['total_samples']}")

    print("\n" + "=" * 80)
    print("SPAIN DIAGNOSIS COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    run_spain_diagnosis()
