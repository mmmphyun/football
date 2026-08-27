"""StatsBomb 데이터 수집 및 전술 분석 CLI 도구."""

import argparse
import logging
import sys
from pathlib import Path

from app.downloader import StatsBombDownloader
from app.processing import process_competition, process_match
from app.storage import (
    get_competitions,
    init_db,
    save_competitions,
    save_matches,
)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("cli")


def handle_fetch(args: argparse.Namespace) -> None:
    """StatsBomb 360 대회 및 경기 raw 데이터를 다운로드하여 캐시하고 DB 메타데이터를 갱신합니다."""
    init_db(args.db_path)
    dl = StatsBombDownloader(raw_dir=args.raw_dir)

    logger.info("360 데이터가 포함된 대회 검색 중...")
    comps = dl.detect_360_competitions(force=args.force)
    if not comps:
        logger.warning("360 데이터가 포함된 대회를 찾을 수 없습니다.")
        return

    # 대회 필터링
    if args.comp_id is not None:
        comps = [c for c in comps if c.get("competition_id") == args.comp_id]
    if args.season_id is not None:
        comps = [c for c in comps if c.get("season_id") == args.season_id]

    logger.info("대상 대회 %d개 발견", len(comps))

    # DB 저장용 대회 목록 변환
    comp_records = []
    for c in comps:
        comp_records.append(
            {
                "competition_id": c["competition_id"],
                "season_id": c["season_id"],
                "name": c.get("competition_name", ""),
                "season_name": c.get("season_name", ""),
                "country": c.get("country_name", ""),
                "match_count": 0,
                "has_360": 1 if c.get("match_available_360") else 0,
                "processed_at": None,
            }
        )
    save_competitions(comp_records, db_path=args.db_path)

    # 경기 목록 수집
    for comp in comps:
        c_id = comp["competition_id"]
        s_id = comp["season_id"]
        c_name = comp.get("competition_name", "")
        s_name = comp.get("season_name", "")
        logger.info("대회 경기 목록 다운로드 중: %s (%s)", c_name, s_name)

        matches = dl.fetch_matches(c_id, s_id, force=args.force)
        match_records = []
        for m in matches:
            match_records.append(
                {
                    "match_id": m["match_id"],
                    "competition_id": c_id,
                    "season_id": s_id,
                    "home_team": m.get("home_team", {}).get("home_team_name", ""),
                    "away_team": m.get("away_team", {}).get("away_team_name", ""),
                    "home_team_id": m.get("home_team", {}).get("home_team_id", 0),
                    "away_team_id": m.get("away_team", {}).get("away_team_id", 0),
                    "home_score": m.get("home_score"),
                    "away_score": m.get("away_score"),
                    "match_date": m.get("match_date", ""),
                    "has_360": 1 if m.get("match_status_360") == "available" else 0,
                    "status": "raw",
                }
            )
        save_matches(match_records, db_path=args.db_path)
        logger.info("대회 %s 경기 %d건 DB 등록 완료", c_name, len(match_records))

        # 경기별 상세 데이터 (events, lineups, 360) 프리패치
        if args.download_bundle:
            for idx, m in enumerate(matches, 1):
                m_id = m["match_id"]
                logger.info("[%d/%d] 경기 %d 데이터 다운로드 캐싱 중...", idx, len(matches), m_id)
                dl.fetch_full_match_bundle(m_id, force=args.force)

    logger.info("fetch 작업이 완료되었습니다.")


