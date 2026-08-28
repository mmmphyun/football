"""시간대별 전술 변화 타임라인 분석 모듈.

경기를 15분 단위 구간(0~15, 15~30, 30~45, 45~60, 60~75, 75~90+)으로 분할하여
수비 라인 높이, 점유율, 압박 강도, 패스 성공률 및 국면별 점유 변화를 산출합니다.
"""

from typing import Any

from app.analysis.common import build_lineup_maps, get_match_duration_min, is_completed_pass
from app.config import DEFENSIVE_THIRD_X, HALF_PITCH_X, TIMELINE_INTERVAL_MINUTES


def compute_timeline_summary(
    events: list[dict[str, Any]],
    team_id: int,
    lineups: list[dict[str, Any]] | None = None,
    interval_min: int = TIMELINE_INTERVAL_MINUTES,
) -> list[dict[str, Any]]:
    """팀의 15분 단위 전술 타임라인 슬라이스 목록을 산출합니다."""
    duration_min = int(get_match_duration_min(events))
    if duration_min <= 0:
        duration_min = 90

    # 라인업 정보가 있으면 선수 메타데이터 맵 구성
    players_meta: dict[int, dict[str, Any]] = {}
    if lineups:
        lineup_maps = build_lineup_maps(lineups)
        players_meta = lineup_maps.get(team_id, {}).get("players", {})

    # 15분 단위 구간 생성
    slices: list[dict[str, Any]] = []
    num_intervals = max(1, (duration_min + interval_min - 1) // interval_min)

    for i in range(num_intervals):
        start_min = i * interval_min
        end_min = min(duration_min, (i + 1) * interval_min)

        slice_events = [
            ev
            for ev in events
            if start_min <= ev.get("minute", 0) < (end_min if i < num_intervals - 1 else 999)
        ]

        team_slice_events = [ev for ev in slice_events if ev.get("team", {}).get("id") == team_id]
        total_slice_events_count = len(slice_events)

        # 1. 점유율 계산 (전체 패스/캐리 중 해당 팀 비율)
        poss_events = [
            ev for ev in slice_events if ev.get("type", {}).get("name") in {"Pass", "Carry", "Shot"}
        ]
        team_poss_events = [
            ev for ev in poss_events if ev.get("possession_team", {}).get("id") == team_id
        ]
        poss_pct = (
            round((len(team_poss_events) / len(poss_events)) * 100.0, 1) if poss_events else 50.0
        )

        # 2. 패스 성공률
        passes = [ev for ev in team_slice_events if ev.get("type", {}).get("name") == "Pass"]
        completed = [ev for ev in passes if is_completed_pass(ev)]
        pass_acc = round((len(completed) / len(passes)) * 100.0, 1) if passes else 0.0

        # 3. 압박 횟수
        pressures = len(
            [ev for ev in team_slice_events if ev.get("type", {}).get("name") == "Pressure"]
        )

        # 4. 수비 라인 높이 (수비 액션 및 후방 위치 평균 x)
        def_locs = []
        for ev in team_slice_events:
            loc = ev.get("location")
            if loc and len(loc) >= 1:
                x = float(loc[0])
                if (
                    ev.get("type", {}).get("name")
                    in {
                        "Pressure",
                        "Tackle",
                        "Interception",
                        "Block",
                        "Clearance",
                    }
                    or x < DEFENSIVE_THIRD_X + 15.0
                ):
                    def_locs.append(x)

        avg_def_line = round(sum(def_locs) / len(def_locs), 1) if def_locs else 35.0

        # 5. 국면 분포 (Defensive / Buildup / Attacking)
        def_count = 0
        bld_count = 0
        att_count = 0

        for ev in team_slice_events:
            loc = ev.get("location")
            x = float(loc[0]) if loc and len(loc) >= 1 else 60.0
            poss_id = ev.get("possession_team", {}).get("id")

            if poss_id != team_id:
                def_count += 1
            elif x < HALF_PITCH_X:
                bld_count += 1
            else:
                att_count += 1

        total_phase = max(1, def_count + bld_count + att_count)
        phase_dist = {
            "defensive": round((def_count / total_phase) * 100.0, 1),
            "buildup": round((bld_count / total_phase) * 100.0, 1),
            "attacking": round((att_count / total_phase) * 100.0, 1),
        }

        # 6. 구간 내 참여 선수 평균 포메이션 좌표 산출
        player_coords: dict[int, list[tuple[float, float]]] = {}
        player_info_map: dict[int, dict[str, Any]] = {}

        for ev in team_slice_events:
            p_obj = ev.get("player")
            if not p_obj or not p_obj.get("id"):
                continue
            pid = p_obj["id"]
            pname = p_obj.get("name", "Unknown")
            pos_name = ev.get("position", {}).get("name", "Player")
            loc = ev.get("location")
            if loc and len(loc) >= 2:
                player_coords.setdefault(pid, []).append((float(loc[0]), float(loc[1])))
                if pid not in player_info_map:
                    p_meta = players_meta.get(pid, {})
                    disp_name = p_meta.get("player_nickname") or p_meta.get("player_name") or pname
                    player_info_map[pid] = {
                        "player_id": pid,
                        "player_name": disp_name,
                        "player_nickname": p_meta.get("player_nickname"),
                        "position": pos_name,
                    }

        slice_players: list[dict[str, Any]] = []
        for pid, coords in player_coords.items():
            avg_x = sum(c[0] for c in coords) / len(coords)
            avg_y = sum(c[1] for c in coords) / len(coords)
            info = player_info_map.get(pid, {})
            slice_players.append(
                {
                    "player_id": pid,
                    "player_name": info.get("player_name", "Unknown"),
                    "player_nickname": info.get("player_nickname"),
                    "position": info.get("position", "Player"),
                    "x": round(avg_x, 2),
                    "y": round(avg_y, 2),
                    "event_count": len(coords),
                }
            )

        # 활동량(이벤트 참여 횟수) 상위 최대 11명으로 정원 엄수 (교체 출전 선수로 인한 증식 방지)
        slice_players.sort(key=lambda p: p["event_count"], reverse=True)
        slice_players = slice_players[:11]

        # 7. 구간 내 주요 이벤트 (골, 옐로/레드카드, 슛)
        key_events = []
        for ev in slice_events:
            ev_type = ev.get("type", {}).get("name", "")
            if ev_type == "Shot":
                shot_team_id = ev.get("team", {}).get("id")
                outcome = ev.get("shot", {}).get("outcome", {}).get("name", "")
                if outcome == "Goal":
                    key_events.append(
                        {
                            "type": "Goal",
                            "minute": ev.get("minute", 0),
                            "team_id": shot_team_id,
                            "player": ev.get("player", {}).get("name", "Unknown"),
                        }
                    )
            elif ev_type in {"Bad Behaviour", "Foul Committed"}:
                card = ev.get("foul_committed", {}).get("card", {}).get("name") or ev.get(
                    "bad_behaviour", {}
                ).get("card", {}).get("name")
                if card:
                    key_events.append(
                        {
                            "type": card,
                            "minute": ev.get("minute", 0),
                            "team_id": ev.get("team", {}).get("id"),
                            "player": ev.get("player", {}).get("name", "Unknown"),
                        }
                    )

        slices.append(
            {
                "slice_index": i,
                "minute_start": start_min,
                "minute_end": end_min,
                "label": f"{start_min}'-{end_min}'",
                "possession_pct": poss_pct,
                "pass_accuracy": pass_acc,
                "pressures": pressures,
                "defensive_line_height": avg_def_line,
                "total_events": total_slice_events_count,
                "phase_distribution": phase_dist,
                "players": slice_players,
                "key_events": key_events,
            }
        )

    return slices
