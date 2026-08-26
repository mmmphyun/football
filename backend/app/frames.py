"""360 트래킹 프레임 시퀀스 빌더 및 외삽 연동 모듈."""

from typing import Any

from app.analysis.common import build_lineup_maps, event_time
from app.analysis.formation import get_position_anchor
from app.analysis.predict import calculate_velocity, extrapolate_frame_players


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


def build_highlight_frames(
    events: list[dict[str, Any]],
    three_sixty_frames: list[dict[str, Any]] | None,
    lineups: list[dict[str, Any]],
    highlight: dict[str, Any],
    formation_anchors: dict[int, dict[int, tuple[float, float]]] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], bool]:
    """하이라이트 이벤트 윈도우에 대한 360 위치/속도/외삽 프레임 시퀀스를 구성합니다.

    Returns:
        tuple[frames, players_list, has_360]:
            - frames: 시간순 프레임 목록 (각 프레임에 선수/공/시야각/외삽 포함)
            - players_list: 경기 참여 선수 메타데이터 목록
            - has_360: 하이라이트 윈도우 내에 실제 360 데이터가 포함되었는지 여부
    """
    start_idx = int(highlight.get("start_event", 0))
    end_idx = int(highlight.get("end_event", len(events) - 1))

    # 범위 클램프
    start_idx = max(0, min(start_idx, len(events) - 1))
    end_idx = max(start_idx, min(end_idx, len(events) - 1))

    # 360 매핑 인덱스 구성 (event_uuid 기준)
    three_sixty_map: dict[str, dict[str, Any]] = {}
    if three_sixty_frames:
        for f360 in three_sixty_frames:
            ev_uuid = f360.get("event_uuid")
            if ev_uuid:
                three_sixty_map[ev_uuid] = f360

    lineup_maps = build_lineup_maps(lineups)
    all_team_ids = list(lineup_maps.keys())

    # 선수 전체 목록 생성
    all_players: list[dict[str, Any]] = []
    for team_id, team_info in lineup_maps.items():
        for p_id, p_info in team_info.get("players", {}).items():
            all_players.append(
                {
                    "player_id": p_id,
                    "team_id": team_id,
                    "team_name": team_info.get("team_name", ""),
                    "player_name": p_info.get("player_name", ""),
                    "player_nickname": p_info.get("player_nickname"),
                    "jersey_number": p_info.get("jersey_number"),
                    "is_starter": p_info.get("is_starter", False),
                    "primary_position": p_info.get("primary_position"),
                }
            )

    window_events = events[start_idx : end_idx + 1]
    frames: list[dict[str, Any]] = []
    window_has_360 = False

    prev_timestamp: float | None = None
    prev_actor_loc: tuple[float, float] | None = None

    for frame_idx, ev in enumerate(window_events):
        ev_id = ev.get("id", "")
        ev_idx = start_idx + frame_idx
        t_sec = event_time(ev)
        dt = (t_sec - prev_timestamp) if (prev_timestamp is not None) else 0.0
        dt = max(0.0, dt)

        f360 = three_sixty_map.get(ev_id)
        ball_loc = ev.get("location")
        actor_player_id = ev.get("player", {}).get("id")
        actor_team_id = ev.get("team", {}).get("id") or (all_team_ids[0] if all_team_ids else 0)

        opponent_team_id = None
        for t_id in all_team_ids:
            if t_id != actor_team_id:
                opponent_team_id = t_id
                break
        if opponent_team_id is None and all_team_ids:
            opponent_team_id = all_team_ids[-1]

        raw_players: list[dict[str, Any]] = []
        visible_area: list[float] = []

        if f360 is not None:
            window_has_360 = True
            visible_area = f360.get("visible_area", [])
            freeze_players = f360.get("freeze_frame", [])

            teammates_present = 0
            opponents_present = 0

            for fp in freeze_players:
                loc = fp.get("location", [60.0, 40.0])
                is_actor = bool(fp.get("actor", False))
                is_teammate = bool(fp.get("teammate", False))
                is_keeper = bool(fp.get("keeper", False))

                if is_teammate:
                    teammates_present += 1
                else:
                    opponents_present += 1

                # 속도 추정
                vx, vy = 0.0, 0.0
                if is_actor and prev_actor_loc is not None and dt > 0.01:
                    vx, vy = calculate_velocity(prev_actor_loc, loc, dt)

                # 포메이션 앵커 좌표 조회
                anchor_x, anchor_y = None, None
                if is_actor and actor_player_id and formation_anchors and actor_team_id:
                    team_anchors = formation_anchors.get(actor_team_id, {})
                    if actor_player_id in team_anchors:
                        anchor_x, anchor_y = team_anchors[actor_player_id]

                player_entry = {
                    "player_id": actor_player_id if is_actor else None,
                    "location": loc,
                    "is_actor": is_actor,
                    "is_teammate": is_teammate,
                    "is_keeper": is_keeper,
                    "vx": vx,
                    "vy": vy,
                    "anchor_x": anchor_x,
                    "anchor_y": anchor_y,
                    "is_inferred": False,
                }
                raw_players.append(player_entry)

                if is_actor:
                    prev_actor_loc = (float(loc[0]), float(loc[1]))

            # 22명 가상 추론: 360 프레임 밖 미인식 선수를 포메이션 앵커 위치에 가상 배치
            # 1) 아군 팀 미인식 선수 보충 (선발 11명 목표)
            home_team_info = lineup_maps.get(actor_team_id, {})
            home_starters = home_team_info.get("starting_xi", [])
            home_players_meta = home_team_info.get("players", {})
            needed_teammates = max(0, 11 - teammates_present)

            teammates_to_add = [p_id for p_id in home_starters if p_id != actor_player_id][
                :needed_teammates
            ]

            for p_id in teammates_to_add:
                p_meta = home_players_meta.get(p_id, {})
                pos_id = p_meta.get("primary_position_id")
                anchor = (
                    formation_anchors.get(actor_team_id, {}).get(p_id)
                    if formation_anchors
                    else None
                )
                if not anchor:
                    anchor = get_position_anchor(pos_id)

                raw_players.append(
                    {
                        "player_id": p_id,
                        "location": [anchor[0], anchor[1]],
                        "is_actor": False,
                        "is_teammate": True,
                        "is_keeper": (pos_id == 1),
                        "vx": 0.0,
                        "vy": 0.0,
                        "anchor_x": anchor[0],
                        "anchor_y": anchor[1],
                        "is_inferred": True,
                    }
                )

            # 2) 상대 팀 미인식 선수 보충 (선발 11명 목표)
            if opponent_team_id:
                opp_team_info = lineup_maps.get(opponent_team_id, {})
                opp_starters = opp_team_info.get("starting_xi", [])
                opp_players_meta = opp_team_info.get("players", {})
                needed_opponents = max(0, 11 - opponents_present)

                opponents_to_add = opp_starters[:needed_opponents]

                for p_id in opponents_to_add:
                    p_meta = opp_players_meta.get(p_id, {})
                    pos_id = p_meta.get("primary_position_id")
                    anchor = (
                        formation_anchors.get(opponent_team_id, {}).get(p_id)
                        if formation_anchors
                        else None
                    )
                    if not anchor:
                        anchor = get_position_anchor(pos_id)

                    # 상대팀은 반대 진영(120 - x, 80 - y)으로 대칭 배치
                    opp_x = round(120.0 - anchor[0], 2)
                    opp_y = round(80.0 - anchor[1], 2)

                    raw_players.append(
                        {
                            "player_id": p_id,
                            "location": [opp_x, opp_y],
                            "is_actor": False,
                            "is_teammate": False,
                            "is_keeper": (pos_id == 1),
                            "vx": 0.0,
                            "vy": 0.0,
                            "anchor_x": opp_x,
                            "anchor_y": opp_y,
                            "is_inferred": True,
                        }
                    )
        else:
            # 360 데이터가 없는 이벤트인 경우 액터 위치 + 21명 포메이션 앵커 가상 프레임 생성
            effective_loc = ball_loc if ball_loc is not None else [60.0, 40.0]
            vx, vy = 0.0, 0.0
            if prev_actor_loc is not None and dt > 0.01:
                vx, vy = calculate_velocity(prev_actor_loc, effective_loc, dt)

            raw_players.append(
                {
                    "player_id": actor_player_id,
                    "location": effective_loc,
                    "is_actor": True,
                    "is_teammate": True,
                    "is_keeper": False,
                    "vx": vx,
                    "vy": vy,
                    "anchor_x": None,
                    "anchor_y": None,
                    "is_inferred": False,
                }
            )
            prev_actor_loc = (float(effective_loc[0]), float(effective_loc[1]))

            # 아군 선발 나머지 10명 가상 배치
            home_team_info = lineup_maps.get(actor_team_id, {})
            for p_id in home_team_info.get("starting_xi", []):
                if p_id == actor_player_id:
                    continue
                p_meta = home_team_info.get("players", {}).get(p_id, {})
                pos_id = p_meta.get("primary_position_id")
                anchor = (
                    formation_anchors.get(actor_team_id, {}).get(p_id)
                    if formation_anchors
                    else None
                )
                if not anchor:
                    anchor = get_position_anchor(pos_id)
                raw_players.append(
                    {
                        "player_id": p_id,
                        "location": [anchor[0], anchor[1]],
                        "is_actor": False,
                        "is_teammate": True,
                        "is_keeper": (pos_id == 1),
                        "vx": 0.0,
                        "vy": 0.0,
                        "anchor_x": anchor[0],
                        "anchor_y": anchor[1],
                        "is_inferred": True,
                    }
                )

            # 상대팀 선발 11명 가상 배치
            if opponent_team_id:
                opp_team_info = lineup_maps.get(opponent_team_id, {})
                for p_id in opp_team_info.get("starting_xi", []):
                    p_meta = opp_team_info.get("players", {}).get(p_id, {})
                    pos_id = p_meta.get("primary_position_id")
                    anchor = (
                        formation_anchors.get(opponent_team_id, {}).get(p_id)
                        if formation_anchors
                        else None
                    )
                    if not anchor:
                        anchor = get_position_anchor(pos_id)
                    opp_x = round(120.0 - anchor[0], 2)
                    opp_y = round(80.0 - anchor[1], 2)
                    raw_players.append(
                        {
                            "player_id": p_id,
                            "location": [opp_x, opp_y],
                            "is_actor": False,
                            "is_teammate": False,
                            "is_keeper": (pos_id == 1),
                            "vx": 0.0,
                            "vy": 0.0,
                            "anchor_x": opp_x,
                            "anchor_y": opp_y,
                            "is_inferred": True,
                        }
                    )

        # 22명(팀원 11명 vs 상대팀 11명) 정원 보정
        t_players = [p for p in raw_players if p.get("is_teammate")]
        o_players = [p for p in raw_players if not p.get("is_teammate")]
        final_players = t_players[:11] + o_players[:11]

        # 단기 외삽 (+2초) 적용
        extrapolated_players = extrapolate_frame_players(final_players, dt=2.0)

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
            "description": _build_frame_description(ev),
            "team_id": actor_team_id,
            "team_name": ev.get("team", {}).get("name", ""),
        }
        frames.append(frame_data)
        prev_timestamp = t_sec

    return frames, all_players, window_has_360
