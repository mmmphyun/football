"""360 트래킹 프레임 시퀀스 빌더 및 가상 추론 모듈."""

import math
from typing import Any

from app.analysis.common import build_lineup_maps, event_time
from app.analysis.formation import get_position_anchor
from app.analysis.predict import extrapolate_frame_players
from app.config import PASS_LANE_BLOCK_RADIUS


def _point_to_segment_distance(
    px: float,
    py: float,
    ax: float,
    ay: float,
    bx: float,
    by: float,
) -> float:
    """점 P(px, py)와 선분 AB 사이의 최단 유클리드 거리를 계산합니다."""
    dx = bx - ax
    dy = by - ay
    seg_len_sq = dx * dx + dy * dy
    if seg_len_sq < 1e-6:
        return math.hypot(px - ax, py - ay)

    # 선분 투영 매개변수 t 계산 (0 <= t <= 1 클램핑)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / seg_len_sq))
    proj_x = ax + t * dx
    proj_y = ay + t * dy
    return math.hypot(px - proj_x, py - proj_y)


def _clamp(val: float, min_v: float, max_v: float) -> float:
    """좌표값을 지정된 범위로 클램핑합니다."""
    return max(min_v, min(val, max_v))


def format_display_name(player_name: str, nickname: str | None = None) -> str:
    """선수의 공식 닉네임 또는 복합 성명(Compound surname)을 반영한 최적의 표시명을 생성합니다."""
    if nickname and nickname.strip():
        return nickname.strip()
    if not player_name or not player_name.strip():
        return "Unknown"

    parts = player_name.strip().split()
    if len(parts) <= 2:
        return " ".join(parts)

    # 스페인/포르투갈/네덜란드/스코틀랜드 등 전치사 결합 복합 성 처리 (Di María, De Paul, Van Dijk, Mac Allister 등)
    prefixes = {"di", "de", "del", "van", "von", "da", "dos", "la", "le", "al", "el", "mac", "mc", "san", "santa"}
    for i in range(len(parts) - 1):
        if parts[i].lower() in prefixes:
            return f"{parts[0]} {' '.join(parts[i:])}"

    # 기본: 첫 이름 + 첫 번째 주요 성 (부계 성)
    return f"{parts[0]} {parts[1]}"


def compute_passing_lanes(
    actor_loc: tuple[float, float],
    players: list[dict[str, Any]],
    block_radius: float = PASS_LANE_BLOCK_RADIUS,
    actual_pass_end: tuple[float, float] | None = None,
) -> list[dict[str, Any]]:
    """공을 쥔 선수(actor)로부터 동료 선수들로의 패스 경로에 대해 레이캐스팅을 수행하여 열린/차단된 패스길을 산출합니다."""
    ax, ay = actor_loc
    teammates = [p for p in players if p.get("is_teammate") and not p.get("is_actor")]
    opponents = [p for p in players if not p.get("is_teammate")]

    lanes: list[dict[str, Any]] = []

    for tm in teammates:
        tm_loc = tm.get("location")
        if not tm_loc or len(tm_loc) < 2:
            continue
        tx, ty = float(tm_loc[0]), float(tm_loc[1])
        dist = round(math.hypot(tx - ax, ty - ay), 2)
        if dist < 1.0:
            continue

        # 상대 수비수가 패스 경로 반경 내에 존재하는지 레이캐스팅 검사
        is_open = True
        blocking_player_id = None
        min_clearance = 999.0

        for opp in opponents:
            opp_loc = opp.get("location")
            if not opp_loc or len(opp_loc) < 2:
                continue
            ox, oy = float(opp_loc[0]), float(opp_loc[1])
            d_to_lane = _point_to_segment_distance(ox, oy, ax, ay, tx, ty)
            if d_to_lane < min_clearance:
                min_clearance = d_to_lane

            if d_to_lane <= block_radius:
                is_open = False
                blocking_player_id = opp.get("player_id")

        # 실제 선택된 패스 궤적인지 여부
        is_selected = False
        if actual_pass_end is not None:
            ex, ey = actual_pass_end
            if math.hypot(tx - ex, ty - ey) <= 4.0:
                is_selected = True

        lanes.append(
            {
                "from_location": [_clamp(round(ax, 2), 0.0, 120.0), _clamp(round(ay, 2), 0.0, 80.0)],
                "to_location": [_clamp(round(tx, 2), 0.0, 120.0), _clamp(round(ty, 2), 0.0, 80.0)],
                "target_player_id": tm.get("player_id"),
                "is_open": is_open,
                "is_selected": is_selected,
                "distance": dist,
                "clearance": round(min_clearance, 2) if min_clearance < 900.0 else None,
                "blocking_player_id": blocking_player_id,
            }
        )

    return lanes


