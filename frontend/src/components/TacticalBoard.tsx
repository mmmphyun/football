import React, { useMemo, useState } from "react";
import {
  FormationPlayer,
  FramePlayer,
  PassEdge,
  PassNode,
  PassingLane,
  PhaseShape,
  PlaybookPattern,
  PressureTrap,
  TacticalPhase,
  TimelineSlice,
  ZoneCell,
} from "../types";
import {
  formatPolygonPoints,
  getZoneRect,
  PITCH_HEIGHT,
  PITCH_WIDTH,
  toSvgCoords,
} from "../lib/pitch";

export interface TacticalBoardProps {
  width?: number;
  height?: number;
  // 3대 국면 모핑 포메이션
  showFormation?: boolean;
  selectedPhase?: TacticalPhase;
  phaseShape?: PhaseShape;
  formationPlayers?: FormationPlayer[];
  // 플레이북 시그니처 패턴 화살표
  showPlaybook?: boolean;
  activePlaybookPattern?: PlaybookPattern | null;
  // 12x8 존 점유율
  zones?: ZoneCell[];
  showZones?: boolean;
  zoneColorTheme?: "blue" | "orange" | "emerald";
  // 패스 네트워크
  passNodes?: PassNode[];
  passEdges?: PassEdge[];
  showPassNetwork?: boolean;
  // 빌드업 3분할
  showBuildup?: boolean;
  buildupData?: { defPct: number; midPct: number; attPct: number };
  // 압박 & PPDA & 압박 트랩
  showPressure?: boolean;
  pressureEvents?: Array<{ x: number; y: number; type: string; is_high_press: boolean }>;
  pressureTraps?: PressureTrap[];
  ppdaValue?: number | null;
  // 전환 속도
  showTransitions?: boolean;
  transitionSequences?: Array<{
    start: [number, number];
    end: [number, number];
    sec: number;
    speed: number;
    is_fast: boolean;
    reached_final_third: boolean;
  }>;
  // 15분 전술 타임라인
  showTimeline?: boolean;
  timelineSlice?: TimelineSlice | null;
  // 하이라이트/프레임 렌더링 & 360 패스길
  players?: FramePlayer[];
  ballLocation?: [number, number];
  visibleArea?: number[];
  passingLanes?: PassingLane[];
  showPassingLanes?: boolean;
  showVisibleArea?: boolean;
  showVelocity?: boolean;
  showGhostPrediction?: boolean;
  showInferredPlayers?: boolean;
  // 이벤트 설명
  frameDescription?: string;
  minute?: number;
  second?: number;
}

const SVG_WIDTH = 1240;
const SVG_HEIGHT = 840;
const MARGIN = 20;

