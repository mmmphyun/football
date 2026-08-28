"""SQLite 기반 데이터베이스 스키마 정의 및 영속성 관리 모듈."""

import contextlib
import json
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.config import DB_PATH


def _dict_factory(cursor: sqlite3.Cursor, row: tuple) -> dict[str, Any]:
    """SQLite 행 튜플을 딕셔너리로 변환하는 팩토리 함수."""
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


@contextmanager
def get_db(db_path: Path | str | None = None) -> Generator[sqlite3.Connection]:
    """SQLite 데이터베이스 커넥션 컨텍스트 매니저.

    트랜잭션 커밋 및 롤백을 안전하게 보장하며,
    디렉터리가 미존재할 경우 자동 생성합니다.
    """
    target_path = Path(db_path) if db_path is not None else DB_PATH
    with contextlib.suppress(FileExistsError):
        target_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(target_path))
    conn.row_factory = _dict_factory
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: Path | str | None = None) -> None:
    """테이블 스키마를 생성하고 초기화합니다."""
    with get_db(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS competitions (
                competition_id INTEGER NOT NULL,
                season_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                season_name TEXT NOT NULL,
                country TEXT NOT NULL,
                match_count INTEGER NOT NULL DEFAULT 0,
                has_360 INTEGER NOT NULL DEFAULT 0,
                processed_at TEXT,
                PRIMARY KEY (competition_id, season_id)
            );

            CREATE TABLE IF NOT EXISTS matches (
                match_id INTEGER PRIMARY KEY,
                competition_id INTEGER NOT NULL,
                season_id INTEGER NOT NULL,
                home_team TEXT NOT NULL,
                away_team TEXT NOT NULL,
                home_team_id INTEGER NOT NULL,
                away_team_id INTEGER NOT NULL,
                home_score INTEGER,
                away_score INTEGER,
                match_date TEXT NOT NULL,
                has_360 INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'raw',
                FOREIGN KEY (competition_id, season_id)
                    REFERENCES competitions (competition_id, season_id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS match_summaries (
                match_id INTEGER PRIMARY KEY,
                summary_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (match_id)
                    REFERENCES matches (match_id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS highlights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id INTEGER NOT NULL,
                team_id INTEGER NOT NULL,
                team_name TEXT NOT NULL,
                type TEXT NOT NULL,
                minute INTEGER NOT NULL,
                second INTEGER NOT NULL,
                xg REAL NOT NULL DEFAULT 0.0,
                start_event INTEGER,
                end_event INTEGER,
                event_index INTEGER NOT NULL,
                window_start_sec REAL NOT NULL DEFAULT 0.0,
                window_end_sec REAL NOT NULL DEFAULT 0.0,
                FOREIGN KEY (match_id)
                    REFERENCES matches (match_id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS highlight_frames (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                highlight_id INTEGER NOT NULL UNIQUE,
                match_id INTEGER NOT NULL,
                frames_json TEXT NOT NULL,
                players_json TEXT NOT NULL,
                has_360 INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (highlight_id)
                    REFERENCES highlights (id)
                    ON DELETE CASCADE,
                FOREIGN KEY (match_id)
                    REFERENCES matches (match_id)
                    ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_matches_comp_season
                ON matches (competition_id, season_id);
            CREATE INDEX IF NOT EXISTS idx_highlights_match_id
                ON highlights (match_id);
            CREATE INDEX IF NOT EXISTS idx_highlight_frames_highlight_id
                ON highlight_frames (highlight_id);
            """
        )


def save_competitions(
    competitions: list[dict[str, Any]],
    db_path: Path | str | None = None,
) -> int:
    """대회 메타데이터 목록을 저장하거나 갱신합니다."""
    records = []
    for c in competitions:
        has_360 = (
            1 if (c.get("has_360") in (1, True) or c.get("match_available_360") is not None) else 0
        )
        records.append(
            {
                "competition_id": c["competition_id"],
                "season_id": c["season_id"],
                "name": c.get("name") or c.get("competition_name", ""),
                "season_name": c.get("season_name", ""),
                "country": c.get("country") or c.get("country_name", ""),
                "match_count": c.get("match_count", 0),
                "has_360": has_360,
                "processed_at": c.get("processed_at"),
            }
        )

    with get_db(db_path) as conn:
        conn.executemany(
            """
            INSERT INTO competitions (
                competition_id, season_id, name, season_name,
                country, match_count, has_360, processed_at
            ) VALUES (
                :competition_id, :season_id, :name, :season_name,
                :country, :match_count, :has_360, :processed_at
            )
            ON CONFLICT(competition_id, season_id) DO UPDATE SET
                name = excluded.name,
                season_name = excluded.season_name,
                country = excluded.country,
                match_count = excluded.match_count,
                has_360 = excluded.has_360,
                processed_at = excluded.processed_at
            """,
            records,
        )
    return len(records)


def get_competitions(db_path: Path | str | None = None) -> list[dict[str, Any]]:
    """저장된 전체 대회 목록을 조회합니다."""
    with get_db(db_path) as conn:
        cursor = conn.execute(
            """
            SELECT competition_id, season_id, name, season_name,
                   country, match_count, has_360, processed_at
            FROM competitions
            ORDER BY competition_id, season_id DESC
            """
        )
        return cursor.fetchall()


def save_matches(
    matches: list[dict[str, Any]],
    db_path: Path | str | None = None,
) -> int:
    """경기 메타데이터 목록을 저장하거나 갱신합니다."""
    records = []
    for m in matches:
        comp_id = m.get("competition_id")
        if comp_id is None:
            comp_id = m.get("competition", {}).get("competition_id", 0)

        season_id = m.get("season_id")
        if season_id is None:
            season_id = m.get("season", {}).get("season_id", 0)

        home_team = m.get("home_team")
        if isinstance(home_team, dict):
            home_team_name = home_team.get("home_team_name", "")
            home_team_id = home_team.get("home_team_id", 0)
        else:
            home_team_name = home_team or ""
            home_team_id = m.get("home_team_id", 0)

        away_team = m.get("away_team")
        if isinstance(away_team, dict):
            away_team_name = away_team.get("away_team_name", "")
            away_team_id = away_team.get("away_team_id", 0)
        else:
            away_team_name = away_team or ""
            away_team_id = m.get("away_team_id", 0)

        has_360 = (
            1 if (m.get("has_360") in (1, True) or m.get("match_status_360") == "available") else 0
        )

        records.append(
            {
                "match_id": m["match_id"],
                "competition_id": comp_id,
                "season_id": season_id,
                "home_team": home_team_name,
                "away_team": away_team_name,
                "home_team_id": home_team_id,
                "away_team_id": away_team_id,
                "home_score": m.get("home_score"),
                "away_score": m.get("away_score"),
                "match_date": m.get("match_date", ""),
                "has_360": has_360,
                "status": m.get("status", "raw"),
            }
        )

    with get_db(db_path) as conn:
        conn.executemany(
            """
            INSERT INTO matches (
                match_id, competition_id, season_id,
                home_team, away_team, home_team_id, away_team_id,
                home_score, away_score, match_date, has_360, status
            ) VALUES (
                :match_id, :competition_id, :season_id,
                :home_team, :away_team, :home_team_id, :away_team_id,
                :home_score, :away_score, :match_date, :has_360, :status
            )
            ON CONFLICT(match_id) DO UPDATE SET
                competition_id = excluded.competition_id,
                season_id = excluded.season_id,
                home_team = excluded.home_team,
                away_team = excluded.away_team,
                home_team_id = excluded.home_team_id,
                away_team_id = excluded.away_team_id,
                home_score = excluded.home_score,
                away_score = excluded.away_score,
                match_date = excluded.match_date,
                has_360 = excluded.has_360,
                status = excluded.status
            """,
            records,
        )
    return len(records)


def get_matches(
    competition_id: int,
    season_id: int,
    db_path: Path | str | None = None,
) -> list[dict[str, Any]]:
    """특정 대회 및 시즌의 경기 목록을 조회합니다."""
    with get_db(db_path) as conn:
        cursor = conn.execute(
            """
            SELECT match_id, competition_id, season_id,
                   home_team, away_team, home_team_id, away_team_id,
                   home_score, away_score, match_date, has_360, status
            FROM matches
            WHERE competition_id = ? AND season_id = ?
            ORDER BY match_date ASC, match_id ASC
            """,
            (competition_id, season_id),
        )
        return cursor.fetchall()


def get_match(
    match_id: int,
    db_path: Path | str | None = None,
) -> dict[str, Any] | None:
    """단일 경기 메타데이터를 조회합니다."""
    with get_db(db_path) as conn:
        cursor = conn.execute(
            """
            SELECT match_id, competition_id, season_id,
                   home_team, away_team, home_team_id, away_team_id,
                   home_score, away_score, match_date, has_360, status
            FROM matches
            WHERE match_id = ?
            """,
            (match_id,),
        )
        return cursor.fetchone()


def update_match_status(
    match_id: int,
    status: str,
    db_path: Path | str | None = None,
) -> None:
    """경기의 가공 상태(raw, processed, error 등)를 업데이트합니다."""
    with get_db(db_path) as conn:
        conn.execute(
            "UPDATE matches SET status = ? WHERE match_id = ?",
            (status, match_id),
        )


def save_match_summary(
    match_id: int,
    summary_data: dict[str, Any],
    db_path: Path | str | None = None,
) -> None:
    """경기의 8종 전술 분석 요약 결과를 JSON 형태로 저장합니다."""
    now_iso = datetime.now(UTC).isoformat()
    summary_json_str = json.dumps(summary_data, ensure_ascii=False)
    with get_db(db_path) as conn:
        conn.execute(
            """
            INSERT INTO match_summaries (match_id, summary_json, created_at)
            VALUES (?, ?, ?)
            ON CONFLICT(match_id) DO UPDATE SET
                summary_json = excluded.summary_json,
                created_at = excluded.created_at
            """,
            (match_id, summary_json_str, now_iso),
        )


def get_match_summary(
    match_id: int,
    db_path: Path | str | None = None,
) -> dict[str, Any] | None:
    """경기의 8종 전술 분석 요약 데이터를 복원하여 반환합니다."""
    with get_db(db_path) as conn:
        cursor = conn.execute(
            "SELECT summary_json FROM match_summaries WHERE match_id = ?",
            (match_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return json.loads(row["summary_json"])


def save_highlights(
    match_id: int,
    highlights: list[dict[str, Any]],
    db_path: Path | str | None = None,
) -> list[int]:
    """경기의 하이라이트 목록을 저장하고 생성된 하이라이트 ID 목록을 반환합니다."""
    saved_ids: list[int] = []
    with get_db(db_path) as conn:
        # 기존 하이라이트 초기화 후 재삽입 (하이라이트-프레임 종속성 초기화)
        conn.execute("DELETE FROM highlights WHERE match_id = ?", (match_id,))
        for hl in highlights:
            cursor = conn.execute(
                """
                INSERT INTO highlights (
                    match_id, team_id, team_name, type, minute, second,
                    xg, start_event, end_event, event_index,
                    window_start_sec, window_end_sec
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    match_id,
                    hl["team_id"],
                    hl["team_name"],
                    hl["type"],
                    hl["minute"],
                    hl["second"],
                    hl.get("xg", 0.0),
                    hl.get("start_event"),
                    hl.get("end_event"),
                    hl["event_index"],
                    hl.get("window_start_sec", 0.0),
                    hl.get("window_end_sec", 0.0),
                ),
            )
            saved_ids.append(cursor.lastrowid)
    return saved_ids


def get_highlights(
    match_id: int,
    db_path: Path | str | None = None,
) -> list[dict[str, Any]]:
    """경기의 모든 하이라이트 항목을 조회합니다."""
    with get_db(db_path) as conn:
        cursor = conn.execute(
            """
            SELECT id, match_id, team_id, team_name, type, minute, second,
                   xg, start_event, end_event, event_index,
                   window_start_sec, window_end_sec
            FROM highlights
            WHERE match_id = ?
            ORDER BY minute ASC, second ASC, id ASC
            """,
            (match_id,),
        )
        return cursor.fetchall()


def save_highlight_frames(
    highlight_id: int,
    match_id: int,
    frames_data: list[dict[str, Any]],
    players_data: list[dict[str, Any]],
    has_360: bool,
    db_path: Path | str | None = None,
) -> int:
    """하이라이트의 인터랙티브 프레임 시퀀스 및 선수 정보를 저장합니다."""
    frames_json_str = json.dumps(frames_data, ensure_ascii=False)
    players_json_str = json.dumps(players_data, ensure_ascii=False)
    has_360_int = 1 if has_360 else 0

    with get_db(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO highlight_frames (
                highlight_id, match_id, frames_json, players_json, has_360
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(highlight_id) DO UPDATE SET
                frames_json = excluded.frames_json,
                players_json = excluded.players_json,
                has_360 = excluded.has_360
            """,
            (highlight_id, match_id, frames_json_str, players_json_str, has_360_int),
        )
        return cursor.lastrowid


def get_highlight_frames(
    highlight_id: int,
    db_path: Path | str | None = None,
) -> dict[str, Any] | None:
    """하이라이트의 프레임 데이터 및 선수 메타데이터를 역직렬화하여 반환합니다."""
    with get_db(db_path) as conn:
        cursor = conn.execute(
            """
            SELECT id, highlight_id, match_id, frames_json, players_json, has_360
            FROM highlight_frames
            WHERE highlight_id = ?
            """,
            (highlight_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return {
            "id": row["id"],
            "highlight_id": row["highlight_id"],
            "match_id": row["match_id"],
            "frames": json.loads(row["frames_json"]),
            "players": json.loads(row["players_json"]),
            "has_360": bool(row["has_360"]),
        }
