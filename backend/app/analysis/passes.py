"""패스 네트워크 및 전진성(Passes & Progressiveness) 분석 모듈.

성공한 패스 체인, 선수별 평균 패스 위치 노드, 상위 패스 연결 엣지(15개),
전진 패스 비율 및 평균 전진 거리를 산출합니다.
"""

from collections import defaultdict
from typing import Any

from app.analysis.common import build_lineup_maps, is_completed_pass


def compute_pass_network(
    events: list[dict[str, Any]],
    lineups: list[dict[str, Any]],
    team_id: int,
    top_edges_limit: int = 15,
) -> dict[str, Any]:
    """패스 네트워크(노드, 상위 엣지) 및 전진성 지표를 산출합니다."""
    lineup_maps = build_lineup_maps(lineups)
    team_meta = lineup_maps.get(team_id, {"players": {}, "starting_xi": []})
    players_meta = team_meta.get("players", {})

    pass_counts: dict[tuple[int, int], int] = defaultdict(int)
    pass_prog_counts: dict[tuple[int, int], int] = defaultdict(int)
    player_pass_locs: dict[int, list[tuple[float, float]]] = defaultdict(list)
    player_pass_attempts: dict[int, int] = defaultdict(int)
    player_pass_completions: dict[int, int] = defaultdict(int)

    total_passes = 0
    completed_passes = 0
    progressive_passes = 0
    total_delta_x = 0.0

    for ev in events:
        if ev.get("type", {}).get("name") != "Pass":
            continue
        if ev.get("team", {}).get("id") != team_id:
            continue

        total_passes += 1
        pass_data = ev.get("pass", {})
        player_info = ev.get("player", {})
        passer_id = player_info.get("id")

        loc = ev.get("location")
        end_loc = pass_data.get("end_location")

        if passer_id is not None:
            player_pass_attempts[passer_id] += 1

        is_prog = False
        if loc and end_loc and len(loc) >= 2 and len(end_loc) >= 2:
            dx = float(end_loc[0]) - float(loc[0])
            total_delta_x += dx
            if dx >= 10.0:
                progressive_passes += 1
                is_prog = True

        if is_completed_pass(ev):
            completed_passes += 1
            recipient_info = pass_data.get("recipient", {})
            recipient_id = recipient_info.get("id")

            if passer_id is not None:
                player_pass_completions[passer_id] += 1
                if loc and len(loc) >= 2:
                    player_pass_locs[passer_id].append((float(loc[0]), float(loc[1])))

                if recipient_id is not None and passer_id != recipient_id:
                    pass_counts[(passer_id, recipient_id)] += 1
                    if is_prog:
                        pass_prog_counts[(passer_id, recipient_id)] += 1

    starting_xi = set(team_meta.get("starting_xi", []))

    # 노드 구성 (선발 11명 중심)
    starters_nodes: list[dict[str, Any]] = []
    other_nodes: list[dict[str, Any]] = []

    for p_id, p_info in players_meta.items():
        locs = player_pass_locs.get(p_id, [])
        attempts = player_pass_attempts.get(p_id, 0)
        completions = player_pass_completions.get(p_id, 0)

        if locs:
            avg_x = round(sum(x for x, _ in locs) / len(locs), 2)
            avg_y = round(sum(y for _, y in locs) / len(locs), 2)
        else:
            avg_x, avg_y = 60.0, 40.0

        disp_name = p_info.get("player_nickname") or p_info.get("player_name", "Unknown")
        node_obj = {
            "player_id": p_id,
            "player_name": disp_name,
            "player_nickname": p_info.get("player_nickname"),
            "full_name": p_info.get("player_name"),
            "jersey_number": p_info.get("jersey_number"),
            "position": p_info.get("primary_position"),
            "is_starter": p_id in starting_xi,
            "x": avg_x,
            "y": avg_y,
            "pass_count": completions,
            "pass_attempts": attempts,
            "pass_completions": completions,
            "pass_accuracy": round(completions / attempts, 3) if attempts > 0 else 0.0,
        }

        if p_id in starting_xi:
            starters_nodes.append(node_obj)
        elif attempts > 0:
            other_nodes.append(node_obj)

    # 선발 11명 정원 준수 (11명 초과 방지)
    if len(starters_nodes) >= 11:
        nodes = starters_nodes[:11]
    else:
        other_nodes.sort(key=lambda n: n["pass_attempts"], reverse=True)
        nodes = (starters_nodes + other_nodes)[:11]

    valid_node_ids = {n["player_id"] for n in nodes}

    # 엣지 구성 및 상위 N개 추출 (유효 11명 노드 간 연결)
    sorted_pairs = sorted(
        [
            ((src, dst), cnt)
            for (src, dst), cnt in pass_counts.items()
            if src in valid_node_ids and dst in valid_node_ids
        ],
        key=lambda item: item[1],
        reverse=True,
    )

    edges: list[dict[str, Any]] = []
    for (src, dst), count in sorted_pairs[:top_edges_limit]:
        src_name = players_meta.get(src, {}).get("player_name", str(src))
        dst_name = players_meta.get(dst, {}).get("player_name", str(dst))
        edges.append(
            {
                "passer_id": src,
                "recipient_id": dst,
                "count": count,
                "progressive_count": pass_prog_counts.get((src, dst), 0),
                "source_id": src,
                "source_name": src_name,
                "target_id": dst,
                "target_name": dst_name,
                "pass_count": count,
            }
        )

    pass_accuracy = round(completed_passes / total_passes, 3) if total_passes > 0 else 0.0
    prog_pass_ratio = round(progressive_passes / total_passes, 3) if total_passes > 0 else 0.0
    avg_delta_x = round(total_delta_x / total_passes, 2) if total_passes > 0 else 0.0

    return {
        "team_id": team_id,
        "total_passes": total_passes,
        "completed_passes": completed_passes,
        "pass_accuracy": pass_accuracy,
        "progressive_passes": progressive_passes,
        "progressive_pass_ratio": prog_pass_ratio,
        "avg_pass_progression_m": avg_delta_x,
        "nodes": nodes,
        "edges": edges,
    }
