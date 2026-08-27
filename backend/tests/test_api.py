"""FastAPI REST 엔드포인트 통합 및 스모크 테스트 스위트."""

from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from app.storage import (
    save_competitions,
    save_highlight_frames,
    save_highlights,
    save_match_summary,
    save_matches,
)


class TestFastAPIEndpoints:
    """FastAPI REST 엔드포인트 검증."""

    def test_health_check(self, client: TestClient) -> None:
        """GET /api/health 헬스체크 엔드포인트 검증."""
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_list_competitions(
        self,
        client: TestClient,
        temp_db: Path,
        sample_competitions: list[dict[str, Any]],
    ) -> None:
        """GET /api/competitions 대회 목록 조회 검증."""
        save_competitions(sample_competitions, db_path=temp_db)

        response = client.get("/api/competitions")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == len(sample_competitions)
        euro_comp = next(c for c in data if c["competition_id"] == 55)
        assert euro_comp["name"] == "UEFA Euro"

    def test_list_matches(
        self,
        client: TestClient,
        temp_db: Path,
        sample_competitions: list[dict[str, Any]],
        sample_matches: list[dict[str, Any]],
    ) -> None:
        """GET /api/competitions/{comp_id}/matches 경기 목록 조회 검증."""
        save_competitions(sample_competitions, db_path=temp_db)
        save_matches(sample_matches, db_path=temp_db)

        # 정상 조회
        response = client.get("/api/competitions/55/matches?season_id=282")
        assert response.status_code == 200
        matches = response.json()
        assert len(matches) == 1
        assert matches[0]["match_id"] == 3788758

        # 쿼리 파라미터 누락 시 422 Unprocessable Entity
        err_res = client.get("/api/competitions/55/matches")
        assert err_res.status_code == 422

    def test_get_match_detail(
        self,
        client: TestClient,
        temp_db: Path,
        sample_competitions: list[dict[str, Any]],
        sample_matches: list[dict[str, Any]],
    ) -> None:
        """GET /api/matches/{match_id} 단일 경기 메타데이터 조회 검증."""
        save_competitions(sample_competitions, db_path=temp_db)
        save_matches(sample_matches, db_path=temp_db)

        # 정상 조회 (200)
        response = client.get("/api/matches/3788758")
        assert response.status_code == 200
        match_data = response.json()
        assert match_data["match_id"] == 3788758
        assert match_data["home_team"] == "Ukraine"

        # 미존재 경기 (404)
        not_found_res = client.get("/api/matches/999999")
        assert not_found_res.status_code == 404
        assert not_found_res.json()["detail"] == "Match not found"

    def test_get_match_summary(
        self,
        client: TestClient,
        temp_db: Path,
        sample_competitions: list[dict[str, Any]],
        sample_matches: list[dict[str, Any]],
    ) -> None:
        """GET /api/matches/{match_id}/summary 전술 분석 요약 조회 검증."""
        save_competitions(sample_competitions, db_path=temp_db)
        save_matches(sample_matches, db_path=temp_db)

        summary_payload = {
            "match_id": 3788758,
            "duration_min": 90.0,
            "teams": {
                "911": {
                    "team_name": "Ukraine",
                    "formation": {
                        "defensive": {"formation": "4-4-2", "line_height": 35.0},
                        "buildup": {"formation": "3-2-4-1", "line_height": 45.0},
                        "attacking": {"formation": "2-3-5", "line_height": 72.0},
                    },
                    "playbook": [
                        {
                            "pattern_id": "side_overload_cutback",
                            "name": "Side Overload & Cutback",
                            "occurrences": 3,
                        }
                    ],
                    "timeline": [{"minute_start": 0, "minute_end": 15, "possession_pct": 55.0}],
                    "pressure": {"pressure_traps": [{"zone": "Right Touchline Trap", "count": 2}]},
                },
                "2358": {
                    "team_name": "North Macedonia",
                    "formation": {
                        "defensive": {"formation": "5-3-2", "line_height": 28.0},
                        "buildup": {"formation": "3-5-2", "line_height": 42.0},
                        "attacking": {"formation": "3-3-4", "line_height": 65.0},
                    },
                    "playbook": [],
                    "timeline": [],
                    "pressure": {"pressure_traps": []},
                },
            },
        }
        save_match_summary(3788758, summary_payload, db_path=temp_db)

        # 정상 조회 (200)
        response = client.get("/api/matches/3788758/summary")
        assert response.status_code == 200
        summary = response.json()
        assert summary["match_id"] == 3788758
        assert "teams" in summary
        assert "911" in summary["teams"]
        ukr = summary["teams"]["911"]
        assert "defensive" in ukr["formation"]
        assert "buildup" in ukr["formation"]
        assert "attacking" in ukr["formation"]
        assert "playbook" in ukr
        assert "timeline" in ukr
        assert "pressure" in ukr

        # 미존재 경기 요약 (404)
        not_found_res = client.get("/api/matches/999999/summary")
        assert not_found_res.status_code == 404
        assert not_found_res.json()["detail"] == "Match summary not found"

    def test_get_highlights_and_frames(
        self,
        client: TestClient,
        temp_db: Path,
        sample_competitions: list[dict[str, Any]],
        sample_matches: list[dict[str, Any]],
    ) -> None:
        """GET /api/matches/{match_id}/highlights 및 frames 조회 검증."""
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
        hl_id = hl_ids[0]

        # 하이라이트 목록 조회 (200)
        hl_response = client.get("/api/matches/3788758/highlights")
        assert hl_response.status_code == 200
        highlights = hl_response.json()
        assert len(highlights) == 1
        assert highlights[0]["id"] == hl_id

        # 프레임 저장 전 frames 조회 시 404 Not Found
        empty_frame_res = client.get(f"/api/highlights/{hl_id}/frames")
        assert empty_frame_res.status_code == 404

        # 프레임 저장
        frames_payload = [
            {
                "frame_index": 0,
                "timestamp_sec": 202.0,
                "players": [],
                "passing_lanes": [
                    {
                        "from_location": [60.0, 40.0],
                        "to_location": [75.0, 50.0],
                        "is_open": True,
                        "is_selected": True,
                    }
                ],
            }
        ]
        players_payload = [{"player_id": 10655, "player_name": "Andriy Yarmolenko"}]
        save_highlight_frames(
            highlight_id=hl_id,
            match_id=3788758,
            frames_data=frames_payload,
            players_data=players_payload,
            has_360=True,
            db_path=temp_db,
        )

        # 프레임 조회 (200)
        frames_response = client.get(f"/api/highlights/{hl_id}/frames")
        assert frames_response.status_code == 200
        frames_data = frames_response.json()
        assert frames_data["has_360"] is True
        assert len(frames_data["frames"]) == 1
        assert len(frames_data["players"]) == 1
        assert "passing_lanes" in frames_data["frames"][0]
        assert frames_data["frames"][0]["passing_lanes"][0]["is_open"] is True
