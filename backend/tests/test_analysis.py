"""8종 전술 분석 모듈 단위 테스트 스위트."""

import math
from typing import Any

from app.analysis.buildup import compute_buildup_summary
from app.analysis.common import (
    build_lineup_maps,
    event_time,
    get_match_duration_min,
    get_opponent_team_id,
    get_team_ids,
    is_completed_pass,
    point_in_polygon,
)
from app.analysis.formation import (
    POSITION_ANCHORS,
    compute_formation_summary,
    get_position_anchor,
)
from app.analysis.passes import compute_pass_network
from app.analysis.playbook import compute_playbook_summary
from app.analysis.predict import (
    calculate_velocity,
    extrapolate_frame_players,
    extrapolate_player_position,
)
from app.analysis.pressure import compute_pressure_summary
from app.analysis.timeline import compute_timeline_summary
from app.analysis.transitions import compute_transitions_summary
from app.analysis.zones import compute_zones_summary
from app.config import (
    EXTRAPOLATION_MAX_SPEED,
    PITCH_LENGTH,
    PITCH_WIDTH,
    ZONES_X,
    ZONES_Y,
)


class TestCommonUtils:
    """공통 도메인 유틸리티 함수 테스트."""

    def test_event_time(self) -> None:
        """이벤트 분/초 기준 누적 초 계산 검증."""
        ev1 = {"minute": 3, "second": 45}
        assert event_time(ev1) == 225.0

        ev2 = {"minute": 93, "second": 20}
        assert event_time(ev2) == 5600.0

    def test_get_match_duration_min(self) -> None:
        """최소 90분 보장 및 최대 시간 산출 검증."""
        events = [{"minute": 10}, {"minute": 45}, {"minute": 88}]
        assert get_match_duration_min(events) == 90.0

        extra_events = [{"minute": 10}, {"minute": 95}]
        assert get_match_duration_min(extra_events) == 95.0

        assert get_match_duration_min([]) == 90.0

    def test_is_completed_pass(self) -> None:
        """패스 성공/실패 여부 판별 검증."""
        comp_pass = {"type": {"name": "Pass"}, "pass": {"outcome": None}}
        assert is_completed_pass(comp_pass) is True

        incomp_pass = {
            "type": {"name": "Pass"},
            "pass": {"outcome": {"id": 9, "name": "Incomplete"}},
        }
        assert is_completed_pass(incomp_pass) is False

        shot_ev = {"type": {"name": "Shot"}}
        assert is_completed_pass(shot_ev) is False

    def test_get_team_ids_and_opponent(self, sample_events: list[dict[str, Any]]) -> None:
        """팀 ID 및 상대팀 ID 추출 검증."""
        team_ids = get_team_ids(sample_events)
        assert len(team_ids) == 2
        assert 911 in team_ids
        assert 2358 in team_ids

        assert get_opponent_team_id(911, sample_events) == 2358
        assert get_opponent_team_id(2358, sample_events) == 911

    def test_point_in_polygon(self) -> None:
        """시야각 폴리곤 내 점 포함 여부 검증."""
        # 10x10 정사각형
        poly = [0.0, 0.0, 10.0, 0.0, 10.0, 10.0, 0.0, 10.0, 0.0, 0.0]
        assert point_in_polygon(5.0, 5.0, poly) is True
        assert point_in_polygon(15.0, 5.0, poly) is False
        assert point_in_polygon(0.0, 0.0, []) is True  # 빈 폴리곤은 True

    def test_build_lineup_maps(self, sample_lineups: list[dict[str, Any]]) -> None:
        """라인업 데이터 매핑 무결성 검증."""
        lineup_maps = build_lineup_maps(sample_lineups)
        assert 911 in lineup_maps
        assert 2358 in lineup_maps

        ukraine = lineup_maps[911]
        assert ukraine["team_name"] == "Ukraine"
        assert 3575 in ukraine["players"]
        zinchenko = ukraine["players"][3575]
        assert zinchenko["player_name"] == "Oleksandr Zinchenko"
        assert zinchenko["jersey_number"] == 17
        assert zinchenko["is_starter"] is True


