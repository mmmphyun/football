"""SQLite storage for processed data and raw-file bookkeeping."""

import json
import sqlite3
from typing import Any, Optional

from . import config

_SCHEMA = """
CREATE TABLE IF NOT EXISTS competitions (
    competition_id INTEGER NOT NULL,
    season_id INTEGER NOT NULL,
    name TEXT,
    season_name TEXT,
    country TEXT,
    match_count INTEGER,
    has_360 INTEGER DEFAULT 0,
    processed_at TEXT,
    PRIMARY KEY (competition_id, season_id)
);

CREATE TABLE IF NOT EXISTS matches (
    match_id INTEGER PRIMARY KEY,
    competition_id INTEGER,
    season_id INTEGER,
    home_team TEXT,
    away_team TEXT,
    home_team_id INTEGER,
    away_team_id INTEGER,
    home_score INTEGER,
    away_score INTEGER,
    match_date TEXT,
    has_360 INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS match_summaries (
    match_id INTEGER PRIMARY KEY,
    summary_json TEXT
);

CREATE TABLE IF NOT EXISTS highlights (
    id TEXT PRIMARY KEY,
    match_id INTEGER,
    team_id INTEGER,
    team_name TEXT,
    type TEXT,
    minute INTEGER,
    second INTEGER,
    xg REAL,
    start_event INTEGER,
    end_event INTEGER,
    event_index INTEGER
);

CREATE TABLE IF NOT EXISTS highlight_frames (
    id TEXT PRIMARY KEY,
    match_id INTEGER,
    frames_json TEXT,
    players_json TEXT,
    has_360 INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_matches_competition ON matches (competition_id, season_id);
CREATE INDEX IF NOT EXISTS idx_highlights_match ON highlights (match_id);
"""


def connect() -> sqlite3.Connection:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = connect()
    try:
        conn.executescript(_SCHEMA)
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------- competitions

