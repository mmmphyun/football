"""StatsBomb 360 하이라이트 10Hz 연속 프레임 보간 및 물리 기반 시퀀스 생성 모듈."""

import math
from typing import Any

from app.analysis.common import build_lineup_maps, event_time
from app.analysis.formation import get_position_anchor
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

    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / seg_len_sq))
    proj_x = ax + t * dx
    proj_y = ay + t * dy
    return math.hypot(px - proj_x, py - proj_y)


def _clamp(val: float, min_v: float, max_v: float) -> float:
    """좌표값을 지정된 범위로 클램핑합니다."""
    return max(min_v, min(val, max_v))


def _lerp(a: float, b: float, t: float) -> float:
    """선형 보간을 수행합니다."""
    return a + (b - a) * t


def format_display_name(player_name: str, nickname: str | None = None) -> str:
    """선수의 공식 닉네임 또는 복합 성명(Compound surname)을 반영한 최적의 표시명을 생성합니다."""
    if nickname and nickname.strip():
        return nickname.strip()
    if not player_name or not player_name.strip():
        return "Unknown"

    parts = player_name.strip().split()
    if len(parts) <= 2:
        return " ".join(parts)

    prefixes = {
        "di", "de", "del", "van", "von", "da", "dos", "la", "le", "al", "el",
        "mac", "mc", "san", "santa",
    }
    for i in range(len(parts) - 1):
        if parts[i].lower() in prefixes:
            return f"{parts[0]} {' '.join(parts[i:])}"

    return f"{parts[0]} {parts[1]}"


