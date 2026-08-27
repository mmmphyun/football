from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.storage import (
    get_competitions,
    get_highlight_frames,
    get_highlights,
    get_match,
    get_match_summary,
    get_matches,
    init_db,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """애플리케이션 시작 시 DB 테이블을 초기화합니다."""
    init_db()
    yield


app = FastAPI(
    title="Football Tactical Analysis API",
    description="StatsBomb Open Data & 360 전술 분석 및 하이라이트 인터랙티브 API",
    version="0.3.0",
    lifespan=lifespan,
)

# 프론트엔드 연동을 위한 CORS 미들웨어 등록
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", summary="헬스 체크")
def health_check() -> dict[str, str]:
    """API 서버 가동 상태를 반환합니다."""
    return {"status": "ok"}


@app.get("/api/competitions", summary="대회 목록 조회")
def list_competitions() -> list[dict[str, Any]]:
    """DB에 저장된 360 지원 대회 목록을 조회합니다."""
    return get_competitions()


@app.get("/api/competitions/{comp_id}/matches", summary="대회별 경기 목록 조회")
def list_matches(
    comp_id: int,
    season_id: int = Query(..., description="시즌 ID"),
) -> list[dict[str, Any]]:
    """특정 대회 및 시즌의 경기 목록을 조회합니다."""
    return get_matches(competition_id=comp_id, season_id=season_id)


@app.get("/api/matches/{match_id}", summary="단일 경기 정보 조회")
def get_match_detail(match_id: int) -> dict[str, Any]:
    """단일 경기 메타데이터를 조회합니다."""
    match = get_match(match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")
    return match


@app.get("/api/matches/{match_id}/summary", summary="경기 전술 분석 요약 조회")
def get_summary(match_id: int) -> dict[str, Any]:
    """경기의 8종 전술 분석 요약 데이터를 조회합니다."""
    summary = get_match_summary(match_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="Match summary not found")
    return summary


@app.get("/api/matches/{match_id}/highlights", summary="경기 하이라이트 목록 조회")
def list_highlights(match_id: int) -> list[dict[str, Any]]:
    """경기의 골 및 고xG 하이라이트 목록을 조회합니다."""
    return get_highlights(match_id)


@app.get("/api/highlights/{highlight_id}/frames", summary="하이라이트 프레임 시퀀스 조회")
def get_frames(highlight_id: int) -> dict[str, Any]:
    """하이라이트의 360 위치, 속도, 외삽 프레임 시퀀스 및 선수 정보를 조회합니다."""
    frames_data = get_highlight_frames(highlight_id)
    if frames_data is None:
        raise HTTPException(status_code=404, detail="Highlight frames not found")
    return frames_data
