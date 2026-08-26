"""경기 전술 분석, 하이라이트 추출 및 SQLite DB 적재 통합 파이프라인 모듈."""

import logging
from pathlib import Path
from typing import Any

from app.analysis import analyze_match
from app.downloader import StatsBombDownloader
from app.frames import build_highlight_frames
from app.highlights import extract_highlights
from app.storage import (
    get_matches,
    init_db,
    save_highlight_frames,
    save_highlights,
    save_match_summary,
    update_match_status,
)

logger = logging.getLogger(__name__)


def _extract_formation_anchors(
    summary_data: dict[str, Any],
) -> dict[int, dict[int, tuple[float, float]]]:
    """분석 요약 결과에서 팀별 선수 포메이션 평균 위치 앵커 맵을 추출합니다."""
    anchors: dict[int, dict[int, tuple[float, float]]] = {}
    teams = summary_data.get("teams", {})
    for team_id_key, t_data in teams.items():
        team_id = int(team_id_key)
        formation = t_data.get("formation", {})
        players = formation.get("players") or formation.get("players_overall") or []
        team_anchor_map: dict[int, tuple[float, float]] = {}
        for p in players:
            p_id = p.get("player_id")
            # 실측 x, y 또는 표준 anchor_x, anchor_y
            x = p.get("x") if p.get("x") is not None else p.get("anchor_x")
            y = p.get("y") if p.get("y") is not None else p.get("anchor_y")
            if p_id is not None and x is not None and y is not None:
                team_anchor_map[p_id] = (float(x), float(y))
        anchors[team_id] = team_anchor_map
    return anchors


def process_match(
    match_id: int,
    downloader: StatsBombDownloader | None = None,
    db_path: Path | str | None = None,
    force: bool = False,
) -> bool:
    """단일 경기의 raw 데이터를 수집/파싱하여 8종 전술 분석, 하이라이트 및 프레임을 DB에 적재합니다."""
    init_db(db_path)
    dl = downloader if downloader is not None else StatsBombDownloader()

    try:
        bundle = dl.fetch_full_match_bundle(match_id, force=force)
        events = bundle.get("events", [])
        lineups = bundle.get("lineups", [])
        three_sixty = bundle.get("three_sixty")

        if not events:
            logger.warning("경기 %d의 이벤트 데이터가 비어있습니다.", match_id)
            update_match_status(match_id, "error", db_path)
            return False

        # 1. 8종 전술 분석 수행 및 요약 JSON 저장
        summary_data = analyze_match(events, lineups, three_sixty)
        save_match_summary(match_id, summary_data, db_path)

        # 2. 하이라이트 추출 및 DB 적재
        highlights = extract_highlights(events)
        saved_hl_ids = save_highlights(match_id, highlights, db_path)

        # 3. 하이라이트별 360 프레임 시퀀스 생성 및 저장
        formation_anchors = _extract_formation_anchors(summary_data)
        for hl_id, hl in zip(saved_hl_ids, highlights, strict=False):
            frames, players, has_360 = build_highlight_frames(
                events=events,
                three_sixty_frames=three_sixty,
                lineups=lineups,
                highlight=hl,
                formation_anchors=formation_anchors,
            )
            save_highlight_frames(
                highlight_id=hl_id,
                match_id=match_id,
                frames_data=frames,
                players_data=players,
                has_360=has_360,
                db_path=db_path,
            )

        # 4. 상태 갱신
        update_match_status(match_id, "processed", db_path)
        logger.info("경기 %d 가공 완료 (하이라이트 %d건)", match_id, len(saved_hl_ids))
        return True
    except Exception as e:
        logger.exception("경기 %d 가공 중 오류 발생: %s", match_id, e)
        update_match_status(match_id, "error", db_path)
        return False


def process_competition(
    competition_id: int,
    season_id: int,
    downloader: StatsBombDownloader | None = None,
    db_path: Path | str | None = None,
    force: bool = False,
) -> dict[str, int]:
    """특정 대회/시즌에 등록된 모든 경기를 일괄 가공합니다."""
    init_db(db_path)
    matches = get_matches(competition_id, season_id, db_path)
    stats = {"total": len(matches), "success": 0, "failed": 0, "skipped": 0}

    for m in matches:
        m_id = m["match_id"]
        status = m.get("status", "raw")
        if status == "processed" and not force:
            stats["skipped"] += 1
            continue

        ok = process_match(m_id, downloader=downloader, db_path=db_path, force=force)
        if ok:
            stats["success"] += 1
        else:
            stats["failed"] += 1

    return stats
