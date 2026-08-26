import React, { useState } from "react";
import { Match, MatchSummary, TacticalTab } from "../types";
import { TacticalBoard } from "./TacticalBoard";
import { StatCard } from "./StatCard";
import {
  Compass,
  Grid,
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
  const [activeTab, setActiveTab] = useState<TacticalTab>("formation");

  const currentTeam = summary.teams[String(selectedTeamId)] || Object.values(summary.teams)[0];

  if (!currentTeam) {
    return (
      <div className="p-8 text-center text-slate-400">
        전술 분석 요약 데이터를 불러올 수 없습니다.
      </div>
    );
  }

  const { formation, zones, passes, pressure, buildup, transitions } = currentTeam;
  const formationPlayers = formation?.players || formation?.players_overall || [];
  const formationName = formation?.formation_name || formation?.formation || "포메이션 정보 없음";

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
              activeTab === "formation"
                ? "bg-emerald-600 text-white"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <Compass className="w-3.5 h-3.5" />
            <span>포메이션</span>
          </button>
          <button
            onClick={() => setActiveTab("zones")}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              activeTab === "zones"
                ? "bg-emerald-600 text-white"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <Grid className="w-3.5 h-3.5" />
            <span>12x8 존 점유율</span>
          </button>
          <button
            onClick={() => setActiveTab("passes")}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              activeTab === "passes"
                ? "bg-emerald-600 text-white"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <Share2 className="w-3.5 h-3.5" />
            <span>패스 네트워크</span>
          </button>
          <button
            onClick={() => setActiveTab("pressure")}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              activeTab === "pressure"
                ? "bg-emerald-600 text-white"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <ShieldAlert className="w-3.5 h-3.5" />
            <span>압박 & PPDA</span>
          </button>
          <button
            onClick={() => setActiveTab("buildup")}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              activeTab === "buildup"
                ? "bg-emerald-600 text-white"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <TrendingUp className="w-3.5 h-3.5" />
            <span>빌드업 3분할</span>
          </button>
          <button
            onClick={() => setActiveTab("transitions")}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              activeTab === "transitions"
                ? "bg-emerald-600 text-white"
                : "text-slate-400 hover:text-slate-200"
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
            formationPlayers={formationPlayers}
            showZones={activeTab === "zones"}
            zones={zones?.cells}
            zoneColorTheme={selectedTeamId === homeTeamId ? "blue" : "orange"}
            showPassNetwork={activeTab === "passes"}
            passNodes={passes?.nodes}
            passEdges={passes?.edges}
          />
          <div className="text-center text-xs text-slate-500">
            * 피치 좌표계: 0 → 120 (좌측 골대 → 우측 공격 방향)
          </div>
        </div>

        {/* Tactical Info Cards (5 cols) */}
        <div className="lg:col-span-5 space-y-4">
          {activeTab === "formation" && (
            <div className="space-y-4">
              <StatCard
                title="기본 포메이션"
                value={formationName}
                subtitle={`선발 및 참여 선수: ${formationPlayers.length}명`}
                badge="실측 평균 위치"
                badgeColor="emerald"
              />
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
                <h4 className="text-xs font-bold text-slate-400 uppercase mb-3">
                  선수별 평균 참여 좌표
                </h4>
                <div className="max-h-64 overflow-y-auto space-y-2 pr-1">
                  {formationPlayers.map((p) => (
                    <div
                      key={p.player_id}
                      className="flex items-center justify-between text-xs bg-slate-950/60 p-2 rounded-lg border border-slate-800/80"
                    >
                      <div className="flex items-center space-x-2">
                        <span className="w-5 h-5 flex items-center justify-center bg-slate-800 rounded text-slate-300 font-mono">
                          {p.jersey_number ?? "-"}
                        </span>
                        <span className="font-medium text-slate-200">{p.player_name}</span>
                        {p.position_name && (
                          <span className="text-[10px] text-slate-400">({p.position_name})</span>
                        )}
                      </div>
                      <div className="font-mono text-slate-400">
                        x: {p.x.toFixed(1)}, y: {p.y.toFixed(1)}
                      </div>
                    </div>
                  ))}
                </div>
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
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
                <h4 className="text-xs font-bold text-slate-400 uppercase mb-3">
                  주요 패스 콤비네이션
                </h4>
                <div className="max-h-64 overflow-y-auto space-y-2 pr-1">
                  {passes?.edges?.map((e, idx) => {
                    const passerId = e.passer_id ?? e.source_id;
                    const recipientId = e.recipient_id ?? e.target_id;
                    const count = e.count ?? e.pass_count ?? 0;
                    const progCount = e.progressive_count ?? 0;
                    const src = passes.nodes.find((n) => n.player_id === passerId);
                    const dst = passes.nodes.find((n) => n.player_id === recipientId);
                    const srcName = src?.player_name ?? e.source_name ?? String(passerId);
                    const dstName = dst?.player_name ?? e.target_name ?? String(recipientId);
                    return (
                      <div
                        key={idx}
                        className="flex items-center justify-between text-xs bg-slate-950/60 p-2 rounded-lg border border-slate-800/80"
                      >
                        <span className="text-slate-200">
                          {srcName.split(" ").pop()} → {dstName.split(" ").pop()}
                        </span>
                        <div className="flex items-center space-x-2">
                          <span className="font-mono text-emerald-400 font-bold">
                            {count}회
                          </span>
                          {progCount > 0 && (
                            <span className="text-[10px] text-indigo-400">
                              (전진 {progCount})
                            </span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}

          {activeTab === "pressure" && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <StatCard
                  title="PPDA (수비 강도)"
                  value={pressure?.ppda !== null ? pressure.ppda.toFixed(2) : "-"}
                  subtitle="상대 패스당 수비 액션"
                  badge="상대 진영 (x>=40)"
                  badgeColor="rose"
                />
                <StatCard
                  title="분당 압박 횟수"
                  value={pressure?.pressure_per_min?.toFixed(2) || "0.0"}
                  subtitle="분당 압박 빈도"
                  badgeColor="amber"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <StatCard
                  title="하이 프레스 횟수"
                  value={`${pressure?.high_press_events || 0}회`}
                  subtitle="상대 진영 압박"
                  badgeColor="emerald"
                />
                <StatCard
                  title="공격 진영 턴오버 강요"
                  value={`${pressure?.turnovers_forced_att_third || 0}회`}
                  subtitle="파이널 써드 탈취 유도"
                  badgeColor="indigo"
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

              <div className="grid grid-cols-2 gap-3">
                <StatCard
                  title="전진 패스 비율"
                  value={`${buildup?.progressive_pass_ratio?.toFixed(1) || 0}%`}
                  subtitle="전진 기여 패스 비율"
                  badgeColor="emerald"
                />
                <StatCard
                  title="전진 캐리 비율"
                  value={`${buildup?.progressive_carry_ratio?.toFixed(1) || 0}%`}
                  subtitle="전진 기여 드리블 비율"
                  badgeColor="blue"
                />
              </div>
            </div>
          )}

          {activeTab === "transitions" && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <StatCard
                  title="볼 탈취 성공"
                  value={`${transitions?.turnovers_won || 0}회`}
                  subtitle="가로채기 및 리커버리"
                  badgeColor="emerald"
                />
                <StatCard
                  title="빠른 공격 전환 (8초 이내)"
                  value={`${transitions?.fast_transitions_to_att_third || 0}회`}
                  subtitle="파이널 써드 도달 성공"
                  badgeColor="amber"
                />
              </div>
              <StatCard
                title="평균 전환 소요 시간"
                value={
                  transitions?.avg_transition_sec !== null
                    ? `${transitions.avg_transition_sec.toFixed(2)}초`
                    : "-"
                }
                subtitle="볼 탈취 후 공격 써드 도달까지"
                badgeColor="indigo"
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