def _build_frame_description(ev: dict[str, Any]) -> str:
    """이벤트로부터 프레임 설명 문자열을 생성합니다."""
    team_name = ev.get("team", {}).get("name", "")
    player_name = ev.get("player", {}).get("name", "")
    type_name = ev.get("type", {}).get("name", "")

    if player_name:
        return f"{team_name} - {player_name} ({type_name})"
    if team_name:
        return f"{team_name} ({type_name})"
    return type_name


def _compute_ball_centric_shift(
    base_anchor: tuple[float, float],
    ball_loc: tuple[float, float],
    is_teammate: bool,
    pos_id: int | None,
) -> tuple[float, float]:
    """공의 위치(ball_loc)와 선수 포지션에 연동된 볼 중심 동적 포메이션 시프트를 산출합니다.

    - X축: 공의 전진에 따라 수비/미드필드/공격 라인이 비례하여 전진/후퇴 (컴팩트니스 유지)
    - Y축: 공이 위치한 측면으로 팀 전체 대형 슬라이드 및 반대편 커버
    """
    bx, by = ball_loc
    ax, ay = base_anchor

    if is_teammate:
        x_shift = (bx - 60.0) * 0.40
        if pos_id == 1:
            x_shift = max(-2.0, min(10.0, x_shift * 0.3))
        elif pos_id in {2, 3, 4, 5, 6, 7, 8}:
            x_shift = max(-12.0, min(25.0, x_shift * 0.65))
        elif pos_id in {9, 10, 11, 12, 13, 14, 15, 16}:
            x_shift = max(-15.0, min(25.0, x_shift * 0.85))
        else:
            x_shift = max(-15.0, min(20.0, x_shift * 0.70))

        y_shift = (by - 40.0) * 0.20
        if (ay < 40.0 and by > 40.0) or (ay > 40.0 and by < 40.0):
            y_shift *= 1.35

        final_x = _clamp(ax + x_shift, 4.0, 116.0)
        final_y = _clamp(ay + y_shift, 4.0, 76.0)
        return (round(final_x, 2), round(final_y, 2))
    else:
        opp_base_x = 120.0 - ax
        opp_base_y = 80.0 - ay

        x_shift = (bx - 60.0) * 0.35
        if pos_id == 1:
            x_shift = max(-8.0, min(5.0, x_shift * 0.2))
        elif pos_id in {2, 3, 4, 5, 6, 7, 8}:
            x_shift = max(-20.0, min(15.0, x_shift * 0.6))
        else:
            x_shift = max(-20.0, min(20.0, x_shift * 0.8))

        y_shift = (by - 40.0) * 0.20
        final_x = _clamp(opp_base_x + x_shift, 4.0, 116.0)
        final_y = _clamp(opp_base_y + y_shift, 4.0, 76.0)
        return (round(final_x, 2), round(final_y, 2))


