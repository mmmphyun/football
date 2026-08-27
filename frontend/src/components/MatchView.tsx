import React, { useState } from "react";
import {
  Match,
  MatchSummary,
  PlaybookPattern,
  TacticalPhase,
  TacticalTab,
  TimelineSlice,
} from "../types";
import { TacticalBoard } from "./TacticalBoard";
import { StatCard } from "./StatCard";
import {
  Activity,
  BookOpen,
  Compass,
  Grid,
  Layers,
  Share2,
  ShieldAlert,
  TrendingUp,
  Zap,
} from "lucide-react";

interface MatchViewProps {
  match: Match;
  summary: MatchSummary;
}

export const MatchView: React.FC<MatchViewProps> = ({ match, summary }) => {
  const teamIds = summary.team_ids || [];
  const homeTeamId = teamIds[0];

  const [selectedTeamId, setSelectedTeamId] = useState<number>(
    homeTeamId ?? Number(Object.keys(summary.teams)[0])
  );
  const [selectedPhase, setSelectedPhase] = useState<TacticalPhase>("progression");
  const [activeTab, setActiveTab] = useState<TacticalTab>("formation");
  const [selectedPlaybookPattern, setSelectedPlaybookPattern] =
    useState<PlaybookPattern | null>(null);
  const [selectedTimelineSlice, setSelectedTimelineSlice] =
    useState<TimelineSlice | null>(null);

  const currentTeam = summary.teams[String(selectedTeamId)] || Object.values(summary.teams)[0];

  // 해당 경기에서 실제로 1회 이상 발생한 시그니처 공격 패턴만 필터링
  const activePlaybooks = (currentTeam?.playbook || []).filter((p) => p.occurrences > 0);

  // 팀 변경 시 플레이북 및 타임라인 슬라이스 자동 리셋/동기화
  React.useEffect(() => {
    if (activePlaybooks.length > 0) {
      setSelectedPlaybookPattern(activePlaybooks[0]);
    } else {
      setSelectedPlaybookPattern(null);
    }

    if (currentTeam?.timeline && currentTeam.timeline.length > 0) {
      setSelectedTimelineSlice(currentTeam.timeline[0]);
    } else {
      setSelectedTimelineSlice(null);
    }
  }, [selectedTeamId, currentTeam]);

  if (!currentTeam) {
    return (
      <div className="p-8 text-center text-slate-400">
        전술 분석 요약 데이터를 불러올 수 없습니다.
      </div>
    );
  }

  const { formation, zones, passes, pressure, buildup, transitions, playbook, timeline } =
    currentTeam;

  // 6대 서브 국면 데이터 추출 (subphases 우선 참조, 없을 시 기존 3대 국면 기반 보정 fallback)
  const subphases = formation?.subphases;
  const baseStarters =
    formation?.starters ||
    formation?.players?.filter((p) => p.is_starter) ||
    formation?.players?.slice(0, 11) ||
    [];

  const phaseShape =
    (subphases && subphases[selectedPhase]) ||
    (selectedPhase === "buildup"
      ? formation?.buildup
      : selectedPhase === "progression"
      ? {
          formation: "3-2-4-1",
          line_height: 48.0,
          width: 52.0,
          length: 32.0,
          players: formation?.players_in_possession?.slice(0, 11) || baseStarters,
        }
      : selectedPhase === "final_third" || selectedPhase === "attacking"
      ? formation?.attacking
      : selectedPhase === "high_press"
      ? {
          formation: "High Press",
          line_height: 55.0,
          width: 42.0,
          length: 28.0,
          players: baseStarters.map((p) => ({
            ...p,
            x: Math.min(115.0, p.x + 12.0),
            y: 40.0 + (p.y - 40.0) * 0.85,
          })),
        }
      : selectedPhase === "low_block"
      ? {
          formation: "5-4-1",
          line_height: 22.0,
          width: 38.0,
          length: 20.0,
          players: baseStarters.map((p) => ({
            ...p,
            x: Math.max(5.0, p.x - 14.0),
            y: 40.0 + (p.y - 40.0) * 0.75,
          })),
        }
      : formation?.defensive);

  const currentFormationName =
    phaseShape?.formation ||
    formation?.formation_name ||
    formation?.formation ||
    "4-3-3";

  const starters = (phaseShape?.players || baseStarters).slice(0, 11);

  const substitutes =
    formation?.substitutes ||
    formation?.players?.filter((p) => !p.is_starter && (p.event_count ?? 0) > 0) ||
    [];

  const buildupDefPct =
    buildup?.defensive_third_pct ??
    (buildup?.buildup_start_distribution
      ? buildup.buildup_start_distribution.defensive_third_ratio * 100
      : 0);
  const buildupMidPct =
    buildup?.middle_third_pct ??
    (buildup?.buildup_start_distribution
      ? buildup.buildup_start_distribution.middle_third_ratio * 100
      : 0);
  const buildupAttPct =
    buildup?.attacking_third_pct ??
    (buildup?.buildup_start_distribution
      ? buildup.buildup_start_distribution.attacking_third_ratio * 100
      : 0);

  return (
    <div className="space-y-6">
      {/* 경기 헤더 스코어보드 */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="flex items-center space-x-6">
          <div className="text-right">
            <div className="text-lg font-bold text-white">{match.home_team}</div>
            <div className="text-xs text-slate-400">Home</div>
          </div>
          <div className="text-3xl font-black text-emerald-400 bg-slate-950 px-4 py-2 rounded-xl border border-slate-800 font-mono">
            {match.home_score} : {match.away_score}
          </div>
          <div className="text-left">
            <div className="text-lg font-bold text-white">{match.away_team}</div>
            <div className="text-xs text-slate-400">Away</div>
          </div>
        </div>

        <div className="flex items-center gap-4 text-xs text-slate-400">
          <div>
            경기 시간:{" "}
            <span className="text-slate-200 font-semibold">
              {summary.match_duration_min.toFixed(0)}분
            </span>
          </div>
          <div>
            360 트래킹:{" "}
            <span
              className={`font-semibold ${
                match.has_360 ? "text-indigo-400" : "text-slate-500"
              }`}
            >
              {match.has_360 ? "지원" : "미지원"}
            </span>
          </div>
        </div>
      </div>

      {/* UEFA 6대 서브 국면 동적 포메이션 모핑 바 */}
      <div className="bg-gradient-to-r from-slate-900 via-slate-850 to-slate-900 border border-slate-700/80 rounded-2xl p-4 shadow-xl">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="flex items-center space-x-2">
            <Layers className="w-5 h-5 text-emerald-400" />
            <div>
              <div className="text-sm font-bold text-white">UEFA 6대 서브 국면 포메이션 모핑</div>
              <div className="text-xs text-slate-400">볼 소유 3단계 및 볼 미소유 수비 3단계 실시간 대형 모핑</div>
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            {/* 볼 소유 3단계 */}
            <div className="flex bg-slate-950/80 p-1 rounded-xl border border-slate-800 space-x-1">
              <span className="text-[10px] font-bold text-emerald-400 uppercase self-center px-1.5 hidden sm:inline">
                볼 소유
              </span>
              <button
                onClick={() => {
                  setSelectedPhase("buildup");
                  setActiveTab("formation");
                }}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                  selectedPhase === "buildup" && activeTab === "formation"
                    ? "bg-emerald-600 text-white shadow-lg shadow-emerald-500/20"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                1. 후방 빌드업
              </button>
              <button
                onClick={() => {
                  setSelectedPhase("progression");
                  setActiveTab("formation");
                }}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                  selectedPhase === "progression" && activeTab === "formation"
                    ? "bg-sky-600 text-white shadow-lg shadow-sky-500/20"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                2. 중원 전개
              </button>
              <button
                onClick={() => {
                  setSelectedPhase("final_third");
                  setActiveTab("formation");
                }}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                  selectedPhase === "final_third" && activeTab === "formation"
                    ? "bg-rose-600 text-white shadow-lg shadow-rose-500/20"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                3. 기회 창출
              </button>
            </div>

            {/* 볼 미소유 3단계 */}
            <div className="flex bg-slate-950/80 p-1 rounded-xl border border-slate-800 space-x-1">
              <span className="text-[10px] font-bold text-amber-400 uppercase self-center px-1.5 hidden sm:inline">
                볼 미소유
              </span>
              <button
                onClick={() => {
                  setSelectedPhase("high_press");
                  setActiveTab("formation");
                }}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                  selectedPhase === "high_press" && activeTab === "formation"
                    ? "bg-orange-600 text-white shadow-lg shadow-orange-500/20"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                4. 전방 압박
              </button>
              <button
                onClick={() => {
                  setSelectedPhase("mid_block");
                  setActiveTab("formation");
                }}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                  selectedPhase === "mid_block" && activeTab === "formation"
                    ? "bg-indigo-600 text-white shadow-lg shadow-indigo-500/20"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                5. 미들 블록
              </button>
              <button
                onClick={() => {
                  setSelectedPhase("low_block");
                  setActiveTab("formation");
                }}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                  selectedPhase === "low_block" && activeTab === "formation"
                    ? "bg-blue-900 text-white shadow-lg shadow-blue-900/40"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                6. 로우 블록
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* 팀 선택 토글 & 전술 지표 탭 */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-3">
        {/* 팀 토글 */}
        <div className="flex bg-slate-900 p-1 rounded-xl border border-slate-800">
          {teamIds.map((tId) => {
            const tData = summary.teams[String(tId)];
            const isSelected = selectedTeamId === tId;
            return (
              <button
                key={tId}
                onClick={() => setSelectedTeamId(tId)}
                className={`px-4 py-2 rounded-lg text-sm font-semibold transition-all ${
                  isSelected
                    ? "bg-slate-800 text-emerald-400 shadow"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                {tData?.team_name || `Team ${tId}`}
              </button>
            );
          })}
        </div>

        {/* 8종 전술 탭 메뉴 */}
        <div className="flex flex-wrap gap-1.5 bg-slate-900/60 p-1 rounded-xl border border-slate-800">
          <button
            onClick={() => setActiveTab("formation")}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              activeTab === "formation" ? "bg-emerald-600 text-white" : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <Compass className="w-3.5 h-3.5" />
            <span>포메이션</span>
          </button>
          <button
            onClick={() => {
              setActiveTab("playbook");
              if (playbook && playbook.length > 0) {
                setSelectedPlaybookPattern(playbook[0]);
              }
            }}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              activeTab === "playbook" ? "bg-emerald-600 text-white" : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <BookOpen className="w-3.5 h-3.5" />
            <span>시그니처 플레이북</span>
          </button>
          <button
            onClick={() => setActiveTab("pressure")}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              activeTab === "pressure" ? "bg-emerald-600 text-white" : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <ShieldAlert className="w-3.5 h-3.5" />
            <span>압박 트랩 & PPDA</span>
          </button>
          <button
            onClick={() => setActiveTab("timeline")}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              activeTab === "timeline" ? "bg-emerald-600 text-white" : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <Activity className="w-3.5 h-3.5" />
            <span>전술 타임라인</span>
          </button>
          <button
            onClick={() => setActiveTab("zones")}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              activeTab === "zones" ? "bg-emerald-600 text-white" : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <Grid className="w-3.5 h-3.5" />
            <span>12x8 존 점유율</span>
          </button>
          <button
            onClick={() => setActiveTab("passes")}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              activeTab === "passes" ? "bg-emerald-600 text-white" : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <Share2 className="w-3.5 h-3.5" />
            <span>패스 네트워크</span>
          </button>
          <button
            onClick={() => setActiveTab("buildup")}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              activeTab === "buildup" ? "bg-emerald-600 text-white" : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <TrendingUp className="w-3.5 h-3.5" />
            <span>빌드업 3분할</span>
          </button>
          <button
            onClick={() => setActiveTab("transitions")}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              activeTab === "transitions" ? "bg-emerald-600 text-white" : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <Zap className="w-3.5 h-3.5" />
            <span>전환 속도</span>
          </button>
        </div>
      </div>

      {/* 메인 콘텐츠 레이아웃: 좌측 바둑판 피치 + 우측 전술 지표 카드 */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Tactical Board (7 cols) */}
        <div className="lg:col-span-7 space-y-3">
          <TacticalBoard
            showFormation={activeTab === "formation"}
            selectedPhase={selectedPhase}
            phaseShape={phaseShape}
            formationPlayers={starters}
            showPlaybook={activeTab === "playbook"}
            activePlaybookPattern={selectedPlaybookPattern}
            showZones={activeTab === "zones"}
            zones={zones?.cells}
            zoneColorTheme={selectedTeamId === homeTeamId ? "blue" : "orange"}
            showPassNetwork={activeTab === "passes"}
            passNodes={passes?.nodes}
            passEdges={passes?.edges}
            showBuildup={activeTab === "buildup"}
            buildupData={{
              defPct: buildupDefPct,
              midPct: buildupMidPct,
              attPct: buildupAttPct,
            }}
            showPressure={activeTab === "pressure"}
            pressureEvents={pressure?.pressure_events}
            pressureTraps={pressure?.pressure_traps}
            ppdaValue={pressure?.ppda}
            showTransitions={activeTab === "transitions"}
            transitionSequences={transitions?.transition_sequences}
            showTimeline={activeTab === "timeline"}
            timelineSlice={selectedTimelineSlice}
          />
          <div className="text-center text-xs text-slate-500">
            * 피치 좌표계: 0 → 120 (좌측 골대 → 우측 공격 방향) | D3 SVG 모핑 트랜지션 적용
          </div>
        </div>

        {/* Tactical Info Cards (5 cols) */}
        <div className="lg:col-span-5 space-y-4">
          {activeTab === "formation" && (
            <div className="space-y-4">
              <StatCard
                title={`${selectedPhase === "defensive" ? "수비" : selectedPhase === "attacking" ? "공격" : "빌드업"} 국면 대형`}
                value={currentFormationName}
                subtitle={`라인 높이: ${phaseShape?.line_height?.toFixed(1) ?? "-"}m | 너비: ${phaseShape?.width?.toFixed(1) ?? "-"}m | 길이: ${phaseShape?.length?.toFixed(1) ?? "-"}m`}
                badge={`${selectedPhase.toUpperCase()} SHAPE`}
                badgeColor={selectedPhase === "defensive" ? "blue" : selectedPhase === "attacking" ? "rose" : "emerald"}
              />

              <div className="grid grid-cols-3 gap-2">
                <div className="bg-slate-900 border border-slate-800 p-3 rounded-xl text-center">
                  <div className="text-[11px] text-slate-400">수비 라인 높이</div>
                  <div className="text-lg font-bold text-white font-mono">{phaseShape?.line_height?.toFixed(1) ?? "35.0"}m</div>
                </div>
                <div className="bg-slate-900 border border-slate-800 p-3 rounded-xl text-center">
                  <div className="text-[11px] text-slate-400">대형 너비 (Spread)</div>
                  <div className="text-lg font-bold text-white font-mono">{phaseShape?.width?.toFixed(1) ?? "45.0"}m</div>
                </div>
                <div className="bg-slate-900 border border-slate-800 p-3 rounded-xl text-center">
                  <div className="text-[11px] text-slate-400">대형 길이 (Compactness)</div>
                  <div className="text-lg font-bold text-white font-mono">{phaseShape?.length?.toFixed(1) ?? "30.0"}m</div>
                </div>
              </div>

              <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
                <h4 className="text-xs font-bold text-slate-400 uppercase mb-3">
                  국면별 선수 참여 좌표 ({starters.length}명)
                </h4>
                <div className="max-h-56 overflow-y-auto space-y-2 pr-1">
                  {starters.map((p) => (
                    <div
                      key={p.player_id}
                      className="flex items-center justify-between text-xs bg-slate-950/60 p-2 rounded-lg border border-slate-800/80"
                    >
                      <div className="flex items-center space-x-2">
                        <span className="w-5 h-5 flex items-center justify-center bg-slate-800 rounded text-slate-300 font-mono">
                          {p.jersey_number ?? "-"}
                        </span>
                        <span className="font-medium text-slate-200">{p.player_name}</span>
                        {p.position && (
                          <span className="text-[10px] text-slate-400">({p.position})</span>
                        )}
                      </div>
                      <div className="font-mono text-slate-400">
                        x: {p.x.toFixed(1)}, y: {p.y.toFixed(1)}
                      </div>
                    </div>
                  ))}
                </div>

                {substitutes.length > 0 && (
                  <div className="mt-4 pt-3 border-t border-slate-800">
                    <h4 className="text-xs font-bold text-amber-400 uppercase mb-2">
                      교체 출전 선수 ({substitutes.length}명)
                    </h4>
                    <div className="space-y-1.5 max-h-36 overflow-y-auto pr-1">
                      {substitutes.map((p) => (
                        <div
                          key={p.player_id}
                          className="flex items-center justify-between text-xs bg-slate-950/40 p-1.5 rounded-lg border border-slate-800/60"
                        >
                          <div className="flex items-center space-x-2">
                            <span className="w-4 h-4 flex items-center justify-center bg-amber-500/20 text-amber-300 rounded text-[10px] font-mono">
                              {p.jersey_number ?? "-"}
                            </span>
                            <span className="text-slate-300 text-[11px]">{p.player_name}</span>
                          </div>
                          <span className="text-[10px] text-slate-500 font-mono">
                            {p.event_count ?? 0}회 관여
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {activeTab === "playbook" && (
            <div className="space-y-4">
              <StatCard
                title="시그니처 전술 플레이북"
                value={`${activePlaybooks.length}개 패턴`}
                subtitle="해당 경기에서 실제로 관측된 시그니처 공격 전개 패턴"
                badge="Active Signatures"
                badgeColor="emerald"
              />

              {activePlaybooks.length === 0 ? (
                <div className="p-8 text-center bg-slate-900 border border-slate-800 rounded-xl text-slate-400 text-xs">
                  해당 경기에서 기록된 시그니처 공격 전개 패턴이 없습니다.
                </div>
              ) : (
                <div className="space-y-3">
                  {activePlaybooks.map((pattern) => {
                    const isSelected = selectedPlaybookPattern?.pattern_id === pattern.pattern_id;
                    return (
                      <div
                        key={pattern.pattern_id}
                        onClick={() => setSelectedPlaybookPattern(pattern)}
                        className={`p-4 rounded-xl border cursor-pointer transition-all ${
                          isSelected
                            ? "bg-slate-800/90 border-emerald-500/80 shadow-lg"
                            : "bg-slate-900 border-slate-800 hover:border-slate-700"
                        }`}
                      >
                        <div className="flex items-center justify-between mb-2">
                          <div className="font-bold text-white text-sm">{pattern.name_ko}</div>
                          <div className="flex items-center space-x-2">
                            <span className="bg-emerald-500/20 text-emerald-400 text-xs px-2 py-0.5 rounded font-mono font-bold">
                              {pattern.occurrences}회 시도
                            </span>
                            <span className="bg-indigo-500/20 text-indigo-400 text-xs px-2 py-0.5 rounded font-mono">
                              xG {pattern.total_xg.toFixed(2)}
                            </span>
                          </div>
                        </div>
                        <div className="text-xs text-slate-400 leading-relaxed mb-3">
                          {pattern.description}
                        </div>
                        <div className="text-[11px] text-slate-500 font-mono">
                          시퀀스 단계: {pattern.sequences[0]?.length || 0}개 이벤트 연계
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {activeTab === "pressure" && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <StatCard
                  title="PPDA (수비 강도)"
                  value={pressure?.ppda !== null && pressure?.ppda !== undefined ? pressure.ppda.toFixed(2) : "-"}
                  subtitle="상대 패스당 수비 액션"
                  badge="상대 진영 (x>=40)"
                  badgeColor="rose"
                />
                <StatCard
                  title="분당 압박 횟수"
                  value={pressure?.pressures_per_min?.toFixed(2) || "0.0"}
                  subtitle="분당 압박 빈도"
                  badgeColor="amber"
                />
              </div>

              {pressure?.pressure_traps && pressure.pressure_traps.length > 0 && (
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
                  <h4 className="text-xs font-bold text-rose-400 uppercase">
                    압박 트랩 핫스팟 (Pressing Trap Zones)
                  </h4>
                  <div className="space-y-2">
                    {pressure.pressure_traps.map((trap, idx) => (
                      <div
                        key={idx}
                        className="flex items-center justify-between p-2 rounded-lg bg-slate-950 border border-slate-800"
                      >
                        <div className="text-xs text-slate-200 font-medium">{trap.zone}</div>
                        <div className="text-xs text-rose-400 font-mono font-bold">{trap.count}회 탈취 유도</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === "timeline" && (
            <div className="space-y-4">
              <StatCard
                title="15분 단위 전술 타임라인 슬라이스"
                value={`${timeline?.length || 0}개 구간`}
                subtitle="시간대별 점유율 및 수비 라인 변화"
                badge="15min Intervals"
                badgeColor="blue"
              />

              <div className="space-y-2 max-h-80 overflow-y-auto pr-1">
                {timeline?.map((sl) => {
                  const isSelected = selectedTimelineSlice?.slice_index === sl.slice_index;
                  return (
                    <div
                      key={sl.slice_index}
                      onClick={() => setSelectedTimelineSlice(sl)}
                      className={`p-3 rounded-xl cursor-pointer transition-all border ${
                        isSelected
                          ? "bg-slate-800/90 border-blue-500 ring-1 ring-blue-500/50 shadow-md"
                          : "bg-slate-900 border-slate-800 hover:border-slate-700"
                      }`}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-bold text-white text-xs flex items-center gap-1.5">
                          <span
                            className={`w-2 h-2 rounded-full ${
                              isSelected ? "bg-blue-400 animate-pulse" : "bg-slate-600"
                            }`}
                          />
                          {sl.label}
                        </span>
                        <span className="text-xs font-mono text-emerald-400 font-bold">
                          점유율 {sl.possession_pct.toFixed(1)}%
                        </span>
                      </div>
                      <div className="grid grid-cols-3 gap-2 text-[11px] text-slate-400">
                        <div>
                          수비 라인:{" "}
                          <span className="text-slate-200 font-mono font-semibold">
                            {sl.defensive_line_height.toFixed(1)}m
                          </span>
                        </div>
                        <div>
                          패스 성공률:{" "}
                          <span className="text-slate-200 font-mono font-semibold">
                            {sl.pass_accuracy.toFixed(1)}%
                          </span>
                        </div>
                        <div>
                          압박:{" "}
                          <span className="text-slate-200 font-mono font-semibold">
                            {sl.pressures}회
                          </span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {activeTab === "zones" && (
            <div className="space-y-4">
              <StatCard
                title="12x8 피치 점유율 분석"
                value={`${zones?.total_samples || 0}개`}
                subtitle="총 360 프레임 및 위치 샘플 수"
                badge="12×8 Grid"
                badgeColor="blue"
              />
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 text-xs text-slate-300 space-y-2">
                <div className="font-semibold text-white">존 점유율 안내</div>
                <p className="text-slate-400 leading-relaxed">
                  피치를 가로 12분할(각 10m), 세로 8분할(각 10m)하여 360 가시 영역 및 이벤트 발생 시
                  해당 팀 선수가 위치한 밀도를 집계한 결과입니다.
                </p>
              </div>
            </div>
          )}

          {activeTab === "passes" && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <StatCard
                  title="패스 노드 수"
                  value={`${passes?.nodes?.length || 0}명`}
                  subtitle="경기 참여 선수"
                  badgeColor="blue"
                />
                <StatCard
                  title="주요 패스 라인"
                  value={`${passes?.edges?.length || 0}개`}
                  subtitle="상위 연계 콤비네이션"
                  badge="Top 15"
                  badgeColor="emerald"
                />
              </div>
            </div>
          )}

          {activeTab === "buildup" && (
            <div className="space-y-4">
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
                <h4 className="text-xs font-bold text-slate-400 uppercase">
                  3분할 빌드업 시작 위치 비율
                </h4>
                <div className="space-y-2">
                  <div>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-slate-400">수비 써드 (0~40m)</span>
                      <span className="text-slate-200 font-mono font-bold">
                        {buildup?.defensive_third_pct?.toFixed(1) || 0}%
                      </span>
                    </div>
                    <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                      <div
                        className="bg-blue-500 h-full rounded-full"
                        style={{ width: `${buildup?.defensive_third_pct || 0}%` }}
                      />
                    </div>
                  </div>
                  <div>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-slate-400">미들 써드 (40~80m)</span>
                      <span className="text-slate-200 font-mono font-bold">
                        {buildup?.middle_third_pct?.toFixed(1) || 0}%
                      </span>
                    </div>
                    <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                      <div
                        className="bg-emerald-500 h-full rounded-full"
                        style={{ width: `${buildup?.middle_third_pct || 0}%` }}
                      />
                    </div>
                  </div>
                  <div>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-slate-400">공격 써드 (80~120m)</span>
                      <span className="text-slate-200 font-mono font-bold">
                        {buildup?.attacking_third_pct?.toFixed(1) || 0}%
                      </span>
                    </div>
                    <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                      <div
                        className="bg-amber-500 h-full rounded-full"
                        style={{ width: `${buildup?.attacking_third_pct || 0}%` }}
                      />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === "transitions" && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <StatCard
                  title="볼 탈취 성공"
                  value={`${transitions?.turnovers_won ?? transitions?.total_recoveries ?? 0}회`}
                  subtitle="가로채기 및 리커버리"
                  badgeColor="emerald"
                />
                <StatCard
                  title="고속 역습 전환"
                  value={`${transitions?.fast_transitions_to_att_third ?? transitions?.fast_transitions ?? 0}회`}
                  subtitle="8초 내 파이널 서드 진입"
                  badge="Fast Counter"
                  badgeColor="rose"
                />
              </div>

              <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-2 text-xs text-slate-300">
                <div className="font-bold text-white flex items-center gap-1.5">
                  <Zap className="w-4 h-4 text-pink-400" />
                  <span>공수 전환 속도 (Transitions) 분석 안내</span>
                </div>
                <p className="text-slate-400 leading-relaxed">
                  볼을 빼앗은(Turnover Won) 순간부터 슈팅이나 파이널 서드 박스 진입까지 전개된 속도와 경로를 추적합니다.
                </p>
                <div className="pt-2 border-t border-slate-800 space-y-1.5 font-mono text-[11px]">
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-pink-500" />
                    <span className="text-pink-300 font-bold">핑크색 라인</span>: 전진 속도 5.0m/s 이상 고속 역습
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-cyan-400" />
                    <span className="text-cyan-300 font-bold">청록색 라인</span>: 안정적인 템포의 지공 빌드업 전환
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