def upsert_competition(comp: dict[str, Any]) -> None:
    conn = connect()
    try:
        conn.execute(
            """INSERT INTO competitions
               (competition_id, season_id, name, season_name, country, processed_at)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(competition_id, season_id) DO UPDATE SET
                 name=excluded.name, season_name=excluded.season_name,
                 country=excluded.country, processed_at=excluded.processed_at""",
            (
                comp["competition_id"],
                comp["season_id"],
                comp.get("competition_name"),
                comp.get("season_name"),
                comp.get("country_name"),
                comp.get("match_updated"),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def list_competitions() -> list[dict[str, Any]]:
    conn = connect()
    try:
        rows = conn.execute(
            """SELECT c.competition_id, c.season_id, c.name, c.season_name, c.country,
                      c.match_count, (MAX(m.has_360)) AS has_360
               FROM competitions c
               LEFT JOIN matches m ON m.competition_id = c.competition_id
                                  AND m.season_id = c.season_id
               GROUP BY c.competition_id, c.season_id
               ORDER BY c.season_name DESC"""
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


# ---------------------------------------------------------------- matches

def upsert_match(match: dict[str, Any]) -> None:
    conn = connect()
    try:
        conn.execute(
            """INSERT INTO matches
               (match_id, competition_id, season_id, home_team, away_team,
                home_team_id, away_team_id, home_score, away_score, match_date)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(match_id) DO UPDATE SET
                 home_team=excluded.home_team, away_team=excluded.away_team,
                 home_score=excluded.home_score, away_score=excluded.away_score,
                 match_date=excluded.match_date""",
            (
                match["match_id"],
                match.get("competition_id"),
                match.get("season_id"),
                match.get("home_team", {}).get("home_team_name"),
                match.get("away_team", {}).get("away_team_name"),
                match.get("home_team", {}).get("home_team_id"),
                match.get("away_team", {}).get("away_team_id"),
                match.get("home_score"),
                match.get("away_score"),
                match.get("match_date"),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def set_match_has_360(match_id: int, has_360: bool) -> None:
    conn = connect()
    try:
        conn.execute(
            "UPDATE matches SET has_360 = ? WHERE match_id = ?",
            (1 if has_360 else 0, match_id),
        )
        conn.commit()
    finally:
        conn.close()


def set_match_status(match_id: int, status: str) -> None:
    conn = connect()
    try:
        conn.execute(
            "UPDATE matches SET status = ? WHERE match_id = ?", (status, match_id)
        )
        conn.commit()
    finally:
        conn.close()


def get_match(match_id: int) -> Optional[dict[str, Any]]:
    conn = connect()
    try:
        row = conn.execute(
            "SELECT * FROM matches WHERE match_id = ?", (match_id,)
        ).fetchone()
        return _row_to_dict(row) if row else None
    finally:
        conn.close()


def list_matches(competition_id: int) -> list[dict[str, Any]]:
    conn = connect()
    try:
        rows = conn.execute(
            "SELECT * FROM matches WHERE competition_id = ? ORDER BY match_date",
            (competition_id,),
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def list_pending_matches(force: bool = False) -> list[dict[str, Any]]:
    conn = connect()
    try:
        if force:
            rows = conn.execute("SELECT * FROM matches ORDER BY match_id").fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM matches WHERE status != 'done' ORDER BY match_id"
            ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


# ---------------------------------------------------------------- summaries

def save_summary(match_id: int, summary: dict[str, Any]) -> None:
    conn = connect()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO match_summaries (match_id, summary_json) VALUES (?, ?)",
            (match_id, json.dumps(summary, ensure_ascii=False)),
        )
        conn.commit()
    finally:
        conn.close()


def get_summary(match_id: int) -> Optional[dict[str, Any]]:
    conn = connect()
    try:
        row = conn.execute(
            "SELECT summary_json FROM match_summaries WHERE match_id = ?", (match_id,)
        ).fetchone()
        return json.loads(row["summary_json"]) if row else None
    finally:
        conn.close()


# ---------------------------------------------------------------- highlights

def replace_highlights(match_id: int, highlights: list[dict[str, Any]]) -> None:
    conn = connect()
    try:
        conn.execute("DELETE FROM highlights WHERE match_id = ?", (match_id,))
        for hl in highlights:
            conn.execute(
                """INSERT OR REPLACE INTO highlights
                   (id, match_id, team_id, team_name, type, minute, second, xg,
                    start_event, end_event, event_index)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    hl["id"],
                    match_id,
                    hl.get("team_id"),
                    hl.get("team_name"),
                    hl.get("type"),
                    hl.get("minute"),
                    hl.get("second"),
                    hl.get("xg"),
                    hl.get("start_event"),
                    hl.get("end_event"),
                    hl.get("event_index"),
                ),
            )
        conn.commit()
    finally:
        conn.close()


def list_highlights(match_id: int) -> list[dict[str, Any]]:
    conn = connect()
    try:
        rows = conn.execute(
            "SELECT * FROM highlights WHERE match_id = ? ORDER BY minute, second",
            (match_id,),
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def save_frames(highlight_id: str, match_id: int, frames: dict[str, Any]) -> None:
    conn = connect()
    try:
        conn.execute(
            """INSERT OR REPLACE INTO highlight_frames
               (id, match_id, frames_json, players_json, has_360)
               VALUES (?, ?, ?, ?, ?)""",
            (
                highlight_id,
                match_id,
                json.dumps(frames.get("frames", []), ensure_ascii=False),
                json.dumps(frames.get("players", []), ensure_ascii=False),
                1 if frames.get("has_360") else 0,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_frames(highlight_id: str) -> Optional[dict[str, Any]]:
    conn = connect()
    try:
        row = conn.execute(
            "SELECT * FROM highlight_frames WHERE id = ?", (highlight_id,)
        ).fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "match_id": row["match_id"],
            "has_360": bool(row["has_360"]),
            "players": json.loads(row["players_json"]),
            "frames": json.loads(row["frames_json"]),
        }
    finally:
        conn.close()


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}