class TestFormationAnalysis:
    """포메이션 및 선수 평균 위치 분석 테스트."""

    def test_get_position_anchor(self) -> None:
        """포지션 ID별 표준 앵커 좌표 검증."""
        assert get_position_anchor(1) == POSITION_ANCHORS[1]
        assert get_position_anchor(9999) == (60.0, 40.0)
        assert get_position_anchor(None) == (60.0, 40.0)

    def test_compute_formation_summary(
        self,
        sample_events: list[dict[str, Any]],
        sample_lineups: list[dict[str, Any]],
    ) -> None:
        """팀 포메이션 및 3대 국면(수비/빌드업/공격) 선수 위치 산출 검증."""
        summary_ukr = compute_formation_summary(sample_events, sample_lineups, team_id=911)
        assert summary_ukr["team_id"] == 911
        assert summary_ukr["formation"] == "433"
        assert len(summary_ukr["players_overall"]) > 0
        assert summary_ukr["team_length"] > 0
        assert summary_ukr["team_width"] > 0

        # 3대 국면 검증
        assert "defensive" in summary_ukr
        assert "buildup" in summary_ukr
        assert "attacking" in summary_ukr

        assert summary_ukr["defensive"]["line_height"] > 0
        assert summary_ukr["buildup"]["line_height"] > 0
        assert summary_ukr["attacking"]["line_height"] > 0
        assert len(summary_ukr["defensive"]["players"]) > 0
        assert len(summary_ukr["buildup"]["players"]) > 0
        assert len(summary_ukr["attacking"]["players"]) > 0

        # Zinchenko (3575)의 위치 데이터 포함 여부
        zinchenko = next(p for p in summary_ukr["players_overall"] if p["player_id"] == 3575)
        assert zinchenko["event_count"] >= 1
        assert 0.0 <= zinchenko["x"] <= PITCH_LENGTH
        assert 0.0 <= zinchenko["y"] <= PITCH_WIDTH


class TestZonesAnalysis:
    """12x8 피치 구역 점유율 분석 테스트."""

    def test_compute_zones_summary_with_360(
        self,
        sample_events: list[dict[str, Any]],
        sample_three_sixty: list[dict[str, Any]],
    ) -> None:
        """360 프레임 기반 12x8 점유율 계산 및 정규화 검증."""
        summary = compute_zones_summary(
            events=sample_events,
            team_id=911,
            three_sixty_frames=sample_three_sixty,
        )
        assert summary["team_id"] == 911
        assert summary["zones_x"] == ZONES_X
        assert summary["zones_y"] == ZONES_Y
        assert summary["has_360"] is True

        grid = summary["overall_grid"]
        assert len(grid) == ZONES_Y
        assert len(grid[0]) == ZONES_X

        # 정규화된 그리드 합계가 약 1.0인지 검증
        total_density = sum(sum(row) for row in grid)
        assert math.isclose(total_density, 1.0, abs_tol=1e-3)

    def test_compute_zones_summary_fallback(
        self,
        sample_events: list[dict[str, Any]],
    ) -> None:
        """360 데이터 부재 시 일반 이벤트 위치 기반 fallback 검증."""
        summary = compute_zones_summary(
            events=sample_events,
            team_id=911,
            three_sixty_frames=None,
        )
        assert summary["has_360"] is False
        total_density = sum(sum(row) for row in summary["overall_grid"])
        assert math.isclose(total_density, 1.0, abs_tol=1e-3)


class TestPassesAnalysis:
    """패스 네트워크 및 전진성 분석 테스트."""

    def test_compute_pass_network(
        self,
        sample_events: list[dict[str, Any]],
        sample_lineups: list[dict[str, Any]],
    ) -> None:
        """패스 네트워크 노드, 엣지 및 전진성 계산 검증."""
        res = compute_pass_network(
            events=sample_events,
            lineups=sample_lineups,
            team_id=911,
            top_edges_limit=15,
        )
        assert res["team_id"] == 911
        assert res["total_passes"] >= 3
        assert res["completed_passes"] >= 2
        assert 0.0 <= res["pass_accuracy"] <= 1.0
        assert res["progressive_passes"] >= 1
        assert len(res["nodes"]) > 0
        assert len(res["edges"]) <= 15


class TestPressureAnalysis:
    """압박 강도, PPDA 및 압박 트랩 핫스팟 분석 테스트."""

    def test_compute_pressure_summary(
        self,
        sample_events: list[dict[str, Any]],
    ) -> None:
        """상대 진영 x>=40 기준 PPDA, 분당 압박 횟수 및 압박 트랩 검증."""
        res_mkd = compute_pressure_summary(events=sample_events, team_id=2358)
        assert res_mkd["team_id"] == 2358
        assert res_mkd["total_pressures"] >= 1
        assert res_mkd["high_press_defensive_actions"] >= 1
        assert res_mkd["ppda"] >= 0.0
        assert res_mkd["pressures_per_min"] >= 0.0
        assert "pressure_traps" in res_mkd
        assert len(res_mkd["pressure_traps"]) > 0


