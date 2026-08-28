"""전체 DB 경기 데이터를 최신 전술 엔진으로 일괄 재가공(Reprocess)하는 스크립트."""

import sqlite3
import sys
from pathlib import Path

# backend 경로 추가
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import DB_PATH
from app.processing import process_match


def main() -> None:
    print(f"Opening DB at: {DB_PATH}")
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    cur.execute("SELECT match_id, home_team, away_team FROM matches")
    matches = cur.fetchall()
    conn.close()

    print(f"Total matches to reprocess: {len(matches)}")
    success_count = 0

    for idx, (m_id, home, away) in enumerate(matches, 1):
        print(f"[{idx}/{len(matches)}] Reprocessing Match {m_id}: {home} vs {away}...")
        ok = process_match(m_id)
        if ok:
            success_count += 1
        else:
            print(f"  FAILED to process match {m_id}")

    print(f"\nCompleted! Successfully reprocessed {success_count}/{len(matches)} matches.")


if __name__ == "__main__":
    main()
