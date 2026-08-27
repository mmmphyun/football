import React, { useEffect, useRef, useState } from "react";
import { Highlight, HighlightFramesData } from "../types";
import { fetchHighlightFrames } from "../api/client";
import { TacticalBoard } from "./TacticalBoard";
import { interpolateFrames } from "../lib/interpolate";
import {
  AlertCircle,
  Eye,
  FastForward,
  GitFork,
  Pause,
  Play,
  RotateCcw,
  SkipBack,
  SkipForward,
  Users,
  Zap,
} from "lucide-react";

interface HighlightViewProps {
  matchId: number;
  highlights: Highlight[];
}

export const HighlightView: React.FC<HighlightViewProps> = ({
  matchId: _matchId,
  highlights,
}) => {
  const [selectedHlId, setSelectedHlId] = useState<number | null>(
    highlights.length > 0 ? highlights[0].id : null
  );
  const [framesData, setFramesData] = useState<HighlightFramesData | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // 플레이어 재생 상태
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(1.0);
  const [currentSec, setCurrentSec] = useState<number>(0);

  // 시각화 옵션 토글
  const [showVisibleArea, setShowVisibleArea] = useState<boolean>(true);
  const [showPassingLanes, setShowPassingLanes] = useState<boolean>(true);
  const [showVelocity, setShowVelocity] = useState<boolean>(true);
  const [showGhostPrediction, setShowGhostPrediction] = useState<boolean>(true);
  const [showInferredPlayers, setShowInferredPlayers] = useState<boolean>(true);

  // 애니메이션 프레임 참조
  const animRef = useRef<number | null>(null);
  const lastTimeRef = useRef<number | null>(null);

  // 하이라이트 선택 시 프레임 데이터 fetch
  useEffect(() => {
    if (!selectedHlId) return;

    let isMounted = true;
    setIsLoading(true);
    setError(null);
    setIsPlaying(false);

    fetchHighlightFrames(selectedHlId)
      .then((data) => {
        if (!isMounted) return;
        setFramesData(data);
        if (data.frames.length > 0) {
          setCurrentSec(data.frames[0].timestamp_sec);
        }
      })
      .catch((err) => {
        if (!isMounted) return;
        setError(err instanceof Error ? err.message : "프레임 로드 실패");
      })
      .finally(() => {
        if (isMounted) setIsLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [selectedHlId]);

  const frames = framesData?.frames || [];
  const startSec = frames.length > 0 ? frames[0].timestamp_sec : 0;
  const endSec = frames.length > 0 ? frames[frames.length - 1].timestamp_sec : 0;
  const totalDuration = Math.max(0.1, endSec - startSec);

  // 애니메이션 루프 (requestAnimationFrame)
  useEffect(() => {
    if (!isPlaying || frames.length <= 1) {
      if (animRef.current) cancelAnimationFrame(animRef.current);
      lastTimeRef.current = null;
      return;
    }

    const animate = (now: number) => {
      if (lastTimeRef.current !== null) {
        const delta = (now - lastTimeRef.current) / 1000;
        setCurrentSec((prev) => {
          const next = prev + delta * playbackSpeed;
          if (next >= endSec) {
            setIsPlaying(false);
            return endSec;
          }
          return next;
        });
      }
      lastTimeRef.current = now;
      animRef.current = requestAnimationFrame(animate);
    };

    animRef.current = requestAnimationFrame(animate);

    return () => {
      if (animRef.current) cancelAnimationFrame(animRef.current);
    };
  }, [isPlaying, playbackSpeed, endSec, frames.length]);

  // 키보드 단축키 (스페이스바 재생/일시정지)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.code === "Space" && e.target === document.body) {
        e.preventDefault();
        setIsPlaying((p) => !p);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  // 현재 시간 기준 보간된 프레임
  const currentFrame = interpolateFrames(frames, currentSec);

  // 스텝 이전/다음 이동
  const handleStep = (direction: "prev" | "next") => {
    setIsPlaying(false);
    if (frames.length === 0) return;

    if (direction === "prev") {
      const prevF = [...frames].reverse().find((f) => f.timestamp_sec < currentSec - 0.05);
      if (prevF) setCurrentSec(prevF.timestamp_sec);
      else setCurrentSec(startSec);
    } else {
      const nextF = frames.find((f) => f.timestamp_sec > currentSec + 0.05);
      if (nextF) setCurrentSec(nextF.timestamp_sec);
      else setCurrentSec(endSec);
    }
  };

  if (highlights.length === 0) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center text-slate-400 space-y-3">
        <AlertCircle className="w-10 h-10 mx-auto text-amber-400" />
        <div className="text-lg font-bold text-white">추출된 하이라이트가 없습니다</div>
        <p className="text-sm text-slate-400">
          해당 경기는 골 또는 xG 0.25 이상의 유효 슈팅 클립이 존재하지 않습니다.
        </p>
      </div>
    );
  }

  const openLanesCount = currentFrame?.passing_lanes?.filter((l) => l.is_open).length ?? 0;
  const blockedLanesCount = currentFrame?.passing_lanes?.filter((l) => !l.is_open).length ?? 0;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
      {/* 좌측 사이드바: 하이라이트 목록 (4 cols) */}
      <div className="lg:col-span-4 bg-slate-900 border border-slate-800 rounded-2xl p-4 space-y-3">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <h3 className="text-sm font-bold text-white uppercase tracking-wider">
            하이라이트 클립 ({highlights.length})
          </h3>
          <span className="text-[11px] text-slate-400">골 & 고xG 슈팅</span>
        </div>

        <div className="space-y-2 max-h-[600px] overflow-y-auto pr-1">
          {highlights.map((hl) => {
            const isSelected = hl.id === selectedHlId;
            const isGoal = hl.type.toLowerCase().includes("goal");

            return (
              <button
                key={hl.id}
                onClick={() => setSelectedHlId(hl.id)}
                className={`w-full text-left p-3 rounded-xl border transition-all ${
                  isSelected
                    ? "bg-slate-800 border-emerald-500/80 shadow-md ring-1 ring-emerald-500/50"
                    : "bg-slate-950/60 border-slate-800/80 hover:border-slate-700 text-slate-300"
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span
                    className={`text-xs px-2 py-0.5 rounded font-bold ${
                      isGoal
                        ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/40"
                        : "bg-amber-500/20 text-amber-400 border border-amber-500/40"
                    }`}
                  >
                    {isGoal ? "GOAL" : "SHOT"}
                  </span>
                  <span className="font-mono text-xs text-slate-400">
                    {hl.minute}분 {hl.second}초
                  </span>
                </div>
                <div className="text-sm font-semibold text-white truncate">{hl.team_name}</div>
                {hl.xg !== undefined && (
                  <div className="text-[11px] text-slate-400 mt-1 font-mono">
                    기대 득점: <span className="text-emerald-400 font-bold">xG {hl.xg.toFixed(2)}</span>
                  </div>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* 우측 메인: 전술 바둑판 플레이어 (8 cols) */}
      <div className="lg:col-span-8 space-y-4">
        {/* 360 가시 영역 및 패스길 통계 상태 배너 */}
        {framesData && (
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-slate-900 border border-slate-800 p-3 rounded-xl flex items-center justify-between">
              <span className="text-xs text-slate-400">360 가시 영역</span>
              <span className={`text-xs font-bold ${framesData.has_360 ? "text-indigo-400" : "text-slate-500"}`}>
                {framesData.has_360 ? "360 Polygon 활성화" : "2D 이벤트 좌표"}
              </span>
            </div>
            <div className="bg-slate-900 border border-slate-800 p-3 rounded-xl flex items-center justify-between">
              <span className="text-xs text-slate-400">실시간 패스길 상태</span>
              <span className="text-xs font-mono font-bold">
                <span className="text-emerald-400">열림 {openLanesCount}</span> /{" "}
                <span className="text-rose-400">차단 {blockedLanesCount}</span>
              </span>
            </div>
          </div>
        )}

        {isLoading ? (
          <div className="aspect-[124/84] bg-slate-950 rounded-2xl border border-slate-800 flex items-center justify-center text-slate-400 text-sm">
            프레임 데이터 로딩 중...
          </div>
        ) : error ? (
          <div className="aspect-[124/84] bg-slate-950 rounded-2xl border border-rose-900/50 flex items-center justify-center text-rose-400 text-sm p-4 text-center">
            {error}
          </div>
        ) : (
          <TacticalBoard
            players={currentFrame?.players}
            ballLocation={currentFrame?.ball_location}
            visibleArea={currentFrame?.visible_area}
            passingLanes={currentFrame?.passing_lanes}
            showPassingLanes={showPassingLanes}
            showVisibleArea={showVisibleArea}
            showVelocity={showVelocity}
            showGhostPrediction={showGhostPrediction}
            showInferredPlayers={showInferredPlayers}
            frameDescription={currentFrame?.description}
            minute={currentFrame?.minute}
            second={currentFrame?.second}
          />
        )}

        {/* 플레이어 컨트롤 바 */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 space-y-3">
          {/* 타임라인 슬라이더 & 시간 표시 */}
          <div className="space-y-1.5">
            <div className="flex justify-between text-xs font-mono text-slate-400">
              <span>
                {currentFrame?.minute !== undefined
                  ? `${String(currentFrame.minute).padStart(2, "0")}:${String(
                      currentFrame.second ?? 0
                    ).padStart(2, "0")}`
                  : "00:00"}
              </span>
              <span>{(currentSec - startSec).toFixed(1)}s / {totalDuration.toFixed(1)}s</span>
            </div>
            <input
              type="range"
              min={startSec}
              max={endSec}
              step={0.05}
              value={currentSec}
              onChange={(e) => {
                setIsPlaying(false);
                setCurrentSec(Number(e.target.value));
              }}
              className="w-full accent-emerald-500 bg-slate-800 h-2 rounded-lg cursor-pointer"
            />
          </div>

          {/* 재생 제어 버튼 그룹 & 옵션 토글 */}
          <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
            {/* 좌측: 재생 제어 */}
            <div className="flex items-center space-x-2">
              <button
                onClick={() => setCurrentSec(startSec)}
                title="처음으로"
                className="p-2 bg-slate-800 hover:bg-slate-700 rounded-lg text-slate-300 transition-colors"
              >
                <RotateCcw className="w-4 h-4" />
              </button>
              <button
                onClick={() => handleStep("prev")}
                title="이전 프레임"
                className="p-2 bg-slate-800 hover:bg-slate-700 rounded-lg text-slate-300 transition-colors"
              >
                <SkipBack className="w-4 h-4" />
              </button>
              <button
                onClick={() => setIsPlaying((p) => !p)}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 rounded-lg text-white font-semibold flex items-center space-x-1.5 transition-colors shadow"
              >
                {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                <span className="text-xs">{isPlaying ? "일시정지" : "재생"}</span>
              </button>
              <button
                onClick={() => handleStep("next")}
                title="다음 프레임"
                className="p-2 bg-slate-800 hover:bg-slate-700 rounded-lg text-slate-300 transition-colors"
              >
                <SkipForward className="w-4 h-4" />
              </button>

              {/* 속도 조절 */}
              <div className="flex items-center bg-slate-800 rounded-lg p-0.5 border border-slate-700">
                {[0.5, 1.0, 2.0].map((spd) => (
                  <button
                    key={spd}
                    onClick={() => setPlaybackSpeed(spd)}
                    className={`px-2 py-1 text-xs rounded font-mono font-medium transition-colors ${
                      playbackSpeed === spd
                        ? "bg-slate-700 text-emerald-400"
                        : "text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    {spd}x
                  </button>
                ))}
              </div>
            </div>

            {/* 우측: 시각화 옵션 토글 */}
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <button
                onClick={() => setShowPassingLanes((v) => !v)}
                className={`flex items-center space-x-1 px-2.5 py-1.5 rounded-lg border transition-colors ${
                  showPassingLanes
                    ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/40"
                    : "bg-slate-800 text-slate-400 border-slate-700"
                }`}
                title="360 패스길 레이캐스팅 표시"
              >
                <GitFork className="w-3.5 h-3.5" />
                <span>패스길</span>
              </button>

              <button
                onClick={() => setShowVisibleArea((v) => !v)}
                className={`flex items-center space-x-1 px-2.5 py-1.5 rounded-lg border transition-colors ${
                  showVisibleArea
                    ? "bg-indigo-500/20 text-indigo-300 border-indigo-500/40"
                    : "bg-slate-800 text-slate-400 border-slate-700"
                }`}
                title="360 시야각 다각형 표시"
              >
                <Eye className="w-3.5 h-3.5" />
                <span>360 시야각</span>
              </button>

              <button
                onClick={() => setShowVelocity((v) => !v)}
                className={`flex items-center space-x-1 px-2.5 py-1.5 rounded-lg border transition-colors ${
                  showVelocity
                    ? "bg-amber-500/20 text-amber-300 border-amber-500/40"
                    : "bg-slate-800 text-slate-400 border-slate-700"
                }`}
                title="선수 속도 벡터 표시"
              >
                <FastForward className="w-3.5 h-3.5" />
                <span>속도 벡터</span>
              </button>

              <button
                onClick={() => setShowGhostPrediction((v) => !v)}
                className={`flex items-center space-x-1 px-2.5 py-1.5 rounded-lg border transition-colors ${
                  showGhostPrediction
                    ? "bg-purple-500/20 text-purple-300 border-purple-500/40"
                    : "bg-slate-800 text-slate-400 border-slate-700"
                }`}
                title="+2초 외삽 고스트 위치 표시"
              >
                <Zap className="w-3.5 h-3.5" />
                <span>+2초 예측</span>
              </button>

              <button
                onClick={() => setShowInferredPlayers((v) => !v)}
                className={`flex items-center space-x-1 px-2.5 py-1.5 rounded-lg border transition-colors ${
                  showInferredPlayers
                    ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/40"
                    : "bg-slate-800 text-slate-400 border-slate-700"
                }`}
                title="360 미인식 선수 22명 가상 추론 표시"
              >
                <Users className="w-3.5 h-3.5" />
                <span>22명 추론</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
