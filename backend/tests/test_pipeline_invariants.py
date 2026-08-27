"""데이터 무결성 및 하이라이트 정합성 실용 테스트 스위트."""

from typing import Any

from app.analysis import analyze_match
from app.frames import build_highlight_frames
from app.highlights import extract_highlights


def test_match_summary_invariants(
    sample_events: list[dict[str, Any]],
    sample_lineups: list[dict[str, Any]],
    sample_three_sixty: list[dict[str, Any]],
) -> None:
    """분석 요약 결과가 핵심 전술 지표를 누락 없이 온전하게 포함하는지 검증합니다."""
    summary = analyze_match(sample_events, sample_lineups, sample_three_sixty)

    assert "teams" in summary
    assert len(summary["teams"]) == 2

    for _t_id, t_data in summary["teams"].items():
        # 1. 3대 국면 및 UEFA 6대 서브 국면 포메이션 무결성
        form = t_data.get("formation", {})
        assert "defensive" in form and "buildup" in form and "attacking" in form
        assert "subphases" in form

        # 선발 11명 정원 엄수 검증
        assert len(form.get("players", [])) <= 11
        assert len(form.get("players_in_possession", [])) <= 11
        assert len(form.get("players_out_of_possession", [])) <= 11

        subphases = form["subphases"]
        for sp_name in (
            "buildup",
            "progression",
            "final_third",
            "high_press",
            "mid_block",
            "low_block",
        ):
            sp_data = subphases[sp_name]
            assert "line_height" in sp_data and 10.0 <= sp_data["line_height"] <= 90.0
            assert "width" in sp_data and sp_data["width"] > 0
            assert "length" in sp_data and sp_data["length"] > 0
            assert "players" in sp_data
            # 국면별 선수 수는 11명을 초과할 수 없음
            assert len(sp_data["players"]) <= 11
            for p in sp_data["players"]:
                assert 0.0 <= p["x"] <= 120.0
                assert 0.0 <= p["y"] <= 80.0

        # 볼 미소유 3단계 라인 높이 물리적 변위 검증 (전방 압박 > 미들 블록 > 로우 블록)
        assert (
            subphases["high_press"]["line_height"]
            > subphases["mid_block"]["line_height"]
            > subphases["low_block"]["line_height"]
        )

        # 볼 소유 3단계 라인 높이 물리적 변위 검증 (기회 창출 > 중원 전개 > 후방 빌드업)
        assert (
            subphases["final_third"]["line_height"]
            > subphases["progression"]["line_height"]
            > subphases["buildup"]["line_height"]
        )

        for phase in ("defensive", "buildup", "attacking"):
            p_data = form[phase]
            assert "line_height" in p_data and 10.0 <= p_data["line_height"] <= 90.0
            assert "width" in p_data and p_data["width"] > 0
            assert "length" in p_data and p_data["length"] > 0
            assert "players" in p_data and len(p_data["players"]) <= 11
            for p in p_data["players"]:
                assert 0.0 <= p["x"] <= 120.0
                assert 0.0 <= p["y"] <= 80.0

        # 2. 학계 연구 기반 5대 시그니처 플레이북 무결성
        playbook = t_data.get("playbook", [])
        assert len(playbook) == 5
        for pattern in playbook:
            assert "pattern_id" in pattern
            assert "name_ko" in pattern
            assert "sequences" in pattern
            assert len(pattern["sequences"]) > 0

        # 3. 15분 전술 타임라인 무결성
        timeline = t_data.get("timeline", [])
        assert len(timeline) >= 6
        for sl in timeline:
            assert "label" in sl
            assert 0.0 <= sl["possession_pct"] <= 100.0
            assert 10.0 <= sl["defensive_line_height"] <= 90.0

        # 4. 압박 트랩 및 PPDA 무결성
        pressure = t_data.get("pressure", {})
        assert "ppda" in pressure and pressure["ppda"] is not None
        assert "pressure_traps" in pressure

        # 5. 패스 네트워크 무결성
        passes = t_data.get("passes", {})
        assert "nodes" in passes and len(passes["nodes"]) > 0
        assert "edges" in passes


def test_highlight_frames_invariants(
    sample_events: list[dict[str, Any]],
    sample_lineups: list[dict[str, Any]],
    sample_three_sixty: list[dict[str, Any]],
) -> None:
    """하이라이트 프레임의 단일 절대 좌표계 및 선수 정원 상한을 검증합니다."""
    highlights = extract_highlights(sample_events)
    assert len(highlights) > 0

    hl = highlights[0]
    frames, players_meta, _ = build_highlight_frames(
        events=sample_events,
        three_sixty_frames=sample_three_sixty,
        lineups=sample_lineups,
        highlight=hl,
    )

    assert len(frames) > 0

    for f in frames:
        # 1. 공 위치 범위 검증
        ball = f.get("ball_location")
        if ball is not None and len(ball) >= 2:
            assert -5.0 <= ball[0] <= 125.0
            assert -5.0 <= ball[1] <= 85.0

        # 2. 선수 정원 상한 및 중복 방지 검증 (아군 최대 11명, 상대팀 최대 11명, 총합 최대 22명)
        f_players = f.get("players", [])
        assert len(f_players) <= 22

        tm_players = [p for p in f_players if p.get("is_teammate")]
        opp_players = [p for p in f_players if not p.get("is_teammate")]

        assert len(tm_players) <= 11
        assert len(opp_players) <= 11

        # 선수 위치 범위 검증
        for p in f_players:
            loc = p.get("location")
            assert loc is not None and len(loc) >= 2
            assert -5.0 <= loc[0] <= 125.0
            assert -5.0 <= loc[1] <= 85.0
