"""스토리지 CRUD 및 데이터 처리 파이프라인 통합 테스트 스위트."""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

from app.downloader import StatsBombDownloader
from app.processing import process_competition, process_match
from app.storage import (
    get_competitions,
    get_highlight_frames,
    get_highlights,
    get_match,
    get_match_summary,
    get_matches,
    save_competitions,
    save_highlight_frames,
    save_highlights,
    save_match_summary,
    save_matches,
    update_match_status,
)


class TestStorageCRUD:
    """SQLite 스토리지 계층 CRUD 함수 테스트."""

    def test_save_and_get_competitions(
        self,
        temp_db: Path,
        sample_competitions: list[dict[str, Any]],
    ) -> None:
        """대회 목록 저장 및 조회 검증."""
        saved_count = save_competitions(sample_competitions, db_path=temp_db)
        assert saved_count == len(sample_competitions)

        comps = get_competitions(db_path=temp_db)
        assert len(comps) == len(sample_competitions)
        euro_comp = next(c for c in comps if c["competition_id"] == 55)
        assert euro_comp["name"] == "UEFA Euro"
        assert euro_comp["has_360"] == 1

    def test_save_and_get_matches(
        self,
        temp_db: Path,
        sample_competitions: list[dict[str, Any]],
        sample_matches: list[dict[str, Any]],
    ) -> None:
        """경기 메타데이터 저장, 목록 조회, 단일 조회 및 상태 업데이트 검증."""
        save_competitions(sample_competitions, db_path=temp_db)
        saved_count = save_matches(sample_matches, db_path=temp_db)
        assert saved_count == 1

        matches = get_matches(competition_id=55, season_id=282, db_path=temp_db)
        assert len(matches) == 1
        assert matches[0]["match_id"] == 3788758
        assert matches[0]["home_score"] == 2
        assert matches[0]["status"] == "raw"

        # 단일 경기 조회
        match = get_match(3788758, db_path=temp_db)
        assert match is not None
        assert match["match_id"] == 3788758

        # 미존재 경기 조회
        assert get_match(999999, db_path=temp_db) is None

        # 상태 갱신
        update_match_status(3788758, "processed", db_path=temp_db)
        match_updated = get_match(3788758, db_path=temp_db)
        assert match_updated is not None
        assert match_updated["status"] == "processed"

    def test_save_and_get_summary(
        self,
        temp_db: Path,
        sample_competitions: list[dict[str, Any]],
        sample_matches: list[dict[str, Any]],
    ) -> None:
        """경기 8종 전술 요약 저장 및 조회 검증."""
        save_competitions(sample_competitions, db_path=temp_db)
        save_matches(sample_matches, db_path=temp_db)

        summary_payload = {"match_id": 3788758, "teams": {911: {"formation": "433"}}}
        save_match_summary(3788758, summary_payload, db_path=temp_db)

        loaded_summary = get_match_summary(3788758, db_path=temp_db)
        assert loaded_summary is not None
        assert loaded_summary["match_id"] == 3788758
        assert loaded_summary["teams"]["911"]["formation"] == "433"

    def test_save_and_get_highlights_and_frames(
        self,
        temp_db: Path,
        sample_competitions: list[dict[str, Any]],
        sample_matches: list[dict[str, Any]],
    ) -> None:
        """하이라이트 및 프레임 시퀀스 저장/조회 검증."""
        save_competitions(sample_competitions, db_path=temp_db)
        save_matches(sample_matches, db_path=temp_db)

        sample_hl = [
            {
                "type": "Goal",
                "period": 1,
                "minute": 3,
                "second": 52,
                "team_id": 911,
                "team_name": "Ukraine",
                "xg": 0.38,
                "start_event": 120,
                "end_event": 125,
                "event_index": 125,
                "window_start_sec": 202.0,
                "window_end_sec": 236.0,
            }
        ]
        hl_ids = save_highlights(3788758, sample_hl, db_path=temp_db)
        assert len(hl_ids) == 1
        hl_id = hl_ids[0]

        highlights = get_highlights(3788758, db_path=temp_db)
        assert len(highlights) == 1
        assert highlights[0]["id"] == hl_id
        assert highlights[0]["team_name"] == "Ukraine"

        # 프레임 저장 및 조회
        frames_payload = [{"frame_index": 0, "timestamp_sec": 202.0, "players": []}]
        players_payload = [{"player_id": 10655, "player_name": "Andriy Yarmolenko"}]
        save_highlight_frames(
            highlight_id=hl_id,
            match_id=3788758,
            frames_data=frames_payload,
            players_data=players_payload,
            has_360=True,
            db_path=temp_db,
        )

        frames_res = get_highlight_frames(hl_id, db_path=temp_db)
        assert frames_res is not None
        assert frames_res["has_360"] is True
        assert len(frames_res["frames"]) == 1
        assert len(frames_res["players"]) == 1


class TestProcessingPipeline:
    """데이터 수집 및 가공 파이프라인 통합 테스트."""

    def test_process_match_success(
        self,
        temp_db: Path,
        sample_competitions: list[dict[str, Any]],
        sample_matches: list[dict[str, Any]],
        sample_events: list[dict[str, Any]],
        sample_lineups: list[dict[str, Any]],
        sample_three_sixty: list[dict[str, Any]],
    ) -> None:
        """단일 경기 분석 및 DB 적재 파이프라인 무결성 검증."""
        save_competitions(sample_competitions, db_path=temp_db)
        save_matches(sample_matches, db_path=temp_db)

        # Mock Downloader 구성
        mock_downloader = MagicMock(spec=StatsBombDownloader)
        mock_downloader.fetch_full_match_bundle.return_value = {
            "events": sample_events,
            "lineups": sample_lineups,
            "three_sixty": sample_three_sixty,
        }

        success = process_match(
            match_id=3788758,
            downloader=mock_downloader,
            db_path=temp_db,
            force=True,
        )
        assert success is True

        # DB 적재 결과 확인
        summary = get_match_summary(3788758, db_path=temp_db)
        assert summary is not None
        assert "teams" in summary

        highlights = get_highlights(3788758, db_path=temp_db)
        assert len(highlights) >= 2

        # 첫 번째 하이라이트의 프레임 조회
        frames = get_highlight_frames(highlights[0]["id"], db_path=temp_db)
        assert frames is not None
        assert len(frames["frames"]) > 0

    def test_process_competition(
        self,
        temp_db: Path,
        sample_competitions: list[dict[str, Any]],
        sample_matches: list[dict[str, Any]],
        sample_events: list[dict[str, Any]],
        sample_lineups: list[dict[str, Any]],
        sample_three_sixty: list[dict[str, Any]],
    ) -> None:
        """대회 단위 일괄 가공 파이프라인 검증."""
        save_competitions(sample_competitions, db_path=temp_db)
        save_matches(sample_matches, db_path=temp_db)

        mock_downloader = MagicMock(spec=StatsBombDownloader)
        mock_downloader.fetch_full_match_bundle.return_value = {
            "events": sample_events,
            "lineups": sample_lineups,
            "three_sixty": sample_three_sixty,
        }

        stats = process_competition(
            competition_id=55,
            season_id=282,
            downloader=mock_downloader,
            db_path=temp_db,
            force=True,
        )
        assert stats["total"] == 1
        assert stats["success"] == 1
        assert stats["failed"] == 0
