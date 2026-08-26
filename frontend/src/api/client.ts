/**
 * FastAPI 백엔드 REST API 통신 클라이언트 모듈.
 */

import {
  Competition,
  Highlight,
  HighlightFramesData,
  Match,
  MatchSummary,
} from "../types";

const BASE_URL = "/api";

async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) {
    const errorBody = await res.text().catch(() => "");
    throw new Error(`API 요청 실패 [${res.status}]: ${url} - ${errorBody}`);
  }
  return res.json() as Promise<T>;
}

export async function fetchCompetitions(): Promise<Competition[]> {
  return fetchJson<Competition[]>(`${BASE_URL}/competitions`);
}

export async function fetchMatches(
  competitionId: number,
  seasonId: number
): Promise<Match[]> {
  return fetchJson<Match[]>(
    `${BASE_URL}/competitions/${competitionId}/matches?season_id=${seasonId}`
  );
}

export async function fetchMatch(matchId: number): Promise<Match> {
  return fetchJson<Match>(`${BASE_URL}/matches/${matchId}`);
}

export async function fetchMatchSummary(matchId: number): Promise<MatchSummary> {
  return fetchJson<MatchSummary>(`${BASE_URL}/matches/${matchId}/summary`);
}

export async function fetchHighlights(matchId: number): Promise<Highlight[]> {
  return fetchJson<Highlight[]>(`${BASE_URL}/matches/${matchId}/highlights`);
}

export async function fetchHighlightFrames(
  highlightId: number
): Promise<HighlightFramesData> {
  return fetchJson<HighlightFramesData>(
    `${BASE_URL}/highlights/${highlightId}/frames`
  );
}
