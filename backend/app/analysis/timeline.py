"""시간대별 전술 변화 타임라인 분석 모듈.

경기를 축구 표준 15분 단위 구간(0~15, 15~30, 30~45+, 45~60, 60~75, 75~90+, 연장전 90~105+, 105~120+)으로 분할하여
수비 라인 높이, 점유율, 압박 강도, 패스 성공률, 국면별 점유 변화 및 교체 체인 기반 11인 포메이션을 산출합니다.
"""

from collections import defaultdict
from typing import Any

from app.analysis.common import build_lineup_maps, is_completed_pass
from app.config import DEFENSIVE_THIRD_X, HALF_PITCH_X, TIMELINE_INTERVAL_MINUTES


def _build_substitution_clusters(events: list[dict[str, Any]]) -> list[set[int]]:
    """경기 내 교체(Substitution) 이벤트를 분석하여 서로 연계된 교체 패밀리 클러스터를 생성합니다."""
    parent: dict[int, int] = {}

    def find(i: int) -> int:
        if parent.setdefault(i, i) == i:
            return i
        parent[i] = find(parent[i])
        return parent[i]

    def union(i: int, j: int) -> None:
        root_i = find(i)
        root_j = find(j)
        if root_i != root_j:
            parent[root_i] = root_j

    for ev in events:
        if ev.get("type", {}).get("name") == "Substitution":
            p_out = ev.get("player", {}).get("id")
            p_in = ev.get("substitution", {}).get("replacement", {}).get("id")
            if p_out and p_in:
                union(p_out, p_in)

    clusters_map: dict[int, set[int]] = defaultdict(set)
    for p_id in parent:
        clusters_map[find(p_id)].add(p_id)

    return list(clusters_map.values())


