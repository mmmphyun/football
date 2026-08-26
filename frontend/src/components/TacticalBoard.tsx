import React, { useMemo } from "react";
import {
  FormationPlayer,
  FramePlayer,
  PassEdge,
  PassNode,
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
  // 12x8 존 점유율
  zones?: ZoneCell[];
  showZones?: boolean;
  zoneColorTheme?: "blue" | "orange" | "emerald";
  // 패스 네트워크
  passNodes?: PassNode[];
  passEdges?: PassEdge[];
  showPassNetwork?: boolean;
  // 포메이션 평균 위치
  formationPlayers?: FormationPlayer[];
  showFormation?: boolean;
  // 하이라이트/프레임 렌더링
  players?: FramePlayer[];
  ballLocation?: [number, number];
  visibleArea?: number[];
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
  zones,
  showZones = false,
  zoneColorTheme = "emerald",
  passNodes,
  passEdges,
  showPassNetwork = false,
  formationPlayers,
  showFormation = false,
  players,
  ballLocation,
  visibleArea,
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

  // 존 컬러 테마
  const getZoneFill = (ratio: number) => {
    const opacity = Math.min(0.7, ratio * 4 + 0.05);
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
            return (
              <g key={`zone-${cell.zone_x}-${cell.zone_y}`}>
                <rect
                  x={rect.x}
                  y={rect.y}
                  width={rect.width}
                  height={rect.height}
                  fill={getZoneFill(cell.ratio)}
                  stroke="rgba(255, 255, 255, 0.05)"
                  strokeWidth="1"
                />
                {cell.ratio > 0.02 && (
                  <text
                    x={rect.x + rect.width / 2}
                    y={rect.y + rect.height / 2 + 4}
                    fill="rgba(255, 255, 255, 0.85)"
                    fontSize="13"
                    fontWeight="bold"
                    textAnchor="middle"
                  >
                    {(cell.ratio * 100).toFixed(1)}%
                  </text>
                )}
              </g>
            );
          })}

        {/* 3. 피치 라인 마킹 (흰색 선) */}
        <g stroke="rgba(255, 255, 255, 0.4)" strokeWidth="2" fill="none">
          {/* 하프라인 */}
          <line x1={halfX} y1={pitchY} x2={halfX} y2={pitchY2} />

          {/* 센터서클 (반지름 9.15m) */}
          <circle cx={centerSpotX} cy={centerSpotY} r={9.15 * 10} />
          <circle cx={centerSpotX} cy={centerSpotY} r="3.5" fill="rgba(255, 255, 255, 0.6)" />

          {/* 홈 페널티 박스 (0..18, 18..62) */}
          {(() => {
            const [p1x, p1y] = toSvg(0, 18);
            const [p2x, p2y] = toSvg(18, 62);
            return <rect x={p1x} y={p1y} width={p2x - p1x} height={p2y - p1y} />;
          })()}

          {/* 홈 골 에어리어 (0..6, 30..50) */}
          {(() => {
            const [g1x, g1y] = toSvg(0, 30);
            const [g2x, g2y] = toSvg(6, 50);
            return <rect x={g1x} y={g1y} width={g2x - g1x} height={g2y - g1y} />;
          })()}

          {/* 홈 페널티 스팟 (12, 40) & 아크 */}
          {(() => {
            const [spX, spY] = toSvg(12, 40);
            return (
              <>
                <circle cx={spX} cy={spY} r="3" fill="rgba(255, 255, 255, 0.6)" />
                <path d={`M ${toSvg(18, 32.5).join(" ")} A ${9.15 * 10} ${9.15 * 10} 0 0 1 ${toSvg(18, 47.5).join(" ")}`} />
              </>
            );
          })()}

          {/* 어웨이 페널티 박스 (102..120, 18..62) */}
          {(() => {
            const [p1x, p1y] = toSvg(102, 18);
            const [p2x, p2y] = toSvg(120, 62);
            return <rect x={p1x} y={p1y} width={p2x - p1x} height={p2y - p1y} />;
          })()}

          {/* 어웨이 골 에어리어 (114..120, 30..50) */}
          {(() => {
            const [g1x, g1y] = toSvg(114, 30);
            const [g2x, g2y] = toSvg(120, 50);
            return <rect x={g1x} y={g1y} width={g2x - g1x} height={g2y - g1y} />;
          })()}

          {/* 어웨이 페널티 스팟 (108, 40) & 아크 */}
          {(() => {
            const [spX, spY] = toSvg(108, 40);
            return (
              <>
                <circle cx={spX} cy={spY} r="3" fill="rgba(255, 255, 255, 0.6)" />
                <path d={`M ${toSvg(102, 32.5).join(" ")} A ${9.15 * 10} ${9.15 * 10} 0 0 0 ${toSvg(102, 47.5).join(" ")}`} />
              </>
            );
          })()}
        </g>

        {/* 4. 360 가시 영역 (visible_area) 다각형 음영 */}
        {showVisibleArea && visibleArea && visibleArea.length >= 6 && (
          <polygon
            points={formatPolygonPoints(visibleArea, SVG_WIDTH, SVG_HEIGHT, MARGIN)}
            fill="rgba(99, 102, 241, 0.18)"
            stroke="rgba(129, 140, 248, 0.6)"
            strokeWidth="2"
            strokeDasharray="4 2"
          />
        )}

        {/* 5. 패스 네트워크 엣지 및 노드 */}
        {showPassNetwork && passEdges && (
          <g>
            {passEdges.map((edge, idx) => {
              const src = nodeMap.get(edge.passer_id);
              const dst = nodeMap.get(edge.recipient_id);
              if (!src || !dst) return null;

              const [x1, y1] = toSvg(src.x, src.y);
              const [x2, y2] = toSvg(dst.x, dst.y);
              const strokeWidth = Math.max(1.5, Math.min(8, edge.count * 0.7));

              return (
                <line
                  key={`pass-edge-${idx}`}
                  x1={x1}
                  y1={y1}
                  x2={x2}
                  y2={y2}
                  stroke="rgba(56, 189, 248, 0.65)"
                  strokeWidth={strokeWidth}
                  markerEnd="url(#pass-arrow)"
                />
              );
            })}
          </g>
        )}

        {showPassNetwork && passNodes && (
          <g>
            {passNodes.map((n) => {
              const [sx, sy] = toSvg(n.x, n.y);
              const r = Math.max(12, Math.min(22, 10 + n.pass_count * 0.3));

              return (
                <g key={`pass-node-${n.player_id}`} className="cursor-pointer">
                  <circle
                    cx={sx}
                    cy={sy}
                    r={r}
                    fill="#0284c7"
                    stroke="#ffffff"
                    strokeWidth="2"
                  />
                  <text
                    x={sx}
                    y={sy + 4}
                    fill="#ffffff"
                    fontSize="11"
                    fontWeight="bold"
                    textAnchor="middle"
                  >
                    {n.jersey_number ?? n.player_name.slice(0, 2)}
                  </text>
                  <text
                    x={sx}
                    y={sy + r + 12}
                    fill="#e0f2fe"
                    fontSize="10"
                    fontWeight="medium"
                    textAnchor="middle"
                  >
                    {n.player_name.split(" ").pop()}
                  </text>
                </g>
              );
            })}
          </g>
        )}

        {/* 6. 포메이션 평균 위치 표시 */}
        {showFormation && formationPlayers && (
          <g>
            {formationPlayers.map((fp) => {
              const [sx, sy] = toSvg(fp.x, fp.y);
              return (
                <g key={`formation-player-${fp.player_id}`}>
                  <circle
                    cx={sx}
                    cy={sy}
                    r="14"
                    fill="#059669"
                    stroke="#ffffff"
                    strokeWidth="2"
                    opacity="0.9"
                  />
                  <text
                    x={sx}
                    y={sy + 4}
                    fill="#ffffff"
                    fontSize="11"
                    fontWeight="bold"
                    textAnchor="middle"
                  >
                    {fp.jersey_number ?? fp.position_name?.slice(0, 2) ?? "P"}
                  </text>
                  <text
                    x={sx}
                    y={sy + 26}
                    fill="#d1fae5"
                    fontSize="10"
                    textAnchor="middle"
                  >
                    {fp.player_name.split(" ").pop()}
                  </text>
                </g>
              );
            })}
          </g>
        )}

        {/* 7. 선수 토큰 및 속도/외삽 렌더링 (리플레이/하이라이트) */}
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

              {/* 액터 하이라이트 후광 링 */}
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

              {/* 선수 원 토큰 */}
              <circle
                cx={sx}
                cy={sy}
                r="13"
                fill={
                  p.is_keeper
                    ? "#eab308"
                    : isHome
                    ? "#2563eb"
                    : "#dc2626"
                }
                stroke={isInferred ? "#94a3b8" : "#ffffff"}
                strokeWidth={isInferred ? 1.5 : 2}
                strokeDasharray={isInferred ? "3 2" : undefined}
                opacity={isInferred ? 0.45 : 1.0}
              />

              {/* 선수 라벨 */}
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

        {/* 8. 공 토큰 */}
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
      </svg>

      {/* 이벤트 오버레이 정보 배너 */}
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
