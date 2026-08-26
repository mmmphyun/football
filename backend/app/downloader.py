"""StatsBomb Open Data 다운로더 및 디스크 캐싱 모듈."""

import json
import logging
import time
from pathlib import Path
from typing import Any

import httpx

from app.config import (
    MIN_MATCHES_360_FILTER,
    RAW_DATA_DIR,
    STATSBOMB_RAW_BASE_URL,
)

logger = logging.getLogger(__name__)


class StatsBombDownloader:
    """StatsBomb GitHub Raw 데이터 다운로드 및 로컬 캐시 관리 클래스."""

    def __init__(
        self,
        base_url: str = STATSBOMB_RAW_BASE_URL,
        raw_dir: Path | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.raw_dir = raw_dir if raw_dir is not None else RAW_DATA_DIR
        self.timeout = timeout
        self.max_retries = max_retries
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, relative_path: str) -> Path:
        """상대 경로에 대응하는 로컬 캐시 파일 경로를 반환합니다."""
        return self.raw_dir / relative_path

    def _read_cache(self, relative_path: str) -> Any | None:
        """디스크 캐시가 존재할 경우 JSON 데이터를 파싱하여 반환합니다."""
        cache_file = self._get_cache_path(relative_path)
        if cache_file.exists():
            try:
                with open(cache_file, encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("캐시 파일 읽기 실패 (%s): %s", cache_file, e)
        return None

    def _write_cache(self, relative_path: str, data: Any) -> None:
        """데이터를 로컬 디스크 캐시에 JSON 포맷으로 저장합니다."""
        cache_file = self._get_cache_path(relative_path)
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def fetch_json(
        self,
        relative_path: str,
        force: bool = False,
        allow_404: bool = False,
    ) -> Any | None:
        """지정된 상대 경로의 JSON 데이터를 다운로드하거나 캐시에서 반환합니다.

        네트워크 실패 시 max_retries 횟수만큼 지수 백오프로 재시도합니다.
        """
        if not force:
            cached = self._read_cache(relative_path)
            if cached is not None:
                return cached

        url = f"{self.base_url}/{relative_path}"
        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.get(url)
                    if response.status_code == 404:
                        if allow_404:
                            return None
                        response.raise_for_status()

                    response.raise_for_status()
                    data = response.json()
                    self._write_cache(relative_path, data)
                    return data
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404 and allow_404:
                    return None
                last_error = e
                logger.warning(
                    "HTTP 요청 오류 [%s] (시도 %d/%d): %s",
                    url,
                    attempt,
                    self.max_retries,
                    e,
                )
            except (httpx.RequestError, json.JSONDecodeError) as e:
                last_error = e
                logger.warning(
                    "네트워크 또는 JSON 파싱 오류 [%s] (시도 %d/%d): %s",
                    url,
                    attempt,
                    self.max_retries,
                    e,
                )

            if attempt < self.max_retries:
                time.sleep(1.0 * (2 ** (attempt - 1)))

        if last_error is not None:
            raise last_error
        return None

    def fetch_competitions(self, force: bool = False) -> list[dict[str, Any]]:
        """competitions.json 파일을 다운로드하여 전체 대회 목록을 반환합니다."""
        data = self.fetch_json("competitions.json", force=force)
        return data if isinstance(data, list) else []

    def detect_360_competitions(
        self,
        force: bool = False,
        min_matches: int = MIN_MATCHES_360_FILTER,
    ) -> list[dict[str, Any]]:
        """StatsBomb 360 트래킹 데이터가 제공되는 대회를 필터링하여 반환합니다.

        match_available_360 필드가 존재하는 대회를 추출합니다.
        """
        competitions = self.fetch_competitions(force=force)
        detected: list[dict[str, Any]] = []

        for comp in competitions:
            has_360 = comp.get("match_available_360") is not None
            if has_360:
                detected.append(comp)

        return detected

    def fetch_matches(
        self,
        competition_id: int,
        season_id: int,
        force: bool = False,
    ) -> list[dict[str, Any]]:
        """특정 대회 및 시즌의 경기 목록(matches/{comp_id}/{season_id}.json)을 가져옵니다."""
        rel_path = f"matches/{competition_id}/{season_id}.json"
        data = self.fetch_json(rel_path, force=force)
        return data if isinstance(data, list) else []

    def fetch_events(self, match_id: int, force: bool = False) -> list[dict[str, Any]]:
        """특정 경기의 이벤트 스트림(events/{match_id}.json)을 가져옵니다."""
        rel_path = f"events/{match_id}.json"
        data = self.fetch_json(rel_path, force=force)
        return data if isinstance(data, list) else []

    def fetch_lineups(self, match_id: int, force: bool = False) -> list[dict[str, Any]]:
        """특정 경기의 라인업 정보(lineups/{match_id}.json)를 가져옵니다."""
        rel_path = f"lineups/{match_id}.json"
        data = self.fetch_json(rel_path, force=force)
        return data if isinstance(data, list) else []

    def fetch_three_sixty(
        self,
        match_id: int,
        force: bool = False,
    ) -> list[dict[str, Any]] | None:
        """특정 경기의 360 프레임 데이터(three-sixty/{match_id}.json)를 가져옵니다.

        360 데이터가 미제공되는 경기(404)의 경우 None을 반환합니다.
        """
        rel_path = f"three-sixty/{match_id}.json"
        data = self.fetch_json(rel_path, force=force, allow_404=True)
        return data if isinstance(data, list) else None

    def fetch_full_match_bundle(
        self,
        match_id: int,
        force: bool = False,
    ) -> dict[str, Any]:
        """경기에 필요한 events, lineups, three-sixty 데이터를 한 번에 수집합니다."""
        events = self.fetch_events(match_id, force=force)
        lineups = self.fetch_lineups(match_id, force=force)
        three_sixty = self.fetch_three_sixty(match_id, force=force)

        return {
            "match_id": match_id,
            "events": events,
            "lineups": lineups,
            "three_sixty": three_sixty,
            "has_360": three_sixty is not None and len(three_sixty) > 0,
        }
