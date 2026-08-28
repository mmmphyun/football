import sys
from collections import Counter, defaultdict

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from app.analysis.common import build_lineup_maps
from app.analysis.formation import compute_formation_summary
from app.analysis.playbook import compute_playbook_summary
from app.analysis.pressure import compute_pressure_summary
from app.downloader import StatsBombDownloader


def run_wc_final_diagnosis() -> None:
    dl = StatsBombDownloader()
    comps = dl.fetch_competitions()
    wc = next(
        c
        for c in comps
        if c.get("competition_name") == "FIFA World Cup" and c.get("season_name") == "2022"
    )
    matches = dl.fetch_matches(wc["competition_id"], wc["season_id"])
    final_m = next(
        m
        for m in matches
        if (
            "Argentina" in m.get("home_team", {}).get("home_team_name", "")
            or "Argentina" in m.get("away_team", {}).get("away_team_name", "")
        )
        and (
            "France" in m.get("home_team", {}).get("home_team_name", "")
            or "France" in m.get("away_team", {}).get("away_team_name", "")
        )
    )
    match_id = final_m["match_id"]
    print(
        f"2022 World Cup Final Match ID: {match_id} ({final_m.get('home_team', {}).get('home_team_name')} vs {final_m.get('away_team', {}).get('away_team_name')})"
    )

    bundle = dl.fetch_full_match_bundle(match_id)
    events = bundle["events"]
    lineups = bundle["lineups"]

    # 팀 매핑
    arg_id = next(
        ev["team"]["id"] for ev in events if ev.get("team") and "Argentina" in ev["team"]["name"]
    )
    fra_id = next(
        ev["team"]["id"] for ev in events if ev.get("team") and "France" in ev["team"]["name"]
    )

    print("=" * 80)
    print(f"MATCH {match_id} (Argentina vs France) TACTICAL DATA DIAGNOSIS")
    print("=" * 80)
    print(
        f"Total Events: {len(events)} (Argentina: {sum(1 for ev in events if ev.get('team', {}).get('id') == arg_id)}, France: {sum(1 for ev in events if ev.get('team', {}).get('id') == fra_id)})"
    )

    lineup_maps = build_lineup_maps(lineups)
    arg_starters_meta = lineup_maps[arg_id]["players"]
    arg_starter_ids = set(lineup_maps[arg_id]["starting_xi"])

    # 1. 국면별 원시 이벤트 분포
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

        if poss_team == arg_id:
            if x < 40.0:
                raw_phase_events["arg_buildup"] += 1
            elif x < 75.0:
                raw_phase_events["arg_progression"] += 1
            else:
                raw_phase_events["arg_final_third"] += 1

            if ev_team_id == arg_id and p_id in arg_starter_ids:
                raw_in_poss_locs[p_id].append((x, y))
        else:
            if ev_team_id == arg_id:
                if x >= 65.0:
                    raw_phase_events["arg_high_press"] += 1
                elif x >= 40.0:
                    raw_phase_events["arg_mid_block"] += 1
                else:
                    raw_phase_events["arg_low_block"] += 1

                if p_id in arg_starter_ids:
                    raw_out_poss_locs[p_id].append((x, y))

    print("\n--- (A) Raw Event Counts by Subphase (Argentina) ---")
    for phase, cnt in sorted(raw_phase_events.items()):
        print(f"  {phase}: {cnt} events")

    # 2. 현재 formation 모듈 출력
    curr_form = compute_formation_summary(events, lineups, arg_id, None)
    print("\n--- (B) Formation & Player Positioning (Argentina) ---")
    print(f"  Starting Formation: {curr_form['formation']}")
    print(f"  Reported Team Length: {curr_form['team_length']}, Width: {curr_form['team_width']}")

    curr_players_map = {p["player_id"]: p for p in curr_form["players"]}
    print("\n  [Starters: Raw In-Possession vs Current Output]")
    for pid in list(arg_starter_ids):
        p_info = arg_starters_meta[pid]
        p_name = p_info["player_name"]
        pos_name = p_info["primary_position"]
        curr_p = curr_players_map.get(pid, {})
        raw_in = raw_in_poss_locs.get(pid, [])
        raw_in_x = sum(pt[0] for pt in raw_in) / len(raw_in) if raw_in else 0.0
        raw_in_y = sum(pt[1] for pt in raw_in) / len(raw_in) if raw_in else 0.0

        print(
            f"    {p_name:<28s} ({pos_name:<22s}) | Raw: ({raw_in_x:5.1f}, {raw_in_y:5.1f}) [n={len(raw_in):3d}] | Curr Output: ({curr_p.get('x', 0):5.1f}, {curr_p.get('y', 0):5.1f}) | Anchor: ({curr_p.get('anchor_x'):5.1f}, {curr_p.get('anchor_y'):5.1f})"
        )

    # 3. 5대 공격 플레이북
    print("\n" + "=" * 80)
    print("[DIAGNOSIS 2] 5대 시그니처 공격 플레이북 (Argentina)")
    curr_playbook = compute_playbook_summary(events, arg_id)
    for pat in curr_playbook:
        print(f"  Pattern: {pat['pattern_id']} ({pat['name_ko']})")
        print(
            f"    Occurrences: {pat['occurrences']}, Total xG: {pat['total_xg']}, Sequences Stored: {len(pat['sequences'])}"
        )
        if pat["sequences"]:
            first_seq = pat["sequences"][0]
            print(f"    Sample sequence ({len(first_seq)} steps):")
            for step in first_seq:
                print(
                    f"      - {step.get('type')}: ({step.get('start_x')}, {step.get('start_y')}) -> ({step.get('end_x')}, {step.get('end_y')}) by {step.get('player_name')}"
                )

    # 4. 압박 및 PPDA
    print("\n" + "=" * 80)
    print("[DIAGNOSIS 3] 압박 및 PPDA (Argentina)")
    curr_pressure = compute_pressure_summary(events, arg_id)
    arg_pressures = [
        ev
        for ev in events
        if ev.get("team", {}).get("id") == arg_id and ev.get("type", {}).get("name") == "Pressure"
    ]
    fra_pressures = [
        ev
        for ev in events
        if ev.get("team", {}).get("id") == fra_id and ev.get("type", {}).get("name") == "Pressure"
    ]

    fra_passes_def_40 = [
        ev
        for ev in events
        if ev.get("team", {}).get("id") == fra_id
        and ev.get("type", {}).get("name") == "Pass"
        and (ev.get("location") and ev.get("location")[0] <= 48.0)
    ]
    arg_def_actions_att_60 = [
        ev
        for ev in events
        if ev.get("team", {}).get("id") == arg_id
        and ev.get("type", {}).get("name")
        in {"Pressure", "Tackle", "Interception", "Foul Committed"}
        and (ev.get("location") and ev.get("location")[0] >= 48.0)
    ]

    print(f"  Raw Pressures: Argentina={len(arg_pressures)}, France={len(fra_pressures)}")
    print(f"  France Passes in def 40% (x<=48): {len(fra_passes_def_40)}")
    print(f"  Argentina High Def Actions (x>=48): {len(arg_def_actions_att_60)}")
    std_ppda = round(len(fra_passes_def_40) / max(1, len(arg_def_actions_att_60)), 2)
    print(f"  Standard StatsBomb PPDA: {std_ppda}")
    print(f"  Current Module Reported PPDA: {curr_pressure['ppda']}")
    print(f"  Current Module High Press Actions: {curr_pressure['high_press_defensive_actions']}")
    print(f"  Current Module Traps Found: {len(curr_pressure['pressure_traps'])}")
    for trap in curr_pressure["pressure_traps"]:
        print(
            f"    Trap: {trap['zone']}, Count: {trap['count']}, Center: ({trap['x']}, {trap['y']}), Intensity: {trap['intensity']}"
        )


if __name__ == "__main__":
    run_wc_final_diagnosis()
