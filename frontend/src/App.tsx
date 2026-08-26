import React, { useEffect, useState } from "react";
import {
  Competition,
  Highlight,
  Match,
  MatchSummary,
  ViewMode,
} from "./types";
import {
  fetchCompetitions,
  fetchHighlights,
  fetchMatches,
  fetchMatchSummary,
} from "./api/client";
import { Header } from "./components/Header";
import { MatchView } from "./components/MatchView";
import { HighlightView } from "./components/HighlightView";
import { AlertCircle, Loader2 } from "lucide-react";

export const App: React.FC = () => {
  // 메타데이터 상태
  const [competitions, setCompetitions] = useState<Competition[]>([]);
  const [selectedCompId, setSelectedCompId] = useState<number | null>(null);
  const [selectedSeasonId, setSelectedSeasonId] = useState<number | null>(null);

  const [matches, setMatches] = useState<Match[]>([]);
  const [selectedMatchId, setSelectedMatchId] = useState<number | null>(null);

  // 경기 상세 데이터 상태
  const [summary, setSummary] = useState<MatchSummary | null>(null);
  const [highlights, setHighlights] = useState<Highlight[]>([]);

  // UI 상태
  const [viewMode, setViewMode] = useState<ViewMode>("tactics");
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isMatchLoading, setIsMatchLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // 1. 초기 대회 목록 로드
  useEffect(() => {
    fetchCompetitions()
      .then((comps) => {
        setCompetitions(comps);
        if (comps.length > 0) {
          const initialComp = comps.find((c) => c.has_360) || comps[0];
          setSelectedCompId(initialComp.competition_id);
          setSelectedSeasonId(initialComp.season_id);
        }
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "대회 목록 로드 실패");
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, []);

  // 2. 대회/시즌 변경 시 경기 목록 로드
  useEffect(() => {
    if (selectedCompId === null || selectedSeasonId === null) return;

    setIsLoading(true);
    fetchMatches(selectedCompId, selectedSeasonId)
      .then((mList) => {
        setMatches(mList);
        if (mList.length > 0) {
          const initialMatch = mList.find((m) => m.has_360) || mList[0];
          setSelectedMatchId(initialMatch.match_id);
        } else {
          setSelectedMatchId(null);
          setSummary(null);
          setHighlights([]);
        }
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "경기 목록 로드 실패");
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, [selectedCompId, selectedSeasonId]);

  // 3. 경기 선택 시 전술 요약 & 하이라이트 병렬 로드
  useEffect(() => {
    if (selectedMatchId === null) return;

    setIsMatchLoading(true);
    setError(null);

    Promise.all([
      fetchMatchSummary(selectedMatchId).catch((err) => {
        console.warn("전술 요약 데이터 로드 실패:", err);
        return null;
      }),
      fetchHighlights(selectedMatchId).catch((err) => {
        console.warn("하이라이트 데이터 로드 실패:", err);
        return [];
      }),
    ])
      .then(([summaryData, highlightList]) => {
        setSummary(summaryData);
        setHighlights(highlightList);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "경기 데이터 로드 실패");
      })
      .finally(() => {
        setIsMatchLoading(false);
      });
  }, [selectedMatchId]);

  const selectedMatch = matches.find((m) => m.match_id === selectedMatchId);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* 글로벌 네비게이션 헤더 */}
      <Header
        competitions={competitions}
        selectedCompId={selectedCompId}
        onSelectCompetition={(compId, seasonId) => {
          setSelectedCompId(compId);
          setSelectedSeasonId(seasonId);
        }}
        matches={matches}
        selectedMatchId={selectedMatchId}
        onSelectMatch={(mId) => setSelectedMatchId(mId)}
        viewMode={viewMode}
        onViewModeChange={(m) => setViewMode(m)}
        has360={selectedMatch?.has_360}
      />

      {/* 메인 본문 콘텐츠 */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-6">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center h-96 space-y-3">
            <Loader2 className="w-8 h-8 text-emerald-500 animate-spin" />
            <div className="text-sm text-slate-400">데이터를 불러오는 중입니다...</div>
          </div>
        ) : error ? (
          <div className="bg-rose-950/40 border border-rose-800/80 rounded-2xl p-8 text-center space-y-2">
            <AlertCircle className="w-8 h-8 text-rose-400 mx-auto" />
            <div className="text-base font-bold text-rose-200">데이터 요청 오류</div>
            <p className="text-xs text-rose-400">{error}</p>
          </div>
        ) : !selectedMatch ? (
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center text-slate-400">
            조회할 수 있는 경기가 없습니다. 상단에서 다른 대회를 선택해주세요.
          </div>
        ) : isMatchLoading ? (
          <div className="flex flex-col items-center justify-center h-96 space-y-3">
            <Loader2 className="w-8 h-8 text-emerald-500 animate-spin" />
            <div className="text-sm text-slate-400">경기 분석 데이터를 분석 중입니다...</div>
          </div>
        ) : (
          <div>
            {viewMode === "tactics" && (
              <>
                {summary ? (
                  <MatchView match={selectedMatch} summary={summary} />
                ) : (
                  <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center text-slate-400 space-y-2">
                    <AlertCircle className="w-8 h-8 mx-auto text-amber-400" />
                    <div className="text-white font-bold">전술 분석 요약 데이터가 없습니다</div>
                    <p className="text-xs text-slate-400">
                      CLI 명령어 `uv run python -m app.cli process`를 실행하여 경기를 먼저 가공해주세요.
                    </p>
                  </div>
                )}
              </>
            )}

            {viewMode === "highlights" && (
              <HighlightView matchId={selectedMatch.match_id} highlights={highlights} />
            )}
          </div>
        )}
      </main>

      {/* 푸터 */}
      <footer className="border-t border-slate-900 bg-slate-950/80 px-6 py-4 text-center text-xs text-slate-500">
        Football Tactical 360 &copy; 2026. Powered by StatsBomb Open Data & Three-Sixty Events.
      </footer>
    </div>
  );
};