def compute_timeline_summary(
    events: list[dict[str, Any]],
    team_id: int,
    lineups: list[dict[str, Any]] | None = None,
    interval_min: int = TIMELINE_INTERVAL_MINUTES,
) -> list[dict[str, Any]]:
    """팀의 Period 기반 15분 단위 전술 타임라인 슬라이스 목록을 산출합니다."""
    # 라인업 정보가 있으면 선수 메타데이터 맵 구성
    players_meta: dict[int, dict[str, Any]] = {}
    if lineups:
        lineup_maps = build_lineup_maps(lineups)
        players_meta = lineup_maps.get(team_id, {}).get("players", {})

    # 경기 내 교체 클러스터 구축 (동일 교체 계통 상호배제용)
    sub_clusters = _build_substitution_clusters(events)

    # 경기 내 최대 Period 확인 (연장전 여부)
    max_period = max((ev.get("period", 1) for ev in events), default=2)

    # 15분 단위 전술 슬라이스 정의 (Period 기반 추가시간 완벽 분리)
    slice_defs: list[dict[str, Any]] = [
        {"period": 1, "min_start": 0, "min_end": 15, "label": "0'-15'"},
        {"period": 1, "min_start": 15, "min_end": 30, "label": "15'-30'"},
        {"period": 1, "min_start": 30, "min_end": 999, "label": "30'-45'+", "display_end": 45},
        {"period": 2, "min_start": 0, "min_end": 60, "label": "45'-60'", "display_start": 45},
        {"period": 2, "min_start": 60, "min_end": 75, "label": "60'-75'"},
        {"period": 2, "min_start": 75, "min_end": 999, "label": "75'-90'+", "display_end": 90},
    ]

    # 연장전(120분) 슬라이스 추가
    if max_period >= 3:
        slice_defs.append(
            {
                "period": 3,
                "min_start": 0,
                "min_end": 999,
                "label": "90'-105'+",
                "display_start": 90,
                "display_end": 105,
            }
        )
    if max_period >= 4:
        slice_defs.append(
            {
                "period": 4,
                "min_start": 0,
                "min_end": 999,
                "label": "105'-120'+",
                "display_start": 105,
                "display_end": 120,
            }
        )

    slices: list[dict[str, Any]] = []

    for i, s_def in enumerate(slice_defs):
        p_target = s_def["period"]
        m_start = s_def["min_start"]
        m_end = s_def["min_end"]

        # Period 및 Minute 조건으로 슬라이스 이벤트 엄격 필터링
        slice_events = [
            ev
            for ev in events
            if ev.get("period") == p_target and m_start <= ev.get("minute", 0) < m_end
        ]

        team_slice_events = [ev for ev in slice_events if ev.get("team", {}).get("id") == team_id]
        total_slice_events_count = len(slice_events)

        # 1. 점유율 계산 (전체 패스/캐리/슈팅 중 해당 팀 비율)
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
                        "jersey_number": p_meta.get("jersey_number"),
                        "position": pos_name,
                    }

        slice_candidates: list[dict[str, Any]] = []
        for pid, coords in player_coords.items():
            avg_x = sum(c[0] for c in coords) / len(coords)
            avg_y = sum(c[1] for c in coords) / len(coords)
            info = player_info_map.get(pid, {})
            slice_candidates.append(
                {
                    "player_id": pid,
                    "player_name": info.get("player_name", "Unknown"),
                    "player_nickname": info.get("player_nickname"),
                    "jersey_number": info.get("jersey_number"),
                    "position": info.get("position", "Player"),
                    "x": round(avg_x, 2),
                    "y": round(avg_y, 2),
                    "event_count": len(coords),
                }
            )

        # 6-1. 교체 체인 기반 상호배제 (동일 교체 계통 선수 경합 시 최다 활동 1인만 선출)
        suppressed_pids: set[int] = set()
        for cluster in sub_clusters:
            competing_in_slice = [p for p in slice_candidates if p["player_id"] in cluster]
            if len(competing_in_slice) >= 2:
                competing_in_slice.sort(key=lambda p: p["event_count"], reverse=True)
                # 1위(승자)를 제외한 나머지 교체 선수들은 이 구간에서 억제
                for loser in competing_in_slice[1:]:
                    suppressed_pids.add(loser["player_id"])

        surviving_players = [p for p in slice_candidates if p["player_id"] not in suppressed_pids]

        # 6-2. 골키퍼 1명 의무 보장 및 필드 플레이어 상위 10명 선별 (총 11명 정원 엄수)
        gk_players: list[dict[str, Any]] = []
        field_players: list[dict[str, Any]] = []

        for p in surviving_players:
            p_meta = players_meta.get(p["player_id"], {})
            pos_id = p_meta.get("primary_position_id")
            pos_name = str(p.get("position", "")).lower()
            if pos_id == 1 or "goalkeeper" in pos_name:
                gk_players.append(p)
            else:
                field_players.append(p)

        # 구간 내 골키퍼 이벤트가 없는 경우 선발 골키퍼를 앵커 위치(x=11.0, y=40.0)로 보장
        selected_gk: dict[str, Any] | None = None
        if gk_players:
            gk_players.sort(key=lambda p: p["event_count"], reverse=True)
            selected_gk = gk_players[0]
        else:
            for p_id, p_info in players_meta.items():
                if (
                    p_info.get("primary_position_id") == 1
                    or p_info.get("primary_position") == "Goalkeeper"
                ):
                    disp_name = p_info.get("player_nickname") or p_info.get(
                        "player_name", "Goalkeeper"
                    )
                    selected_gk = {
                        "player_id": p_id,
                        "player_name": disp_name,
                        "player_nickname": p_info.get("player_nickname"),
                        "jersey_number": p_info.get("jersey_number"),
                        "position": "Goalkeeper",
                        "x": 11.0,
                        "y": 40.0,
                        "event_count": 0,
                    }
                    break

        field_players.sort(key=lambda p: p["event_count"], reverse=True)
        top_field = field_players[:10]

        final_slice_players = ([selected_gk] if selected_gk else []) + top_field
        slice_players = final_slice_players[:11]

        # 7. 구간 내 주요 이벤트 (골, 자책골, 옐로/레드카드)
        key_events = []
        for ev in slice_events:
            ev_type = ev.get("type", {}).get("name", "")
            ev_min = ev.get("minute", 0)
            ev_team_id = ev.get("team", {}).get("id")
            p_name = ev.get("player", {}).get("name", "Unknown")

            if ev_type == "Shot":
                outcome = ev.get("shot", {}).get("outcome", {}).get("name", "")
                if outcome == "Goal":
                    key_events.append(
                        {
                            "type": "Goal",
                            "minute": ev_min,
                            "team_id": ev_team_id,
                            "player": p_name,
                        }
                    )
            elif ev_type == "Own Goal For":
                key_events.append(
                    {
                        "type": "Goal",
                        "minute": ev_min,
                        "team_id": ev_team_id,
                        "player": f"자책골 ({p_name})",
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
                            "minute": ev_min,
                            "team_id": ev_team_id,
                            "player": p_name,
                        }
                    )

        slices.append(
            {
                "slice_index": i,
                "minute_start": s_def.get("display_start", s_def["min_start"]),
                "minute_end": s_def.get(
                    "display_end", s_def["min_end"] if s_def["min_end"] != 999 else 90
                ),
                "label": s_def["label"],
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
