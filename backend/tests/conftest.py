"""Pytest 공통 픽스처 및 테스트 환경 설정 모듈."""

import json
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

import app.storage as storage
from app.main import app


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    """테스트 픽스처 디렉터리 경로를 반환합니다."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def sample_competitions(fixtures_dir: Path) -> list[dict[str, Any]]:
    """대회 픽스처 데이터를 로드합니다."""
    with open(fixtures_dir / "competitions.json", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def sample_matches(fixtures_dir: Path) -> list[dict[str, Any]]:
    """경기 픽스처 데이터를 로드합니다."""
    with open(fixtures_dir / "matches.json", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def sample_lineups(fixtures_dir: Path) -> list[dict[str, Any]]:
    """라인업 픽스처 데이터를 로드합니다."""
    with open(fixtures_dir / "lineups.json", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def sample_events(fixtures_dir: Path) -> list[dict[str, Any]]:
    """이벤트 픽스처 데이터를 로드합니다."""
    with open(fixtures_dir / "events.json", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def sample_three_sixty(fixtures_dir: Path) -> list[dict[str, Any]]:
    """360 트래킹 프레임 픽스처 데이터를 로드합니다."""
    with open(fixtures_dir / "three_sixty.json", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def temp_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[Path]:
    """각 테스트별 격리된 임시 SQLite DB를 생성하고 초기화합니다."""
    db_file = tmp_path / "test_tactics.db"
    monkeypatch.setattr(storage, "DB_PATH", db_file)
    storage.init_db()
    yield db_file


@pytest.fixture
def client(temp_db: Path) -> Generator[TestClient]:
    """FastAPI TestClient fixture."""
    with TestClient(app) as test_client:
        yield test_client