class TestPlaybookAnalysis:
    """시그니처 공격 패턴 TOP 3 플레이북 분석 테스트."""

    def test_compute_playbook_summary(
        self,
        sample_events: list[dict[str, Any]],
    ) -> None:
        """시그니처 공격 패턴 TOP 3 추출 및 시퀀스 무결성 검증."""
        playbook = compute_playbook_summary(events=sample_events, team_id=911)
        assert len(playbook) == 3
        for item in playbook:
            assert "pattern_id" in item
            assert "name" in item
            assert "name_ko" in item
            assert "occurrences" in item
            assert "total_xg" in item
            assert "sequences" in item
            assert len(item["sequences"]) > 0


class TestTimelineAnalysis:
    """시간대별 전술 타임라인 분석 테스트."""

    def test_compute_timeline_summary(
        self,
        sample_events: list[dict[str, Any]],
    ) -> None:
        """15분 단위 전술 슬라이스 및 지표 산출 검증."""
        timeline = compute_timeline_summary(events=sample_events, team_id=911, interval_min=15)
        assert len(timeline) >= 6
        for sl in timeline:
            assert "minute_start" in sl
            assert "minute_end" in sl
            assert "possession_pct" in sl
            assert "pass_accuracy" in sl
            assert "defensive_line_height" in sl
            assert "phase_distribution" in sl


class TestBuildupAnalysis:
    """빌드업 및 전진 전개 분석 테스트."""

    def test_compute_buildup_summary(
        self,
        sample_events: list[dict[str, Any]],
    ) -> None:
        """3분할 시작 지점 및 전진 패스/캐리 비율 검증."""
        res = compute_buildup_summary(events=sample_events, team_id=911)
        assert res["team_id"] == 911
        assert res["total_possessions"] >= 1
        assert "buildup_start_distribution" in res
        assert "progression" in res
        prog = res["progression"]
        assert prog["total_passes"] >= 1
        assert prog["total_carries"] >= 1


class TestTransitionsAnalysis:
    """공수 전환 속도 및 속공/지공 분석 테스트."""

    def test_compute_transitions_summary(
        self,
        sample_events: list[dict[str, Any]],
    ) -> None:
        """공 회수 후 8초 이내 속공 전환 판정 검증."""
        res = compute_transitions_summary(events=sample_events, team_id=2358)
        assert res["team_id"] == 2358
        assert res["total_recoveries"] >= 1
        assert res["fast_transitions"] >= 1
        assert 0.0 <= res["fast_transition_ratio"] <= 1.0


class TestPredictEngine:
    """단기 외삽 및 물리 예측 엔진 테스트."""

    def test_calculate_velocity(self) -> None:
        """속도 벡터 계산 및 최대 속도 클램프 검증."""
        vx, vy = calculate_velocity([0.0, 0.0], [6.0, 8.0], dt=1.0)
        # 속도 10.0 -> 최대 속도 8.0으로 스케일링 (vx=4.8, vy=6.4)
        speed = math.sqrt(vx * vx + vy * vy)
        assert math.isclose(speed, EXTRAPOLATION_MAX_SPEED, abs_tol=1e-2)

        # dt <= 0일 때 0 반환
        assert calculate_velocity([0.0, 0.0], [5.0, 5.0], dt=0.0) == (0.0, 0.0)

    def test_extrapolate_player_position_clamping(self) -> None:
        """피치 경계(120x80) 클램핑 및 앵커 복원력 검증."""
        # 피치 밖으로 벗어나는 속도
        pred_x, pred_y = extrapolate_player_position(
            x=118.0,
            y=78.0,
            vx=10.0,
            vy=10.0,
            dt=2.0,
        )
        assert 0.0 <= pred_x <= PITCH_LENGTH
        assert 0.0 <= pred_y <= PITCH_WIDTH

    def test_extrapolate_frame_players(self) -> None:
        """선수 리스트 일괄 외삽 적용 검증."""
        players = [
            {"player_id": 1, "location": [50.0, 30.0], "vx": 2.0, "vy": 1.0},
            {"player_id": 2, "location": [80.0, 40.0], "vx": -1.5, "vy": 0.5},
        ]
        result = extrapolate_frame_players(players, dt=2.0)
        assert len(result) == 2
        for p in result:
            assert "pred_x" in p
            assert "pred_y" in p
            assert "pred_location" in p
            assert len(p["pred_location"]) == 2
