"""HTTP access to StatsBomb Open Data on GitHub."""

import time
from typing import Any, Optional

import httpx

from . import config


class DownloadError(RuntimeError):
    pass


def _get(url: str, retries: int = 3) -> httpx.Response:
    last_error: Optional[Exception] = None
    for attempt in range(retries):
        try:
            resp = httpx.get(url, timeout=30, follow_redirects=True)
            if resp.status_code == 404:
                return resp
            resp.raise_for_status()
            return resp
        except Exception as exc:  # noqa: BLE001 - retry any transient failure
            last_error = exc
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    raise DownloadError(f"Failed to download {url}: {last_error}")


def fetch_json(url: str, retries: int = 3) -> Any:
    resp = _get(url, retries=retries)
    if resp.status_code == 404:
        return None
    return resp.json()


def fetch_competitions() -> list[dict[str, Any]]:
    return fetch_json(f"{config.SB_RAW_BASE}/competitions.json") or []


def fetch_matches(competition_id: int, season_id: int) -> list[dict[str, Any]]:
    return (
        fetch_json(
            f"{config.SB_RAW_BASE}/matches/{competition_id}/{season_id}.json"
        )
        or []
    )


def fetch_events(match_id: int) -> Optional[list[dict[str, Any]]]:
    return fetch_json(f"{config.SB_RAW_BASE}/events/{match_id}.json")


def fetch_lineups(match_id: int) -> Optional[list[dict[str, Any]]]:
    return fetch_json(f"{config.SB_RAW_BASE}/lineups/{match_id}.json")


def fetch_three_sixty(match_id: int) -> Optional[list[dict[str, Any]]]:
    return fetch_json(f"{config.SB_RAW_BASE}/three-sixty/{match_id}.json")


def fetch_three_sixty_index() -> Optional[set[int]]:
    """List match ids that have 360 data, via the GitHub contents API."""
    data = fetch_json(f"{config.SB_API_BASE}/three-sixty", retries=2)
    if data is None or not isinstance(data, list):
        return None
    match_ids: set[int] = set()
    for entry in data:
        name = entry.get("name", "")
        if name.endswith(".json"):
            try:
                match_ids.add(int(name[:-5]))
            except ValueError:
                continue
    return match_ids