"""하이라이트 추출 및 360 프레임 빌더 단위 테스트 스위트."""

from typing import Any

from app.config import MIN_HIGHLIGHT_XG
from app.frames import build_highlight_frames
from app.highlights import extract_highlights, is_goal_event, is_high_xg_shot


class TestHighlightExtraction:
    """골/고xG 판정 및 포제션 윈도우 클리핑 테스트."""

    def test_is_goal_event(self) -> None:
        """골 및 자책골 판별 검증."""
        goal_shot = {
            "type": {"name": "Shot"},
            "shot": {"outcome": {"name": "Goal"}},
        }
        assert is_goal_event(goal_shot) is True

        saved_shot = {
            "type": {"name": "Shot"},
            "shot": {"outcome": {"name": "Saved"}},
        }
        assert is_goal_event(saved_shot) is False

        own_goal = {"type": {"name": "Own Goal Against"}}
        assert is_goal_event(own_goal) is True

        pass_ev = {"type": {"name": "Pass"}}
        assert is_goal_event(pass_ev) is False

    def test_is_high_xg_shot(self) -> None:
        """고xG 슈팅(기본 임계값 0.25) 판별 검증."""
        high_xg = {
            "type": {"name": "Shot"},
            "shot": {"statsbomb_xg": 0.38},
        }
        assert is_high_xg_shot(high_xg, min_xg=MIN_HIGHLIGHT_XG) is True

        low_xg = {
            "type": {"name": "Shot"},
            "shot": {"statsbomb_xg": 0.08},
        }
        assert is_high_xg_shot(low_xg, min_xg=MIN_HIGHLIGHT_XG) is False

    def test_extract_highlights(self, sample_events: list[dict[str, Any]]) -> None:
        """하이라이트 추출 및 포제션 윈도우 인덱스 산출 검증."""
        highlights = extract_highlights(sample_events, min_xg=MIN_HIGHLIGHT_XG)
        # sample_events에는 1개의 Goal(Yarmolenko)과 1개의 High xG Shot(Velkovski, xG 0.28)이 포함됨
        assert len(highlights) >= 2

        # 첫 번째 하이라이트 (Goal)
        hl_goal = highlights[0]
        assert hl_goal["type"] == "Goal"
        assert hl_goal["team_name"] == "Ukraine"
        assert hl_goal["team_id"] == 911
        assert hl_goal["xg"] == 0.38
        assert hl_goal["start_event"] <= hl_goal["event_index"] <= hl_goal["end_event"]
        assert hl_goal["window_start_sec"] <= hl_goal["window_end_sec"]


class TestFrameBuilder:
    """360 프레임 시퀀스 빌더 테스트."""

    def test_build_highlight_frames(
        self,
        sample_events: list[dict[str, Any]],
        sample_three_sixty: list[dict[str, Any]],
        sample_lineups: list[dict[str, Any]],
    ) -> None:
        """360 트래킹 프레임 시퀀스 및 선수 메타데이터 생성 검증."""
        highlights = extract_highlights(sample_events)
        assert len(highlights) > 0
        hl = highlights[0]

        frames, players_list, has_360 = build_highlight_frames(
            events=sample_events,
            three_sixty_frames=sample_three_sixty,
            lineups=sample_lineups,
            highlight=hl,
        )

        assert len(frames) > 0
        assert len(players_list) > 0
        assert isinstance(has_360, bool)

        # 프레임 내부 필수 필드 및 passing_lanes 검증
        first_frame = frames[0]
        assert "frame_index" in first_frame
        assert "timestamp_sec" in first_frame
        assert "players" in first_frame
        assert "visible_area" in first_frame
        assert "description" in first_frame
        assert "event_type" in first_frame
        assert "passing_lanes" in first_frame
        assert isinstance(first_frame["passing_lanes"], list)

        # 선수 정보 내부 외삽(pred_x, pred_y) 검증
        for p in first_frame["players"]:
            assert "location" in p
            assert "pred_location" in p
            assert "is_actor" in p
            assert "is_keeper" in p
