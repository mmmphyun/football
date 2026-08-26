import React from "react";
import { Competition, Match, ViewMode } from "../types";
import { Activity, Film, Trophy } from "lucide-react";

interface HeaderProps {
  competitions: Competition[];
  selectedCompId: number | null;
  onSelectCompetition: (compId: number, seasonId: number) => void;
  matches: Match[];
  selectedMatchId: number | null;
  onSelectMatch: (matchId: number) => void;
  viewMode: ViewMode;
  onViewModeChange: (mode: ViewMode) => void;
  has360?: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  competitions,
  selectedCompId,
  onSelectCompetition,
  matches,
  selectedMatchId,
  onSelectMatch,
  viewMode,
  onViewModeChange,
  has360 = false,
}) => {
  return (
    <header className="bg-slate-900 border-b border-slate-800 px-6 py-4 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center justify-between gap-4">
        {/* 로고 & 타이틀 */}
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-emerald-500/10 border border-emerald-500/30 rounded-lg text-emerald-400">
            <Activity className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
              Football Tactical 360
              {has360 && (
                <span className="px-2 py-0.5 text-xs font-semibold bg-indigo-500/20 text-indigo-400 border border-indigo-500/40 rounded-full">
                  360 Tracking
                </span>
              )}
            </h1>
            <p className="text-xs text-slate-400">StatsBomb 전술 분석 & 인터랙티브 리플레이</p>
          </div>
        </div>

        {/* 대회 및 경기 선택 셀렉터 */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center space-x-2 bg-slate-800/80 border border-slate-700 px-3 py-1.5 rounded-md">
            <Trophy className="w-4 h-4 text-amber-400" />
            <select
              className="bg-transparent text-sm text-slate-200 outline-none cursor-pointer"
              value={selectedCompId ?? ""}
              onChange={(e) => {
                const compId = Number(e.target.value);
                const comp = competitions.find((c) => c.competition_id === compId);
                if (comp) onSelectCompetition(comp.competition_id, comp.season_id);
              }}
            >
              <option value="" disabled className="bg-slate-900">
                대회 선택
              </option>
              {competitions.map((c) => (
                <option
                  key={`${c.competition_id}-${c.season_id}`}
                  value={c.competition_id}
                  className="bg-slate-900"
                >
                  {c.name} ({c.season_name || c.season_id}) {c.has_360 ? "★ 360" : ""}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center space-x-2 bg-slate-800/80 border border-slate-700 px-3 py-1.5 rounded-md">
            <select
              className="bg-transparent text-sm text-slate-200 outline-none cursor-pointer max-w-[240px] truncate"
              value={selectedMatchId ?? ""}
              onChange={(e) => onSelectMatch(Number(e.target.value))}
              disabled={matches.length === 0}
            >
              <option value="" disabled className="bg-slate-900">
                {matches.length === 0 ? "경기 없음" : "경기 선택"}
              </option>
              {matches.map((m) => (
                <option key={m.match_id} value={m.match_id} className="bg-slate-900">
                  {m.home_team} {m.home_score} - {m.away_score} {m.away_team} ({m.match_date})
                </option>
              ))}
            </select>
          </div>

          {/* 뷰 모드 탭 */}
          <div className="flex bg-slate-800 p-1 rounded-lg border border-slate-700">
            <button
              onClick={() => onViewModeChange("tactics")}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                viewMode === "tactics"
                  ? "bg-emerald-600 text-white shadow-sm"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <Activity className="w-4 h-4" />
              <span>전술 분석</span>
            </button>
            <button
              onClick={() => onViewModeChange("highlights")}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                viewMode === "highlights"
                  ? "bg-emerald-600 text-white shadow-sm"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <Film className="w-4 h-4" />
              <span>하이라이트</span>
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};