def compute_passing_lanes(
    actor_loc: tuple[float, float],
    players: list[dict[str, Any]],
    block_radius: float = PASS_LANE_BLOCK_RADIUS,
    actual_pass_end: tuple[float, float] | None = None,
) -> list[dict[str, Any]]:
    """공을 쥔 선수(actor)로부터 동료 선수들로의 패스 경로에 대해 레이캐스팅을 수행하여 열린/차단된 패스길을 산출합니다."""
    ax, ay = actor_loc
    teammates = [p for p in players if p.get("is_teammate") and not p.get("is_actor") and p.get("opacity", 1.0) >= 0.3]
    opponents = [p for p in players if not p.get("is_teammate") and p.get("opacity", 1.0) >= 0.3]

    lanes: list[dict[str, Any]] = []

    for tm in teammates:
        tm_loc = tm.get("location")
        if not tm_loc or len(tm_loc) < 2:
            continue
        tx, ty = float(tm_loc[0]), float(tm_loc[1])
        dist = round(math.hypot(tx - ax, ty - ay), 2)
        if dist < 1.0:
            continue

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
    """공의 위치(ball_loc)와 선수 포지션에 연동된 볼 중심 동적 포메이션 시프트를 산출합니다."""
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
    fps: int = 10,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], bool]:
    """10Hz 물리 속도 추적, 패서-리시버 앵커링, 관성 외삽 및 볼 중심 동적 시프트가 사전 계산된 10Hz 완성형 프레임을 생성합니다."""
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
    window_has_360 = False

    hl_team_id = highlight.get("team_id") or (all_team_ids[0] if all_team_ids else 0)
    hl_opponent_id = next((t_id for t_id in all_team_ids if t_id != hl_team_id), None)

    # 1. 키프레임 구축 (Anchor Keyframes)
    keyframes: list[dict[str, Any]] = []
    active_tracks: dict[int, dict[str, Any]] = {}
    next_uid = 1

    for frame_idx, ev in enumerate(window_events):
        ev_id = ev.get("id", "")
        t_sec = event_time(ev)
        ev_type = ev.get("type", {}).get("name", "")
        player_name = ev.get("player", {}).get("name")
        player_id = ev.get("player", {}).get("id")
        event_team_id = ev.get("team", {}).get("id") or hl_team_id
        is_opp_event = event_team_id != hl_team_id
        raw_ball_loc = ev.get("location")

        if raw_ball_loc and len(raw_ball_loc) >= 2:
            bx, by = float(raw_ball_loc[0]), float(raw_ball_loc[1])
            ball_loc = [_clamp(bx, 0.0, 120.0), _clamp(by, 0.0, 80.0)]
        else:
            ball_loc = [60.0, 40.0]

        f360 = three_sixty_map.get(ev_id)
        vis_area = []
        frame_raw_players: list[dict[str, Any]] = []

        if f360 is not None:
            window_has_360 = True
            raw_vis = f360.get("visible_area", [])
            vis_area = [_clamp(v, 0.0, 120.0 if i % 2 == 0 else 80.0) for i, v in enumerate(raw_vis)]
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

                # A. Actor
                if target_is_teammate and player_id:
                    actors = [i for i, p in enumerate(ff_cands) if p.get("actor")]
                    if actors:
                        act_idx = actors[0]
                        existing = [uid for uid, trk in prev_cands if trk.get("player_id") == player_id]
                        uid = existing[0] if existing else next_uid
                        if not existing:
                            next_uid += 1

                        matched_ff_idx.add(act_idx)
                        matched_uids.add(uid)
                        floc = ff_cands[act_idx].get("location", ball_loc)
                        cloc = [_clamp(float(floc[0]), 0.0, 120.0), _clamp(float(floc[1]), 0.0, 80.0)]

                        prev_l = active_tracks.get(uid, {}).get("loc", cloc)
                        dt_trk = max(t_sec - active_tracks.get(uid, {}).get("last_time", t_sec - 0.1), 0.001)
                        vx = (cloc[0] - prev_l[0]) / dt_trk
                        vy = (cloc[1] - prev_l[1]) / dt_trk
                        spd = math.hypot(vx, vy)
                        if spd > 9.5:
                            scale = 9.5 / spd
                            vx *= scale
                            vy *= scale

                        p_meta = lineup_maps.get(target_team_id, {}).get("players", {}).get(player_id, {})
                        disp_name = format_display_name(p_meta.get("player_name", ""), p_meta.get("player_nickname"))

                        p_obj = {
                            "uid": uid,
                            "player_id": player_id,
                            "name": disp_name,
                            "team_id": target_team_id,
                            "is_teammate": True,
                            "is_actor": True,
                            "is_keeper": False,
                            "loc": cloc,
                            "vel": [round(vx, 2), round(vy, 2)],
                            "is_inferred": False,
                            "opacity": 1.0,
                        }
                        frame_raw_players.append(p_obj)
                        active_tracks[uid] = {
                            "loc": cloc,
                            "player_id": player_id,
                            "is_teammate": True,
                            "last_time": t_sec,
                            "vel": [vx, vy],
                            "role": "actor",
                            "name": disp_name,
                        }

                # B. Keeper
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

                    p_obj = {
                        "uid": k_uid,
                        "player_id": None,
                        "name": f"{target_team_name} GK",
                        "team_id": target_team_id,
                        "is_teammate": target_is_teammate,
                        "is_actor": False,
                        "is_keeper": True,
                        "loc": cloc,
                        "vel": [0.0, 0.0],
                        "is_inferred": False,
                        "opacity": 1.0,
                    }
                    frame_raw_players.append(p_obj)
                    active_tracks[k_uid] = {
                        "loc": cloc,
                        "player_id": None,
                        "is_teammate": target_is_teammate,
                        "last_time": t_sec,
                        "vel": [0.0, 0.0],
                        "role": "keeper",
                        "name": p_obj["name"],
                    }

                # C. 필드 플레이어 속도 제약 매칭
                unmatched_ff = [i for i in range(len(ff_cands)) if i not in matched_ff_idx]
                unmatched_prev = [(uid, trk) for uid, trk in prev_cands if uid not in matched_uids]

                pair_cands = []
                for fi in unmatched_ff:
                    floc = ff_cands[fi].get("location", [60.0, 40.0])
                    cloc = [_clamp(float(floc[0]), 0.0, 120.0), _clamp(float(floc[1]), 0.0, 80.0)]
                    for uid, trk in unmatched_prev:
                        dt_trk = max(t_sec - trk["last_time"], 0.001)
                        d = math.hypot(cloc[0] - trk["loc"][0], cloc[1] - trk["loc"][1])
                        spd = d / dt_trk
                        if spd <= 10.0:
                            pair_cands.append((d, fi, uid, cloc))

                pair_cands.sort(key=lambda x: x[0])
                for _d, fi, uid, cloc in pair_cands:
                    if fi not in matched_ff_idx and uid not in matched_uids:
                        matched_ff_idx.add(fi)
                        matched_uids.add(uid)

                        prev_l = active_tracks[uid]["loc"]
                        dt_trk = max(t_sec - active_tracks[uid]["last_time"], 0.001)
                        vx = (cloc[0] - prev_l[0]) / dt_trk
                        vy = (cloc[1] - prev_l[1]) / dt_trk
                        spd = math.hypot(vx, vy)
                        if spd > 9.5:
                            scale = 9.5 / spd
                            vx *= scale
                            vy *= scale

                        p_obj = {
                            "uid": uid,
                            "player_id": active_tracks[uid].get("player_id"),
                            "name": active_tracks[uid].get("name", f"{target_team_name} Player #{uid}"),
                            "team_id": target_team_id,
                            "is_teammate": target_is_teammate,
                            "is_actor": False,
                            "is_keeper": False,
                            "loc": cloc,
                            "vel": [round(vx, 2), round(vy, 2)],
                            "is_inferred": False,
                            "opacity": 1.0,
                        }
                        frame_raw_players.append(p_obj)
                        active_tracks[uid] = {
                            "loc": cloc,
                            "player_id": p_obj["player_id"],
                            "name": p_obj["name"],
                            "is_teammate": target_is_teammate,
                            "last_time": t_sec,
                            "vel": [vx, vy],
                            "role": "field",
                        }

                # D. 신규 진입 선수
                for fi in unmatched_ff:
                    if fi not in matched_ff_idx:
                        new_uid = next_uid
                        next_uid += 1
                        floc = ff_cands[fi].get("location", [60.0, 40.0])
                        cloc = [_clamp(float(floc[0]), 0.0, 120.0), _clamp(float(floc[1]), 0.0, 80.0)]
                        p_obj = {
                            "uid": new_uid,
                            "player_id": None,
                            "name": f"{target_team_name} Player #{new_uid}",
                            "team_id": target_team_id,
                            "is_teammate": target_is_teammate,
                            "is_actor": False,
                            "is_keeper": False,
                            "loc": cloc,
                            "vel": [0.0, 0.0],
                            "is_inferred": False,
                            "opacity": 1.0,
                        }
                        frame_raw_players.append(p_obj)
                        active_tracks[new_uid] = {
                            "loc": cloc,
                            "player_id": None,
                            "name": p_obj["name"],
                            "is_teammate": target_is_teammate,
                            "last_time": t_sec,
                            "vel": [0.0, 0.0],
                            "role": "field",
                        }

        # 22명 볼 중심 동적 가상 추론 (결측 포지션 1:1 보충)
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
                    "uid": next_uid,
                    "player_id": p_id,
                    "name": disp_name,
                    "team_id": hl_team_id,
                    "is_teammate": True,
                    "is_actor": False,
                    "is_keeper": (pos_id == 1),
                    "loc": [shifted_loc[0], shifted_loc[1]],
                    "vel": [0.0, 0.0],
                    "is_inferred": True,
                    "opacity": 0.45,
                }
            )
            next_uid += 1

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
                        "uid": next_uid,
                        "player_id": p_id,
                        "name": disp_name,
                        "team_id": hl_opponent_id,
                        "is_teammate": False,
                        "is_actor": False,
                        "is_keeper": (pos_id == 1),
                        "loc": [shifted_loc[0], shifted_loc[1]],
                        "vel": [0.0, 0.0],
                        "is_inferred": True,
                        "opacity": 0.45,
                    }
                )
                next_uid += 1

        # 팀당 11명 상한 정규화
        t_players = [p for p in frame_raw_players if p.get("is_teammate")][:11]
        o_players = [p for p in frame_raw_players if not p.get("is_teammate")][:11]

        keyframes.append(
            {
                "index": frame_idx,
                "event_id": ev_id,
                "event_type": ev_type,
                "player_name": player_name,
                "player_id": player_id,
                "team_id": event_team_id,
                "team_name": ev.get("team", {}).get("name", ""),
                "timestamp_sec": t_sec,
                "minute": ev.get("minute", 0),
                "second": ev.get("second", 0),
                "ball_loc": ball_loc,
                "pass_info": ev.get("pass"),
                "shot_info": ev.get("shot"),
                "visible_area": vis_area,
                "players": t_players + o_players,
                "description": _build_frame_description(ev),
            }
        )

    if not keyframes:
        return [], all_players, False

    # 2. 10Hz 연속 보간 및 완성형 프레임 시퀀스 생성
    start_t = keyframes[0]["timestamp_sec"]
    last_k = keyframes[-1]
    shot_duration = float(last_k.get("shot_info", {}).get("duration", 0.5))
    end_t = last_k["timestamp_sec"] + (shot_duration if last_k["event_type"] == "Shot" else 0.5)

    dt_step = 1.0 / fps
    total_steps = int(math.ceil((end_t - start_t) / dt_step)) + 1
    interpolated_frames: list[dict[str, Any]] = []

    for step in range(total_steps):
        cur_t = round(start_t + step * dt_step, 2)

        k_prev = keyframes[0]
        k_next = keyframes[-1]
        for k in range(len(keyframes) - 1):
            if keyframes[k]["timestamp_sec"] <= cur_t <= keyframes[k + 1]["timestamp_sec"]:
                k_prev = keyframes[k]
                k_next = keyframes[k + 1]
                break

        is_shot_phase = cur_t >= keyframes[-1]["timestamp_sec"] and keyframes[-1]["event_type"] == "Shot"

        # A. 공 위치 보간
        if is_shot_phase and keyframes[-1].get("shot_info", {}).get("end_location"):
            shot_t_offset = min(cur_t - keyframes[-1]["timestamp_sec"], shot_duration)
            alpha_shot = shot_t_offset / shot_duration if shot_duration > 0 else 1.0
            p_start = keyframes[-1]["ball_loc"]
            p_end = keyframes[-1]["shot_info"]["end_location"][:2]
            ball_pos = [
                _clamp(p_start[0] + alpha_shot * (p_end[0] - p_start[0]), 0.0, 120.0),
                _clamp(p_start[1] + alpha_shot * (p_end[1] - p_start[1]), 0.0, 80.0),
            ]
            alpha = 1.0
        else:
            seg_dt = max(k_next["timestamp_sec"] - k_prev["timestamp_sec"], 0.0001)
            alpha = min(max((cur_t - k_prev["timestamp_sec"]) / seg_dt, 0.0), 1.0)

            if k_prev["event_type"] == "Pass" and k_prev.get("pass_info", {}).get("end_location"):
                p_start = k_prev["ball_loc"]
                p_end = k_prev["pass_info"]["end_location"]
                ball_pos = [
                    _clamp(p_start[0] + alpha * (p_end[0] - p_start[0]), 0.0, 120.0),
                    _clamp(p_start[1] + alpha * (p_end[1] - p_start[1]), 0.0, 80.0),
                ]
            else:
                ball_pos = [
                    _clamp(k_prev["ball_loc"][0] + alpha * (k_next["ball_loc"][0] - k_prev["ball_loc"][0]), 0.0, 120.0),
                    _clamp(k_prev["ball_loc"][1] + alpha * (k_next["ball_loc"][1] - k_prev["ball_loc"][1]), 0.0, 80.0),
                ]

        # B. 선수 위치 보간 및 관성 감속 페이드아웃
        prev_p_map = {p.get("player_id") or p.get("uid"): p for p in k_prev["players"]}
        next_p_map = {p.get("player_id") or p.get("uid"): p for p in k_next["players"]}
        passer_player_id = k_prev.get("player_id") if k_prev["event_type"] == "Pass" else None

        all_keys = set(prev_p_map.keys()) | set(next_p_map.keys())
        frame_interp_players: list[dict[str, Any]] = []

        for p_key in all_keys:
            p1 = prev_p_map.get(p_key)
            p2 = next_p_map.get(p_key)

            if p1 and p2:
                pos = [
                    _clamp(p1["loc"][0] + alpha * (p2["loc"][0] - p1["loc"][0]), 0.0, 120.0),
                    _clamp(p1["loc"][1] + alpha * (p2["loc"][1] - p1["loc"][1]), 0.0, 80.0),
                ]
                op = _lerp(p1.get("opacity", 1.0), p2.get("opacity", 1.0), alpha)
                frame_interp_players.append(
                    {
                        "player_id": p1.get("player_id"),
                        "name": p1.get("name"),
                        "team_id": p1.get("team_id"),
                        "is_teammate": p1.get("is_teammate"),
                        "is_actor": p1.get("is_actor") if alpha < 0.5 else p2.get("is_actor"),
                        "is_keeper": p1.get("is_keeper"),
                        "location": [round(pos[0], 2), round(pos[1], 2)],
                        "velocity": p1.get("vel", [0.0, 0.0]),
                        "pred_location": [
                            round(_clamp(pos[0] + p1.get("vel", [0, 0])[0] * 1.5, 0.0, 120.0), 2),
                            round(_clamp(pos[1] + p1.get("vel", [0, 0])[1] * 1.5, 0.0, 80.0), 2),
                        ],
                        "is_inferred": p1.get("is_inferred", False),
                        "opacity": round(op, 2),
                    }
                )
            elif p1 and not p2:
                is_passer = passer_player_id and p1.get("player_id") == passer_player_id
                elapsed = cur_t - k_prev["timestamp_sec"]
                vx, vy = p1.get("vel", [0.0, 0.0])
                drag = max(1.0 - (elapsed / 2.0), 0.2)
                pos = [
                    _clamp(p1["loc"][0] + vx * elapsed * drag, 0.0, 120.0),
                    _clamp(p1["loc"][1] + vy * elapsed * drag, 0.0, 80.0),
                ]
                opacity = 1.0 if is_passer else max(1.0 - (elapsed / 1.2), 0.0)
                if opacity > 0.05:
                    frame_interp_players.append(
                        {
                            "player_id": p1.get("player_id"),
                            "name": p1.get("name"),
                            "team_id": p1.get("team_id"),
                            "is_teammate": p1.get("is_teammate"),
                            "is_actor": p1.get("is_actor"),
                            "is_keeper": p1.get("is_keeper"),
                            "location": [round(pos[0], 2), round(pos[1], 2)],
                            "velocity": p1.get("vel", [0.0, 0.0]),
                            "pred_location": None,
                            "is_inferred": p1.get("is_inferred", False),
                            "opacity": round(opacity, 2),
                        }
                    )
            elif p2 and not p1:
                until_in = k_next["timestamp_sec"] - cur_t
                opacity = min(max(1.0 - (until_in / 0.8), 0.1), 1.0)
                vx, vy = p2.get("vel", [0.0, 0.0])
                pos = [
                    _clamp(p2["loc"][0] - vx * until_in, 0.0, 120.0),
                    _clamp(p2["loc"][1] - vy * until_in, 0.0, 80.0),
                ]
                frame_interp_players.append(
                    {
                        "player_id": p2.get("player_id"),
                        "name": p2.get("name"),
                        "team_id": p2.get("team_id"),
                        "is_teammate": p2.get("is_teammate"),
                        "is_actor": p2.get("is_actor"),
                        "is_keeper": p2.get("is_keeper"),
                        "location": [round(pos[0], 2), round(pos[1], 2)],
                        "velocity": p2.get("vel", [0.0, 0.0]),
                        "pred_location": None,
                        "is_inferred": p2.get("is_inferred", False),
                        "opacity": round(opacity, 2),
                    }
                )

        # 리시버 앵커링: 패스 구간 동안 리시버가 공을 받으러 달려오는 궤적 보장
        if k_prev["event_type"] == "Pass" and k_next["event_type"] == "Ball Receipt*":
            recip_id = k_next.get("player_id")
            recip_name = k_next.get("player_name")
            if recip_id and not any(p.get("player_id") == recip_id for p in frame_interp_players):
                end_l = k_prev["pass_info"]["end_location"]
                start_apx = [max(end_l[0] - 10.0, 0.0), end_l[1]]
                run_x = start_apx[0] + alpha * (end_l[0] - start_apx[0])
                run_y = start_apx[1] + alpha * (end_l[1] - start_apx[1])
                frame_interp_players.append(
                    {
                        "player_id": recip_id,
                        "name": recip_name,
                        "team_id": hl_team_id,
                        "is_teammate": True,
                        "is_actor": True,
                        "is_keeper": False,
                        "location": [round(_clamp(run_x, 0.0, 120.0), 2), round(_clamp(run_y, 0.0, 80.0), 2)],
                        "velocity": [round((end_l[0] - start_apx[0]) / max(seg_dt, 0.1), 2), 0.0],
                        "pred_location": [round(end_l[0], 2), round(end_l[1], 2)],
                        "is_inferred": False,
                        "opacity": round(min(0.4 + 0.6 * alpha, 1.0), 2),
                    }
                )

        # 팀당 11명 상한 필터링
        tm_fin = [p for p in frame_interp_players if p.get("is_teammate")][:11]
        opp_fin = [p for p in frame_interp_players if not p.get("is_teammate")][:11]
        final_players = tm_fin + opp_fin

        # 360 패스길 레이캐스팅 산출
        actor_player = next((p for p in final_players if p.get("is_actor")), None)
        if actor_player and actor_player.get("location"):
            a_loc = (float(actor_player["location"][0]), float(actor_player["location"][1]))
        else:
            a_loc = (float(ball_pos[0]), float(ball_pos[1]))

        actual_pass_end = None
        if k_prev.get("event_type") == "Pass" and k_prev.get("pass_info", {}).get("end_location"):
            end_l = k_prev["pass_info"]["end_location"]
            actual_pass_end = (float(end_l[0]), float(end_l[1]))

        passing_lanes = compute_passing_lanes(
            actor_loc=a_loc,
            players=final_players,
            actual_pass_end=actual_pass_end,
        )

        min_val = int(cur_t // 60)
        sec_val = int(cur_t % 60)

        frame_data = {
            "frame_index": step,
            "event_index": k_prev["index"],
            "event_id": k_prev["event_id"],
            "event_type": k_prev["event_type"],
            "minute": min_val,
            "second": sec_val,
            "timestamp_sec": cur_t,
            "period": k_prev.get("period", 1),
            "ball_location": [round(ball_pos[0], 2), round(ball_pos[1], 2)],
            "visible_area": k_prev.get("visible_area", []),
            "players": final_players,
            "passing_lanes": passing_lanes,
            "description": k_prev["description"],
            "team_id": k_prev["team_id"],
            "team_name": k_prev["team_name"],
        }
        interpolated_frames.append(frame_data)

    return interpolated_frames, all_players, window_has_360