def build_highlight_frames(
    events: list[dict[str, Any]],
    three_sixty_frames: list[dict[str, Any]] | None,
    lineups: list[dict[str, Any]],
    highlight: dict[str, Any],
    formation_anchors: dict[int, Any] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], bool]:
    """물리 속도 제약 추적, 패서-리시버 앵커링, 볼 중심 동적 가상 추론이 적용된 360 프레임 시퀀스를 생성합니다."""
    start_idx = int(highlight.get("start_event", 0))
    end_idx = int(highlight.get("end_event", len(events) - 1))

    start_idx = max(0, min(start_idx, len(events) - 1))
    end_idx = max(start_idx, min(end_idx, len(events) - 1))

    three_sixty_map: dict[str, dict[str, Any]] = {}
    if three_sixty_frames:
        for f360 in three_sixty_frames:
            ev_uuid = f360.get("event_uuid")
            if ev_uuid:
                three_sixty_map[ev_uuid] = f360

    lineup_maps = build_lineup_maps(lineups)
    all_team_ids = list(lineup_maps.keys())

    all_players: list[dict[str, Any]] = []
    for team_id, team_info in lineup_maps.items():
        for p_id, p_info in team_info.get("players", {}).items():
            full_name = p_info.get("player_name", "")
            nickname = p_info.get("player_nickname")
            disp_name = format_display_name(full_name, nickname)
            all_players.append(
                {
                    "player_id": p_id,
                    "team_id": team_id,
                    "team_name": team_info.get("team_name", ""),
                    "player_name": disp_name,
                    "full_name": full_name,
                    "player_nickname": nickname,
                    "jersey_number": p_info.get("jersey_number"),
                    "is_starter": p_info.get("is_starter", False),
                    "primary_position": p_info.get("primary_position"),
                    "primary_position_id": p_info.get("primary_position_id"),
                }
            )

    window_events = events[start_idx : end_idx + 1]
    frames: list[dict[str, Any]] = []
    window_has_360 = False

    hl_team_id = highlight.get("team_id") or (all_team_ids[0] if all_team_ids else 0)
    hl_opponent_id = next((t_id for t_id in all_team_ids if t_id != hl_team_id), None)

    active_tracks: dict[int, dict[str, Any]] = {}
    next_uid = 1

    prev_t_sec: float | None = None

    for frame_idx, ev in enumerate(window_events):
        ev_id = ev.get("id", "")
        ev_idx = start_idx + frame_idx
        t_sec = event_time(ev)
        dt = max((t_sec - prev_t_sec) if (prev_t_sec is not None) else 0.1, 0.001)

        f360 = three_sixty_map.get(ev_id)
        raw_ball_loc = ev.get("location")
        actor_player_id = ev.get("player", {}).get("id")
        ev_team_id = ev.get("team", {}).get("id") or hl_team_id
        is_opp_event = ev_team_id != hl_team_id

        if raw_ball_loc and len(raw_ball_loc) >= 2:
            bx, by = float(raw_ball_loc[0]), float(raw_ball_loc[1])
            ball_loc = [_clamp(bx, 0.0, 120.0), _clamp(by, 0.0, 80.0)]
        else:
            ball_loc = [60.0, 40.0]

        visible_area: list[float] = []
        frame_raw_players: list[dict[str, Any]] = []

        if f360 is not None:
            window_has_360 = True
            raw_vis = f360.get("visible_area", [])
            visible_area = [_clamp(v, 0.0, 120.0 if i % 2 == 0 else 80.0) for i, v in enumerate(raw_vis)]
            freeze_players = f360.get("freeze_frame", [])

            for target_is_teammate in [True, False]:
                target_team_id = hl_team_id if target_is_teammate else hl_opponent_id
                target_team_name = (
                    lineup_maps.get(target_team_id, {}).get("team_name", "Team")
                    if target_team_id
                    else "Opponent"
                )

                ff_cands = []
                for fp in freeze_players:
                    raw_tm = bool(fp.get("teammate", False))
                    mapped_tm = raw_tm if not is_opp_event else not raw_tm
                    if mapped_tm == target_is_teammate:
                        ff_cands.append(fp)

                prev_cands = [
                    (uid, trk)
                    for uid, trk in active_tracks.items()
                    if trk.get("is_teammate") == target_is_teammate and (t_sec - trk["last_time"]) <= 4.0
                ]

                matched_ff_idx = set()
                matched_uids = set()

                if target_is_teammate and actor_player_id:
                    actors = [i for i, p in enumerate(ff_cands) if p.get("actor")]
                    if actors:
                        act_idx = actors[0]
                        existing = [uid for uid, trk in prev_cands if trk.get("player_id") == actor_player_id]
                        uid = existing[0] if existing else next_uid
                        if not existing:
                            next_uid += 1

                        matched_ff_idx.add(act_idx)
                        matched_uids.add(uid)

                        floc = ff_cands[act_idx].get("location", ball_loc)
                        cloc = [_clamp(float(floc[0]), 0.0, 120.0), _clamp(float(floc[1]), 0.0, 80.0)]

                        prev_l = active_tracks.get(uid, {}).get("loc", cloc)
                        vx = (cloc[0] - prev_l[0]) / dt
                        vy = (cloc[1] - prev_l[1]) / dt
                        spd = math.hypot(vx, vy)
                        if spd > 9.5:
                            scale = 9.5 / spd
                            vx *= scale
                            vy *= scale

                        p_meta = lineup_maps.get(target_team_id, {}).get("players", {}).get(actor_player_id, {})
                        disp_name = format_display_name(p_meta.get("player_name", ""), p_meta.get("player_nickname"))

                        p_entry = {
                            "player_id": actor_player_id,
                            "name": disp_name,
                            "location": cloc,
                            "is_actor": True,
                            "is_teammate": True,
                            "is_keeper": False,
                            "vx": round(vx, 2),
                            "vy": round(vy, 2),
                            "velocity": [round(vx, 2), round(vy, 2)],
                            "is_inferred": False,
                            "opacity": 1.0,
                            "uid": uid,
                        }
                        frame_raw_players.append(p_entry)
                        active_tracks[uid] = {
                            "loc": cloc,
                            "player_id": actor_player_id,
                            "is_teammate": True,
                            "last_time": t_sec,
                            "vel": [vx, vy],
                            "role": "actor",
                        }

                keepers = [i for i, p in enumerate(ff_cands) if p.get("keeper")]
                if keepers and (keepers[0] not in matched_ff_idx):
                    k_idx = keepers[0]
                    existing_k = [uid for uid, trk in prev_cands if trk.get("role") == "keeper"]
                    k_uid = existing_k[0] if existing_k else next_uid
                    if not existing_k:
                        next_uid += 1

                    matched_ff_idx.add(k_idx)
                    matched_uids.add(k_uid)

                    floc = ff_cands[k_idx].get("location", [6.0, 40.0])
                    cloc = [_clamp(float(floc[0]), 0.0, 120.0), _clamp(float(floc[1]), 0.0, 80.0)]

                    p_entry = {
                        "player_id": None,
                        "name": f"{target_team_name} GK",
                        "location": cloc,
                        "is_actor": False,
                        "is_teammate": target_is_teammate,
                        "is_keeper": True,
                        "vx": 0.0,
                        "vy": 0.0,
                        "velocity": [0.0, 0.0],
                        "is_inferred": False,
                        "opacity": 1.0,
                        "uid": k_uid,
                    }
                    frame_raw_players.append(p_entry)
                    active_tracks[k_uid] = {
                        "loc": cloc,
                        "player_id": None,
                        "is_teammate": target_is_teammate,
                        "last_time": t_sec,
                        "vel": [0.0, 0.0],
                        "role": "keeper",
                    }

                unmatched_ff = [i for i in range(len(ff_cands)) if i not in matched_ff_idx]
                unmatched_prev = [(uid, trk) for uid, trk in prev_cands if uid not in matched_uids]

                pair_cands = []
                for fi in unmatched_ff:
                    floc = ff_cands[fi].get("location", [60.0, 40.0])
                    cloc = [_clamp(float(floc[0]), 0.0, 120.0), _clamp(float(floc[1]), 0.0, 80.0)]
                    for uid, trk in unmatched_prev:
                        d = math.hypot(cloc[0] - trk["loc"][0], cloc[1] - trk["loc"][1])
                        spd = d / dt
                        if spd <= 10.0:
                            pair_cands.append((d, fi, uid, cloc))

                pair_cands.sort(key=lambda x: x[0])
                for _d, fi, uid, cloc in pair_cands:
                    if fi not in matched_ff_idx and uid not in matched_uids:
                        matched_ff_idx.add(fi)
                        matched_uids.add(uid)

                        prev_l = active_tracks[uid]["loc"]
                        vx = (cloc[0] - prev_l[0]) / dt
                        vy = (cloc[1] - prev_l[1]) / dt
                        spd = math.hypot(vx, vy)
                        if spd > 9.5:
                            scale = 9.5 / spd
                            vx *= scale
                            vy *= scale

                        p_entry = {
                            "player_id": active_tracks[uid].get("player_id"),
                            "name": active_tracks[uid].get("name", f"{target_team_name} Player #{uid}"),
                            "location": cloc,
                            "is_actor": False,
                            "is_teammate": target_is_teammate,
                            "is_keeper": False,
                            "vx": round(vx, 2),
                            "vy": round(vy, 2),
                            "velocity": [round(vx, 2), round(vy, 2)],
                            "is_inferred": False,
                            "opacity": 1.0,
                            "uid": uid,
                        }
                        frame_raw_players.append(p_entry)
                        active_tracks[uid] = {
                            "loc": cloc,
                            "player_id": p_entry["player_id"],
                            "name": p_entry["name"],
                            "is_teammate": target_is_teammate,
                            "last_time": t_sec,
                            "vel": [vx, vy],
                            "role": "field",
                        }

                for fi in unmatched_ff:
                    if fi not in matched_ff_idx:
                        new_uid = next_uid
                        next_uid += 1
                        floc = ff_cands[fi].get("location", [60.0, 40.0])
                        cloc = [_clamp(float(floc[0]), 0.0, 120.0), _clamp(float(floc[1]), 0.0, 80.0)]
                        p_entry = {
                            "player_id": None,
                            "name": f"{target_team_name} Player #{new_uid}",
                            "location": cloc,
                            "is_actor": False,
                            "is_teammate": target_is_teammate,
                            "is_keeper": False,
                            "vx": 0.0,
                            "vy": 0.0,
                            "velocity": [0.0, 0.0],
                            "is_inferred": False,
                            "opacity": 1.0,
                            "uid": new_uid,
                        }
                        frame_raw_players.append(p_entry)
                        active_tracks[new_uid] = {
                            "loc": cloc,
                            "player_id": None,
                            "name": p_entry["name"],
                            "is_teammate": target_is_teammate,
                            "last_time": t_sec,
                            "vel": [0.0, 0.0],
                            "role": "field",
                        }

        # ---------------------------------------------------------------------
        # 22명 가상 추론: 볼 중심 동적 포메이션 시프트 & 결측 포지션 1:1 보충
        # ---------------------------------------------------------------------
        home_team_info = lineup_maps.get(hl_team_id, {})
        home_starters = home_team_info.get("starting_xi", [])
        home_players_meta = home_team_info.get("players", {})

        assigned_player_ids = {p["player_id"] for p in frame_raw_players if p.get("player_id")}
        present_teammates = sum(1 for p in frame_raw_players if p.get("is_teammate"))

        missing_starters = [pid for pid in home_starters if pid not in assigned_player_ids]
        needed_count = max(0, 11 - present_teammates)

        for p_id in missing_starters[:needed_count]:
            p_meta = home_players_meta.get(p_id, {})
            pos_id = p_meta.get("primary_position_id")
            base_anchor = get_position_anchor(pos_id)
            shifted_loc = _compute_ball_centric_shift(
                base_anchor=base_anchor,
                ball_loc=(ball_loc[0], ball_loc[1]),
                is_teammate=True,
                pos_id=pos_id,
            )
            disp_name = format_display_name(p_meta.get("player_name", ""), p_meta.get("player_nickname"))

            frame_raw_players.append(
                {
                    "player_id": p_id,
                    "name": disp_name,
                    "location": [shifted_loc[0], shifted_loc[1]],
                    "is_actor": False,
                    "is_teammate": True,
                    "is_keeper": (pos_id == 1),
                    "vx": 0.0,
                    "vy": 0.0,
                    "velocity": [0.0, 0.0],
                    "is_inferred": True,
                    "opacity": 0.45,
                }
            )

        if hl_opponent_id:
            opp_team_info = lineup_maps.get(hl_opponent_id, {})
            opp_starters = opp_team_info.get("starting_xi", [])
            opp_players_meta = opp_team_info.get("players", {})
            present_opponents = sum(1 for p in frame_raw_players if not p.get("is_teammate"))
            missing_opp = [pid for pid in opp_starters if pid not in assigned_player_ids]
            needed_opp_count = max(0, 11 - present_opponents)

            for p_id in missing_opp[:needed_opp_count]:
                p_meta = opp_players_meta.get(p_id, {})
                pos_id = p_meta.get("primary_position_id")
                base_anchor = get_position_anchor(pos_id)
                shifted_loc = _compute_ball_centric_shift(
                    base_anchor=base_anchor,
                    ball_loc=(ball_loc[0], ball_loc[1]),
                    is_teammate=False,
                    pos_id=pos_id,
                )
                disp_name = format_display_name(p_meta.get("player_name", ""), p_meta.get("player_nickname"))

                frame_raw_players.append(
                    {
                        "player_id": p_id,
                        "name": disp_name,
                        "location": [shifted_loc[0], shifted_loc[1]],
                        "is_actor": False,
                        "is_teammate": False,
                        "is_keeper": (pos_id == 1),
                        "vx": 0.0,
                        "vy": 0.0,
                        "velocity": [0.0, 0.0],
                        "is_inferred": True,
                        "opacity": 0.45,
                    }
                )

        t_players = [p for p in frame_raw_players if p.get("is_teammate")]
        o_players = [p for p in frame_raw_players if not p.get("is_teammate")]
        final_players = t_players[:11] + o_players[:11]

        extrapolated_players = extrapolate_frame_players(final_players, dt=2.0)

        actor_player = next((p for p in final_players if p.get("is_actor")), None)
        if actor_player and actor_player.get("location"):
            a_loc = (float(actor_player["location"][0]), float(actor_player["location"][1]))
        elif ball_loc:
            a_loc = (float(ball_loc[0]), float(ball_loc[1]))
        else:
            a_loc = (60.0, 40.0)

        actual_pass_end = None
        if ev.get("type", {}).get("name") == "Pass":
            end_l = ev.get("pass", {}).get("end_location")
            if end_l and len(end_l) >= 2:
                actual_pass_end = (float(end_l[0]), float(end_l[1]))

        passing_lanes = compute_passing_lanes(
            actor_loc=a_loc,
            players=final_players,
            actual_pass_end=actual_pass_end,
        )

        frame_data = {
            "frame_index": frame_idx,
            "event_index": ev_idx,
            "event_id": ev_id,
            "event_type": ev.get("type", {}).get("name", ""),
            "minute": ev.get("minute", 0),
            "second": ev.get("second", 0),
            "timestamp_sec": round(t_sec, 2),
            "period": ev.get("period", 1),
            "ball_location": ball_loc,
            "visible_area": visible_area,
            "players": extrapolated_players,
            "passing_lanes": passing_lanes,
            "description": _build_frame_description(ev),
            "team_id": ev_team_id,
            "team_name": ev.get("team", {}).get("name", ""),
        }
        frames.append(frame_data)
        prev_t_sec = t_sec

    return frames, all_players, window_has_360