def handle_process(args: argparse.Namespace) -> None:
    """다운로드된 경기 데이터를 가공하여 전술 분석 결과 및 하이라이트를 DB에 적재합니다."""
    init_db(args.db_path)
    dl = StatsBombDownloader(raw_dir=args.raw_dir)

    if args.match_id is not None:
        logger.info("단일 경기 %d 가공 시작...", args.match_id)
        ok = process_match(args.match_id, downloader=dl, db_path=args.db_path, force=args.force)
        if ok:
            logger.info("단일 경기 %d 가공 성공", args.match_id)
        else:
            logger.error("단일 경기 %d 가공 실패", args.match_id)
            sys.exit(1)
        return

    if args.comp_id is not None and args.season_id is not None:
        logger.info("대회 (%d, %d) 경기 가공 시작...", args.comp_id, args.season_id)
        stats = process_competition(
            args.comp_id,
            args.season_id,
            downloader=dl,
            db_path=args.db_path,
            force=args.force,
        )
        logger.info(
            "가공 완료: 총 %d건 (성공: %d, 실패: %d, 건너뜀: %d)",
            stats["total"],
            stats["success"],
            stats["failed"],
            stats["skipped"],
        )
        return

    if args.all:
        logger.info("전체 등록된 경기 일괄 가공 시작...")
        comps = get_competitions(db_path=args.db_path)
        total_success = 0
        total_failed = 0
        if comps:
            for comp in comps:
                c_id = comp["competition_id"]
                s_id = comp["season_id"]
                stats = process_competition(
                    c_id, s_id, downloader=dl, db_path=args.db_path, force=args.force
                )
                total_success += stats["success"]
                total_failed += stats["failed"]
        else:
            from app.storage import get_db

            with get_db(args.db_path) as conn:
                rows = conn.execute("SELECT match_id FROM matches").fetchall()
                match_ids = [r["match_id"] for r in rows]
            logger.info("matches 테이블에서 %d개 경기 발견", len(match_ids))
            for m_id in match_ids:
                ok = process_match(m_id, downloader=dl, db_path=args.db_path, force=args.force)
                if ok:
                    total_success += 1
                else:
                    total_failed += 1
        logger.info("전체 가공 완료: 성공 %d건, 실패 %d건", total_success, total_failed)
        return

    logger.warning("가공할 대상을 지정하십시오. (--match-id, --comp-id & --season-id, 또는 --all)")


def build_parser() -> argparse.ArgumentParser:
    """CLI 인자 파서를 생성합니다."""
    parser = argparse.ArgumentParser(
        prog="python -m app.cli",
        description="StatsBomb 전술 분석 파이프라인 CLI",
    )
    parser.add_argument("--db-path", type=Path, default=None, help="SQLite DB 파일 경로")
    parser.add_argument(
        "--raw-dir", type=Path, default=None, help="Raw 데이터 디스크 캐시 디렉터리"
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # fetch 서브커맨드
    fetch_parser = subparsers.add_parser("fetch", help="StatsBomb 원본 데이터 다운로드 및 캐싱")
    fetch_parser.add_argument("--comp-id", type=int, default=None, help="특정 대회 ID")
    fetch_parser.add_argument("--season-id", type=int, default=None, help="특정 시즌 ID")
    fetch_parser.add_argument("--force", action="store_true", help="기존 캐시 무시 강제 재다운로드")
    fetch_parser.add_argument(
        "--download-bundle",
        action="store_true",
        default=True,
        help="경기별 이벤트/360 데이터 일괄 프리패치",
    )

    # process 서브커맨드
    process_parser = subparsers.add_parser("process", help="경기 전술 분석 및 DB 적재")
    process_parser.add_argument("--match-id", type=int, default=None, help="가공할 단일 경기 ID")
    process_parser.add_argument("--comp-id", type=int, default=None, help="가공할 대회 ID")
    process_parser.add_argument("--season-id", type=int, default=None, help="가공할 시즌 ID")
    process_parser.add_argument(
        "--all", action="store_true", help="DB에 등록된 모든 경기 일괄 가공"
    )
    process_parser.add_argument("--force", action="store_true", help="이미 가공된 경기 재가공")

    return parser


def main() -> None:
    """CLI 진입점 함수."""
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "fetch":
        handle_fetch(args)
    elif args.command == "process":
        handle_process(args)


if __name__ == "__main__":
    main()