export const TacticalBoard: React.FC<TacticalBoardProps> = ({
  showFormation = false,
  selectedPhase = "overall",
  phaseShape,
  formationPlayers,
  showPlaybook = false,
  activePlaybookPattern,
  zones,
  showZones = false,
  zoneColorTheme = "emerald",
  passNodes,
  passEdges,
  showPassNetwork = false,
  showBuildup = false,
  buildupData,
  showPressure = false,
  pressureEvents,
  pressureTraps,
  ppdaValue,
  showTransitions = false,
  transitionSequences,
  showTimeline = false,
  timelineSlice,
  players,
  ballLocation,
  visibleArea,
  passingLanes,
  showPassingLanes = true,
  showVisibleArea = true,
  showVelocity = true,
  showGhostPrediction = true,
  showInferredPlayers = true,
  frameDescription,
  minute,
  second,
}) => {
  // SVG 좌표 변환 헬퍼
  const toSvg = (x: number, y: number) =>
    toSvgCoords(x, y, SVG_WIDTH, SVG_HEIGHT, MARGIN);

  // 피치 라인 계산
  const [pitchX, pitchY] = toSvg(0, 0);
  const [pitchX2, pitchY2] = toSvg(PITCH_WIDTH, PITCH_HEIGHT);
  const pitchW = pitchX2 - pitchX;
  const pitchH = pitchY2 - pitchY;

  const [halfX] = toSvg(60, 0);
  const [centerSpotX, centerSpotY] = toSvg(60, 40);

  // 패스 네트워크 노드 맵
  const nodeMap = useMemo(() => {
    const map = new Map<number, PassNode>();
    if (passNodes) {
      passNodes.forEach((n) => map.set(n.player_id, n));
    }
    return map;
  }, [passNodes]);

  // 존 점유율 최대치 및 호버 인터랙션
  const maxZoneRatio = useMemo(() => {
    if (!zones || zones.length === 0) return 0.025;
    return Math.max(...zones.map((c) => c.ratio), 0.001);
  }, [zones]);

  const [hoveredZone, setHoveredZone] = useState<{
    zone_x: number;
    zone_y: number;
    count: number;
    ratio: number;
    x: number;
    y: number;
  } | null>(null);

  // 존 컬러 테마
  const getZoneFill = (ratio: number) => {
    const intensity = Math.min(1.0, ratio / maxZoneRatio);
    const opacity = Math.max(0.04, intensity * 0.75);
    if (zoneColorTheme === "blue") return `rgba(59, 130, 246, ${opacity})`;
    if (zoneColorTheme === "orange") return `rgba(249, 115, 22, ${opacity})`;
    return `rgba(16, 185, 129, ${opacity})`;
  };

  // 필터링된 선수 목록 (22명 추론 토글 적용)
  const renderPlayers = useMemo(() => {
    if (!players) return [];
    if (showInferredPlayers) return players;
    return players.filter((p) => !p.is_inferred);
  }, [players, showInferredPlayers]);

  // 포메이션 모핑 대상 선수 목록
  const activeFormationPlayers = useMemo(() => {
    if (phaseShape?.players && phaseShape.players.length > 0) {
      return phaseShape.players;
    }
    return formationPlayers || [];
  }, [phaseShape, formationPlayers]);

  return (
    <div className="relative w-full aspect-[124/84] max-w-5xl mx-auto bg-slate-950 rounded-2xl overflow-hidden border border-slate-800 shadow-2xl select-none">
      <svg
        viewBox={`0 0 ${SVG_WIDTH} ${SVG_HEIGHT}`}
        className="w-full h-full"
        preserveAspectRatio="xMidYMid meet"
      >
        <defs>
          {/* 패스 네트워크 화살표 마커 */}
          <marker
            id="pass-arrow"
            viewBox="0 0 10 10"
            refX="8"
            refY="5"
            markerWidth="6"
            markerHeight="6"
            orient="auto-start-reverse"
          >
            <path d="M 0 1 L 10 5 L 0 9 z" fill="#38bdf8" />
          </marker>

          {/* 플레이북 공격 전개 화살표 마커 */}
          <marker
            id="playbook-pass-arrow"
            viewBox="0 0 10 10"
            refX="8"
            refY="5"
            markerWidth="6"
            markerHeight="6"
            orient="auto-start-reverse"
          >
            <path d="M 0 1 L 10 5 L 0 9 z" fill="#38bdf8" />
          </marker>
          <marker
            id="playbook-carry-arrow"
            viewBox="0 0 10 10"
            refX="8"
            refY="5"
            markerWidth="6"
            markerHeight="6"
            orient="auto-start-reverse"
          >
            <path d="M 0 1 L 10 5 L 0 9 z" fill="#a855f7" />
          </marker>
          <marker
            id="playbook-shot-arrow"
            viewBox="0 0 10 10"
            refX="8"
            refY="5"
            markerWidth="7"
            markerHeight="7"
            orient="auto-start-reverse"
          >
            <path d="M 0 0 L 10 5 L 0 10 z" fill="#facc15" />
          </marker>

          {/* 속도 벡터 화살표 마커 */}
          <marker
            id="velocity-arrow"
            viewBox="0 0 10 10"
            refX="7"
            refY="5"
            markerWidth="5"
            markerHeight="5"
            orient="auto"
          >
            <path d="M 0 1 L 10 5 L 0 9 z" fill="#fbbf24" />
          </marker>

          {/* 외삽 고스트 화살표 마커 */}
          <marker
            id="ghost-arrow"
            viewBox="0 0 10 10"
            refX="7"
            refY="5"
            markerWidth="5"
            markerHeight="5"
            orient="auto"
          >
            <path d="M 0 1 L 10 5 L 0 9 z" fill="#a855f7" />
          </marker>

          {/* 360 패스길 화살표 마커 */}
          <marker
            id="open-lane-arrow"
            viewBox="0 0 10 10"
            refX="8"
            refY="5"
            markerWidth="5"
            markerHeight="5"
            orient="auto-start-reverse"
          >
            <path d="M 0 1 L 10 5 L 0 9 z" fill="#22c55e" />
          </marker>
          <marker
            id="blocked-lane-arrow"
            viewBox="0 0 10 10"
            refX="8"
            refY="5"
            markerWidth="5"
            markerHeight="5"
            orient="auto-start-reverse"
          >
            <path d="M 0 1 L 10 5 L 0 9 z" fill="#ef4444" />
          </marker>
          <marker
            id="selected-lane-arrow"
            viewBox="0 0 10 10"
            refX="8"
            refY="5"
            markerWidth="6"
            markerHeight="6"
            orient="auto-start-reverse"
          >
            <path d="M 0 1 L 10 5 L 0 9 z" fill="#eab308" />
          </marker>
        </defs>

        {/* 1. 피치 잔디 베이스 */}
        <rect
          x={pitchX}
          y={pitchY}
          width={pitchW}
          height={pitchH}
          fill="#142618"
          stroke="#335c39"
          strokeWidth="3"
          rx="6"
        />

        {/* 잔디 스트라이프 패턴 (가로 12칸) */}
        {Array.from({ length: 12 }).map((_, i) => {
          if (i % 2 !== 0) return null;
          const [sx] = toSvg(i * 10, 0);
          const [sx2] = toSvg((i + 1) * 10, 0);
          return (
            <rect
              key={`stripe-${i}`}
              x={sx}
              y={pitchY}
              width={sx2 - sx}
              height={pitchH}
              fill="rgba(255, 255, 255, 0.015)"
            />
          );
        })}

        {/* 2. 12x8 존 점유율 히트맵 오버레이 */}
        {showZones &&
          zones &&
          zones.map((cell) => {
            const rect = getZoneRect(
              cell.zone_x,
              cell.zone_y,
              SVG_WIDTH,
              SVG_HEIGHT,
              MARGIN
            );
            const intensity = cell.ratio / maxZoneRatio;
            const isTopZone = intensity >= 0.65;
            const isHovered =
              hoveredZone?.zone_x === cell.zone_x &&
              hoveredZone?.zone_y === cell.zone_y;

            return (
              <g
                key={`zone-${cell.zone_x}-${cell.zone_y}`}
                className="cursor-pointer"
                onMouseEnter={() =>
                  setHoveredZone({
                    zone_x: cell.zone_x,
                    zone_y: cell.zone_y,
                    count: cell.count,
                    ratio: cell.ratio,
                    x: rect.x + rect.width / 2,
                    y: rect.y + rect.height / 2,
                  })
                }
                onMouseLeave={() => setHoveredZone(null)}
              >
                <rect
                  x={rect.x}
                  y={rect.y}
                  width={rect.width}
                  height={rect.height}
                  fill={getZoneFill(cell.ratio)}
                  stroke={
                    isHovered
                      ? "#ffffff"
                      : isTopZone
                      ? "rgba(255, 255, 255, 0.25)"
                      : "rgba(255, 255, 255, 0.05)"
                  }
                  strokeWidth={isHovered ? "2" : "1"}
                />
                {isTopZone && (
                  <text
                    x={rect.x + rect.width / 2}
                    y={rect.y + rect.height / 2 + 4}
                    fill="rgba(255, 255, 255, 0.9)"
                    fontSize="12"
                    fontWeight="bold"
                    fontFamily="monospace"
                    textAnchor="middle"
                  >
                    {(cell.ratio * 100).toFixed(1)}%
                  </text>
                )}
              </g>
            );
          })}

        {/* 2-1. 빌드업 3분할 써드 (0~40, 40~80, 80~120) 오버레이 */}
        {showBuildup && (
          <g>
            {/* 수비 써드 (0~40m) */}
            {(() => {
              const [x1] = toSvg(0, 0);
              const [x2] = toSvg(40, 0);
              const w = x2 - x1;
              return (
                <g>
                  <rect
                    x={x1}
                    y={pitchY}
                    width={w}
                    height={pitchH}
                    fill="rgba(59, 130, 246, 0.12)"
                    stroke="rgba(59, 130, 246, 0.4)"
                    strokeDasharray="4 4"
                    strokeWidth="1.5"
                  />
                  <text
                    x={x1 + w / 2}
                    y={pitchY + 40}
                    fill="#93c5fd"
                    fontSize="16"
                    fontWeight="bold"
                    textAnchor="middle"
                  >
                    수비 써드 (0~40m)
                  </text>
                  <text
                    x={x1 + w / 2}
                    y={pitchY + pitchH / 2}
                    fill="#ffffff"
                    fontSize="28"
                    fontWeight="black"
                    fontFamily="monospace"
                    textAnchor="middle"
                  >
                    {buildupData?.defPct?.toFixed(1) ?? "0.0"}%
                  </text>
                </g>
              );
            })()}

            {/* 미들 써드 (40~80m) */}
            {(() => {
              const [x1] = toSvg(40, 0);
              const [x2] = toSvg(80, 0);
              const w = x2 - x1;
              return (
                <g>
                  <rect
                    x={x1}
                    y={pitchY}
                    width={w}
                    height={pitchH}
                    fill="rgba(16, 185, 129, 0.12)"
                    stroke="rgba(16, 185, 129, 0.4)"
                    strokeDasharray="4 4"
                    strokeWidth="1.5"
                  />
                  <text
                    x={x1 + w / 2}
                    y={pitchY + 40}
                    fill="#6ee7b7"
                    fontSize="16"
                    fontWeight="bold"
                    textAnchor="middle"
                  >
                    미들 써드 (40~80m)
                  </text>
                  <text
                    x={x1 + w / 2}
                    y={pitchY + pitchH / 2}
                    fill="#ffffff"
                    fontSize="28"
                    fontWeight="black"
                    fontFamily="monospace"
                    textAnchor="middle"
                  >
                    {buildupData?.midPct?.toFixed(1) ?? "0.0"}%
                  </text>
                </g>
              );
            })()}

            {/* 공격 써드 (80~120m) */}
            {(() => {
              const [x1] = toSvg(80, 0);
              const [x2] = toSvg(120, 0);
              const w = x2 - x1;
              return (
                <g>
                  <rect
                    x={x1}
                    y={pitchY}
                    width={w}
                    height={pitchH}
                    fill="rgba(245, 158, 11, 0.12)"
                    stroke="rgba(245, 158, 11, 0.4)"
                    strokeDasharray="4 4"
                    strokeWidth="1.5"
                  />
                  <text
                    x={x1 + w / 2}
                    y={pitchY + 40}
                    fill="#fde68a"
                    fontSize="16"
                    fontWeight="bold"
                    textAnchor="middle"
                  >
                    공격 써드 (80~120m)
                  </text>
                  <text
                    x={x1 + w / 2}
                    y={pitchY + pitchH / 2}
                    fill="#ffffff"
                    fontSize="28"
                    fontWeight="black"
                    fontFamily="monospace"
                    textAnchor="middle"
                  >
                    {buildupData?.attPct?.toFixed(1) ?? "0.0"}%
                  </text>
                </g>
              );
            })()}
          </g>
        )}

        {/* 2-2. 압박 & PPDA & 압박 트랩 오버레이 */}
        {showPressure && (
          <g>
            {/* PPDA 하이프레스 구역 (x >= 40m) 음영 */}
            {(() => {
              const [x1] = toSvg(40, 0);
              const [x2] = toSvg(120, 0);
              const w = x2 - x1;
              return (
                <g>
                  <rect
                    x={x1}
                    y={pitchY}
                    width={w}
                    height={pitchH}
                    fill="rgba(239, 68, 68, 0.08)"
                    stroke="rgba(239, 68, 68, 0.5)"
                    strokeDasharray="6 4"
                    strokeWidth="2"
                  />
                  <line
                    x1={x1}
                    y1={pitchY}
                    x2={x1}
                    y2={pitchY2}
                    stroke="#ef4444"
                    strokeWidth="2.5"
                    strokeDasharray="8 4"
                  />
                  <text
                    x={x1 + 10}
                    y={pitchY + 25}
                    fill="#fca5a5"
                    fontSize="13"
                    fontWeight="bold"
                  >
                    PPDA 하이프레스 기준선 (x ≥ 40m)
                  </text>
                  {ppdaValue !== undefined && ppdaValue !== null && (
                    <text
                      x={x1 + w / 2}
                      y={pitchY + 40}
                      fill="#ef4444"
                      fontSize="18"
                      fontWeight="black"
                      fontFamily="monospace"
                      textAnchor="middle"
                    >
                      PPDA: {ppdaValue.toFixed(2)}
                    </text>
                  )}
                </g>
              );
            })()}

            {/* 압박 트랩 핫스팟 렌더링 */}
            {pressureTraps &&
              pressureTraps.map((trap, idx) => {
                const [tx, ty] = toSvg(trap.x, trap.y);
                return (
                  <g key={`pressure-trap-${idx}`} className="animate-pulse">
                    <circle
                      cx={tx}
                      cy={ty}
                      r="36"
                      fill="rgba(239, 68, 68, 0.22)"
                      stroke="#ef4444"
                      strokeWidth="2.5"
                      strokeDasharray="6 3"
                    />
                    <circle
                      cx={tx}
                      cy={ty}
                      r="14"
                      fill="#dc2626"
                      stroke="#ffffff"
                      strokeWidth="2.5"
                      className="drop-shadow-lg"
                    />
                    <rect
                      x={tx - 70}
                      y={ty - 44}
                      width="140"
                      height="24"
                      rx="6"
                      fill="rgba(15, 23, 42, 0.9)"
                      stroke="#ef4444"
                      strokeWidth="1.5"
                    />
                    <text
                      x={tx}
                      y={ty - 28}
                      fill="#fca5a5"
                      fontSize="13"
                      fontWeight="bold"
                      textAnchor="middle"
                    >
                      {trap.zone} ({trap.count}회)
                    </text>
                  </g>
                );
              })}

            {/* 개별 압박 마커 (환공포증 완화: 은은한 배경 점으로 렌더링) */}
            {pressureEvents &&
              pressureEvents.map((pe, idx) => {
                const [sx, sy] = toSvg(pe.x, pe.y);
                const color = pe.is_high_press ? "#ef4444" : "#f59e0b";
                return (
                  <g key={`pressure-ev-${idx}`}>
                    <circle
                      cx={sx}
                      cy={sy}
                      r={pe.is_high_press ? 3.5 : 2.5}
                      fill={color}
                      fillOpacity={pe.is_high_press ? 0.45 : 0.25}
                    />
                  </g>
                );
              })}

            {/* 압박 탭 범례 (우측 상단) */}
            <g transform={`translate(${SVG_WIDTH - 280}, ${pitchY + 15})`}>
              <rect
                width="260"
                height="80"
                rx="8"
                fill="rgba(15, 23, 42, 0.92)"
                stroke="#334155"
                strokeWidth="1.5"
              />
              <circle cx="20" cy="22" r="7" fill="#ef4444" stroke="#ffffff" strokeWidth="1.5" />
              <text x="35" y="26" fill="#fca5a5" fontSize="12" fontWeight="bold">
                압박 트랩 핫스팟 (2인+ 탈취)
              </text>
              <circle cx="20" cy="45" r="4" fill="#ef4444" fillOpacity="0.8" />
              <text x="35" y="49" fill="#f87171" fontSize="11">
                하이프레스 이벤트 (x ≥ 40m)
              </text>
              <circle cx="20" cy="65" r="3" fill="#f59e0b" fillOpacity="0.6" />
              <text x="35" y="69" fill="#fcd34d" fontSize="11">
                일반 압박 시도
              </text>
            </g>
          </g>
        )}

        {/* 2-3. 전환 속도 오버레이 */}
        {showTransitions && (
          <g>
            {transitionSequences &&
              transitionSequences.map((seq, idx) => {
                const [sx, sy] = toSvg(seq.start[0], seq.start[1]);
                const [ex, ey] = toSvg(seq.end[0], seq.end[1]);
                const color = seq.is_fast ? "#ec4899" : "#06b6d4";
                return (
                  <g key={`trans-seq-${idx}`}>
                    <circle cx={sx} cy={sy} r="7" fill={color} stroke="#ffffff" strokeWidth="2" />
                    <line
                      x1={sx}
                      y1={sy}
                      x2={ex}
                      y2={ey}
                      stroke={color}
                      strokeWidth={seq.is_fast ? "3.5" : "2.5"}
                      strokeOpacity="0.85"
                    />
                    <circle cx={ex} cy={ey} r="4" fill={color} fillOpacity="0.8" />
                  </g>
                );
              })}

            {/* 전환 속도 범례 (우측 상단) */}
            <g transform={`translate(${SVG_WIDTH - 300}, ${pitchY + 15})`}>
              <rect
                width="280"
                height="80"
                rx="8"
                fill="rgba(15, 23, 42, 0.92)"
                stroke="#334155"
                strokeWidth="1.5"
              />
              <circle cx="20" cy="22" r="6" fill="#ec4899" stroke="#ffffff" strokeWidth="1.5" />
              <line x1="30" y1="22" x2="60" y2="22" stroke="#ec4899" strokeWidth="3" />
              <text x="70" y="26" fill="#f472b6" fontSize="12" fontWeight="bold">
                고속 역습 (속도 &gt; 5.0m/s, 박스 진입)
              </text>
              <circle cx="20" cy="48" r="5" fill="#06b6d4" stroke="#ffffff" strokeWidth="1.5" />
              <line x1="30" y1="48" x2="60" y2="48" stroke="#06b6d4" strokeWidth="2.5" />
              <text x="70" y="52" fill="#67e8f9" fontSize="12" fontWeight="bold">
                지공 전환 (안정적 템포 전개)
              </text>
              <text x="20" y="70" fill="#94a3b8" fontSize="10">
                * 원: 턴오버 발생 지점 | 선: 공격 전개 도달 경로
              </text>
            </g>
          </g>
        )}

        {/* 2-4. 15분 전술 타임라인 오버레이 */}
        {showTimeline && timelineSlice && (
          <g>
            {/* 수비 라인 높이 표시선 */}
            {(() => {
              const [lx] = toSvg(timelineSlice.defensive_line_height, 0);
              return (
                <g>
                  <line
                    x1={lx}
                    y1={pitchY}
                    x2={lx}
                    y2={pitchY2}
                    stroke="#38bdf8"
                    strokeWidth="3"
                    strokeDasharray="8 4"
                    style={{ transition: "all 0.5s ease" }}
                  />
                  <rect
                    x={lx + 6}
                    y={pitchY + 12}
                    width="150"
                    height="28"
                    rx="6"
                    fill="rgba(15, 23, 42, 0.92)"
                    stroke="#38bdf8"
                    strokeWidth="1.5"
                  />
                  <text
                    x={lx + 81}
                    y={pitchY + 31}
                    fill="#7dd3fc"
                    fontSize="13"
                    fontWeight="bold"
                    textAnchor="middle"
                  >
                    수비 라인: {timelineSlice.defensive_line_height.toFixed(1)}m
                  </text>
                </g>
              );
            })()}

            {/* 타임라인 구간 정보 배너 (상단 중앙) */}
            <g transform={`translate(${centerSpotX - 160}, ${pitchY + 15})`}>
              <rect
                width="320"
                height="65"
                rx="10"
                fill="rgba(15, 23, 42, 0.95)"
                stroke="#334155"
                strokeWidth="1.5"
                className="drop-shadow-xl"
              />
              <text
                x="160"
                y="25"
                fill="#ffffff"
                fontSize="14"
                fontWeight="bold"
                textAnchor="middle"
              >
                {timelineSlice.label} 전술 요약
              </text>
              <text
                x="60"
                y="48"
                fill="#34d399"
                fontSize="12"
                fontWeight="bold"
                textAnchor="middle"
              >
                점유율 {timelineSlice.possession_pct.toFixed(1)}%
              </text>
              <text
                x="160"
                y="48"
                fill="#94a3b8"
                fontSize="12"
                textAnchor="middle"
              >
                패스성공 {timelineSlice.pass_accuracy.toFixed(1)}%
              </text>
              <text
                x="260"
                y="48"
                fill="#f59e0b"
                fontSize="12"
                fontWeight="bold"
                textAnchor="middle"
              >
                압박 {timelineSlice.pressures}회
              </text>
            </g>

            {/* 타임라인 구간 선수 포메이션 마커 (최대 11명 엄수) */}
            {timelineSlice.players &&
              timelineSlice.players.slice(0, 11).map((tp) => {
                const [sx, sy] = toSvg(tp.x, tp.y);
                return (
                  <g
                    key={`timeline-player-${tp.player_id}`}
                    style={{
                      transform: `translate(${sx}px, ${sy}px)`,
                      transformBox: "fill-box",
                      transition: "transform 0.5s cubic-bezier(0.34, 1.56, 0.64, 1)",
                    }}
                  >
                    <circle
                      r="16"
                      fill="#0284c7"
                      stroke="#ffffff"
                      strokeWidth="2.5"
                      className="drop-shadow-lg"
                    />
                    <text
                      y="4"
                      fill="#ffffff"
                      fontSize="11"
                      fontWeight="bold"
                      textAnchor="middle"
                    >
                      {tp.position?.slice(0, 2) ?? "P"}
                    </text>
                    <rect
                      x="-40"
                      y="20"
                      width="80"
                      height="18"
                      rx="4"
                      fill="rgba(15, 23, 42, 0.9)"
                      stroke="#0284c7"
                      strokeWidth="1"
                    />
                    <text
                      y="33"
                      fill="#e0f2fe"
                      fontSize="10"
                      fontWeight="semibold"
                      textAnchor="middle"
                    >
                      {tp.player_name.split(" ").pop()}
                    </text>
                  </g>
                );
              })}
          </g>
        )}

        {/* 3. 피치 라인 마킹 (흰색 선) */}
        <g stroke="rgba(255, 255, 255, 0.4)" strokeWidth="2" fill="none">
          {/* 하프라인 */}
          <line x1={halfX} y1={pitchY} x2={halfX} y2={pitchY2} />

          {/* 센터서클 */}
          <circle cx={centerSpotX} cy={centerSpotY} r={9.15 * 10} />
          <circle cx={centerSpotX} cy={centerSpotY} r="3.5" fill="rgba(255, 255, 255, 0.6)" />

          {/* 페널티 박스 홈 & 어웨이 */}
          {(() => {
            const [p1x, p1y] = toSvg(0, 18);
            const [p2x, p2y] = toSvg(18, 62);
            return <rect x={p1x} y={p1y} width={p2x - p1x} height={p2y - p1y} />;
          })()}
          {(() => {
            const [p1x, p1y] = toSvg(102, 18);
            const [p2x, p2y] = toSvg(120, 62);
            return <rect x={p1x} y={p1y} width={p2x - p1x} height={p2y - p1y} />;
          })()}
        </g>

        {/* 4. 360 가시 영역 (visible_area) 다각형 */}
        {showVisibleArea && visibleArea && visibleArea.length >= 6 && (
          <polygon
            points={formatPolygonPoints(visibleArea, SVG_WIDTH, SVG_HEIGHT, MARGIN)}
            fill="rgba(99, 102, 241, 0.18)"
            stroke="rgba(129, 140, 248, 0.6)"
            strokeWidth="2"
            strokeDasharray="4 2"
          />
        )}

        {/* 4-1. 360 열린 / 차단된 패스길 레이캐스팅 렌더링 */}
        {showPassingLanes && passingLanes && (
          <g>
            {passingLanes.map((lane, idx) => {
              const [fx, fy] = toSvg(lane.from_location[0], lane.from_location[1]);
              const [tx, ty] = toSvg(lane.to_location[0], lane.to_location[1]);

              if (lane.is_selected) {
                return (
                  <g key={`lane-selected-${idx}`}>
                    <line
                      x1={fx}
                      y1={fy}
                      x2={tx}
                      y2={ty}
                      stroke="#eab308"
                      strokeWidth="3.5"
                      markerEnd="url(#selected-lane-arrow)"
                    />
                  </g>
                );
              }

              if (lane.is_open) {
                return (
                  <line
                    key={`lane-open-${idx}`}
                    x1={fx}
                    y1={fy}
                    x2={tx}
                    y2={ty}
                    stroke="#22c55e"
                    strokeWidth="2"
                    strokeOpacity="0.75"
                    markerEnd="url(#open-lane-arrow)"
                  />
                );
              }

              return (
                <line
                  key={`lane-blocked-${idx}`}
                  x1={fx}
                  y1={fy}
                  x2={tx}
                  y2={ty}
                  stroke="#ef4444"
                  strokeWidth="1.5"
                  strokeDasharray="4 3"
                  strokeOpacity="0.6"
                  markerEnd="url(#blocked-lane-arrow)"
                />
              );
            })}
          </g>
        )}

        {/* 5. 플레이북 시그니처 패턴 전개 화살표 */}
        {showPlaybook && activePlaybookPattern && (
          <g>
            {activePlaybookPattern.sequences.map((seq, sIdx) => (
              <g key={`playbook-seq-${sIdx}`}>
                {seq.map((ev, eIdx) => {
                  const [sx, sy] = toSvg(ev.start_x, ev.start_y);
                  const [ex, ey] = toSvg(ev.end_x, ev.end_y);

                  if (ev.type === "Shot") {
                    return (
                      <g key={`pb-ev-${sIdx}-${eIdx}`}>
                        <line
                          x1={sx}
                          y1={sy}
                          x2={ex}
                          y2={ey}
                          stroke="#facc15"
                          strokeWidth="4"
                          markerEnd="url(#playbook-shot-arrow)"
                        />
                        <circle cx={ex} cy={ey} r="8" fill="#facc15" stroke="#000000" strokeWidth="2" />
                      </g>
                    );
                  }

                  if (ev.type === "Carry") {
                    return (
                      <line
                        key={`pb-ev-${sIdx}-${eIdx}`}
                        x1={sx}
                        y1={sy}
                        x2={ex}
                        y2={ey}
                        stroke="#a855f7"
                        strokeWidth="2.5"
                        strokeDasharray="5 3"
                        markerEnd="url(#playbook-carry-arrow)"
                      />
                    );
                  }

                  return (
                    <line
                      key={`pb-ev-${sIdx}-${eIdx}`}
                      x1={sx}
                      y1={sy}
                      x2={ex}
                      y2={ey}
                      stroke="#38bdf8"
                      strokeWidth="3"
                      markerEnd="url(#playbook-pass-arrow)"
                    />
                  );
                })}
              </g>
            ))}
          </g>
        )}

        {/* 6. 패스 네트워크 엣지 및 노드 */}
        {showPassNetwork && (
          <g>
            {/* 패스 엣지 (화살표 연결선) */}
            {passEdges &&
              passEdges.map((edge, idx) => {
                const passerId = edge.passer_id ?? edge.source_id;
                const recipientId = edge.recipient_id ?? edge.target_id;
                if (passerId === undefined || recipientId === undefined) return null;

                const src = nodeMap.get(passerId);
                const dst = nodeMap.get(recipientId);
                if (!src || !dst) return null;

                const [x1, y1] = toSvg(src.x, src.y);
                const [x2, y2] = toSvg(dst.x, dst.y);
                const count = edge.count ?? edge.pass_count ?? 1;

                return (
                  <line
                    key={`pass-edge-${idx}`}
                    x1={x1}
                    y1={y1}
                    x2={x2}
                    y2={y2}
                    stroke="rgba(56, 189, 248, 0.7)"
                    strokeWidth={Math.max(1.8, Math.min(8, count * 0.75))}
                    markerEnd="url(#pass-arrow)"
                  />
                );
              })}

            {/* 패스 노드 (선수 원형 마커 및 이름/등번호/패스 횟수) */}
            {passNodes &&
              passNodes.map((node) => {
                const [nx, ny] = toSvg(node.x, node.y);
                const r = Math.max(14, Math.min(22, 12 + (node.pass_count ?? 0) * 0.35));
                return (
                  <g key={`pass-node-${node.player_id}`}>
                    <circle
                      cx={nx}
                      cy={ny}
                      r={r}
                      fill="#0284c7"
                      stroke="#ffffff"
                      strokeWidth="2.5"
                      className="drop-shadow-lg"
                    />
                    <text
                      x={nx}
                      y={ny + 4}
                      fill="#ffffff"
                      fontSize="12"
                      fontWeight="bold"
                      textAnchor="middle"
                    >
                      {node.jersey_number ?? (node.position ? node.position.slice(0, 2) : "P")}
                    </text>
                    <rect
                      x={nx - 45}
                      y={ny + r + 3}
                      width="90"
                      height="18"
                      rx="4"
                      fill="rgba(15, 23, 42, 0.85)"
                      stroke="#0284c7"
                      strokeWidth="1"
                    />
                    <text
                      x={nx}
                      y={ny + r + 16}
                      fill="#e0f2fe"
                      fontSize="11"
                      fontWeight="semibold"
                      textAnchor="middle"
                    >
                      {node.player_name.split(" ").pop()} ({node.pass_count ?? 0}회)
                    </text>
                  </g>
                );
              })}
          </g>
        )}

        {/* 7. 포메이션 3대 국면 동적 모핑 렌더링 (CSS 트랜지션 적용) */}
        {showFormation && (
          <g>
            {/* 수비 라인 높이 표시선 */}
            {phaseShape?.line_height !== undefined && (
              <g>
                {(() => {
                  const [lx] = toSvg(phaseShape.line_height, 0);
                  return (
                    <>
                      <line
                        x1={lx}
                        y1={pitchY}
                        x2={lx}
                        y2={pitchY2}
                        stroke="#60a5fa"
                        strokeWidth="2.5"
                        strokeDasharray="6 4"
                        style={{ transition: "all 0.6s cubic-bezier(0.34, 1.56, 0.64, 1)" }}
                      />
                      <rect
                        x={lx + 6}
                        y={pitchY + 12}
                        width="140"
                        height="26"
                        rx="6"
                        fill="rgba(15, 23, 42, 0.9)"
                        stroke="#60a5fa"
                        strokeWidth="1.5"
                      />
                      <text
                        x={lx + 76}
                        y={pitchY + 29}
                        fill="#93c5fd"
                        fontSize="13"
                        fontWeight="bold"
                        textAnchor="middle"
                      >
                        수비 라인: {phaseShape.line_height.toFixed(1)}m
                      </text>
                    </>
                  );
                })()}
              </g>
            )}

            {/* 11명 선수 토큰 (위치 모핑 애니메이션) */}
            {activeFormationPlayers.map((fp) => {
              const [sx, sy] = toSvg(fp.x, fp.y);
              const phaseColorMap: Record<string, string> = {
                buildup: "#059669",
                progression: "#0284c7",
                final_third: "#dc2626",
                attacking: "#dc2626",
                high_press: "#ea580c",
                mid_block: "#4f46e5",
                defensive: "#4f46e5",
                low_block: "#1e3a8a",
                overall: "#0284c7",
              };
              const phaseColor = phaseColorMap[selectedPhase] || "#059669";
              return (
                <g
                  key={`formation-player-${fp.player_id}`}
                  style={{
                    transform: `translate(${sx}px, ${sy}px)`,
                    transformBox: "fill-box",
                    transition: "transform 0.6s cubic-bezier(0.34, 1.56, 0.64, 1)",
                  }}
                >
                  <circle
                    r="18"
                    fill={phaseColor}
                    stroke="#ffffff"
                    strokeWidth="3"
                    className="drop-shadow-xl"
                  />
                  <text
                    y="5"
                    fill="#ffffff"
                    fontSize="13"
                    fontWeight="bold"
                    textAnchor="middle"
                  >
                    {fp.jersey_number ?? fp.position?.slice(0, 2) ?? "P"}
                  </text>
                  <rect
                    x="-45"
                    y="22"
                    width="90"
                    height="20"
                    rx="5"
                    fill="rgba(15, 23, 42, 0.9)"
                    stroke={phaseColor}
                    strokeWidth="1"
                  />
                  <text
                    y="36"
                    fill="#ffffff"
                    fontSize="12"
                    fontWeight="semibold"
                    textAnchor="middle"
                  >
                    {fp.player_name.split(" ").pop()}
                  </text>
                </g>
              );
            })}
          </g>
        )}

        {/* 8. 프레임/하이라이트 선수 토큰 */}
        {renderPlayers.map((p, idx) => {
          const [sx, sy] = toSvg(p.location[0], p.location[1]);
          const isHome = p.is_teammate;
          const isInferred = Boolean(p.is_inferred);

          // 외삽 위치 (고스트)
          const predLoc = p.pred_location;
          const hasPred = showGhostPrediction && predLoc;

          // 속도 벡터 화살표 끝점
          let velX = sx;
          let velY = sy;
          if (showVelocity && p.velocity) {
            const [vx, vy] = p.velocity;
            velX = sx + vx * 12;
            velY = sy + vy * 12;
          }

          return (
            <g key={`player-token-${p.player_id ?? idx}`}>
              {/* +2초 예측 고스트 토큰 및 점선 연결 */}
              {hasPred && (
                <g opacity="0.6">
                  {(() => {
                    const [px, py] = toSvg(predLoc![0], predLoc![1]);
                    return (
                      <>
                        <line
                          x1={sx}
                          y1={sy}
                          x2={px}
                          y2={py}
                          stroke="#c084fc"
                          strokeWidth="2"
                          strokeDasharray="3 3"
                          markerEnd="url(#ghost-arrow)"
                        />
                        <circle
                          cx={px}
                          cy={py}
                          r="12"
                          fill="transparent"
                          stroke="#c084fc"
                          strokeWidth="2"
                          strokeDasharray="2 2"
                        />
                      </>
                    );
                  })()}
                </g>
              )}

              {/* 속도 벡터 화살표 */}
              {showVelocity && p.velocity && (
                <line
                  x1={sx}
                  y1={sy}
                  x2={velX}
                  y2={velY}
                  stroke="#fbbf24"
                  strokeWidth="2.5"
                  markerEnd="url(#velocity-arrow)"
                />
              )}

              {p.is_actor && (
                <circle
                  cx={sx}
                  cy={sy}
                  r="19"
                  fill="none"
                  stroke="#facc15"
                  strokeWidth="3"
                  className="animate-pulse"
                />
              )}
              <circle
                cx={sx}
                cy={sy}
                r="13"
                fill={p.is_keeper ? "#eab308" : isHome ? "#2563eb" : "#dc2626"}
                stroke={isInferred ? "#94a3b8" : "#ffffff"}
                strokeWidth={isInferred ? 1.5 : 2}
                strokeDasharray={isInferred ? "3 2" : undefined}
                opacity={isInferred ? 0.45 : 1.0}
              />
              <text
                x={sx}
                y={sy + 4}
                fill="#ffffff"
                fontSize="10"
                fontWeight="bold"
                textAnchor="middle"
                opacity={isInferred ? 0.7 : 1.0}
              >
                {p.is_keeper ? "GK" : p.player_id ? String(p.player_id).slice(-2) : ""}
              </text>
            </g>
          );
        })}

        {/* 9. 공 토큰 */}
        {ballLocation && (
          <g>
            {(() => {
              const [bx, by] = toSvg(ballLocation[0], ballLocation[1]);
              return (
                <>
                  <circle cx={bx} cy={by} r="7" fill="#ffffff" stroke="#000000" strokeWidth="1.5" />
                  <circle cx={bx} cy={by} r="2.5" fill="#f59e0b" />
                </>
              );
            })()}
          </g>
        )}

        {/* 10. 마우스 호버 툴팁 */}
        {showZones && hoveredZone && (
          <g
            transform={`translate(${Math.min(
              SVG_WIDTH - 150,
              Math.max(70, hoveredZone.x)
            )}, ${Math.max(45, hoveredZone.y - 35)})`}
          >
            <rect
              x="-70"
              y="-28"
              width="140"
              height="36"
              rx="6"
              fill="rgba(15, 23, 42, 0.95)"
              stroke="#38bdf8"
              strokeWidth="1.5"
              className="drop-shadow-xl"
            />
            <text x="0" y="1" fill="#ffffff" fontSize="12" fontWeight="bold" textAnchor="middle">
              {(hoveredZone.ratio * 100).toFixed(2)}% ({hoveredZone.count}회)
            </text>
          </g>
        )}
      </svg>

      {/* 이벤트 오버레이 배너 */}
      {(frameDescription || minute !== undefined) && (
        <div className="absolute top-3 left-3 bg-slate-900/90 backdrop-blur border border-slate-700/80 px-3 py-1.5 rounded-lg text-xs flex items-center gap-2 shadow-lg">
          {minute !== undefined && (
            <span className="font-mono font-bold text-emerald-400">
              {String(minute).padStart(2, "0")}:{String(second ?? 0).padStart(2, "0")}
            </span>
          )}
          {frameDescription && <span className="text-slate-200">{frameDescription}</span>}
        </div>
      )}
    </div>
  );
};
