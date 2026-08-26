/**
 * 축구 전술 분석 및 360 리플레이 데이터 모델 타입 정의.
 */

export interface Competition {
  competition_id: number;
  season_id: number;
  name: string;
  season_name?: string;
  match_count?: number;
  has_360?: boolean;
}

export interface Match {
  match_id: number;
  competition_id: number;
  season_id: number;
  match_date: string;
  home_team: string;
  away_team: string;
  home_score: number;
  away_score: number;
  has_360: boolean;
  status: "raw" | "processed" | "error";
  summary_json?: string;
}

export interface FormationPlayer {
  player_id: number;
  player_name: string;
  jersey_number?: number;
  position_id?: number;
  position_name?: string;
  x: number;
  y: number;
  event_count?: number;
}

export interface FormationSummary {
  formation_name?: string;
  players: FormationPlayer[];
}

export interface ZoneCell {
  zone_x: number;
  zone_y: number;
  count: number;
  ratio: number;
}

export interface ZonesSummary {
  grid_cols: number;
  grid_rows: number;
  total_samples: number;
  cells: ZoneCell[];
}

export interface PassNode {
  player_id: number;
  player_name: string;
  jersey_number?: number;
  x: number;
  y: number;
  pass_count: number;
  progressive_passes: number;
}

export interface PassEdge {
  passer_id: number;
  recipient_id: number;
  count: number;
  progressive_count: number;
}

export interface PassNetworkSummary {
  nodes: PassNode[];
  edges: PassEdge[];
}

export interface PressureSummary {
  ppda: number | null;
  high_press_events: number;
  total_pressure_events: number;
  pressure_per_min: number;
  turnovers_forced_att_third: number;
}

export interface BuildupSummary {
  defensive_third_pct: number;
  middle_third_pct: number;
  attacking_third_pct: number;
  progressive_pass_ratio: number;
  progressive_carry_ratio: number;
}

export interface TransitionsSummary {
  turnovers_won: number;
  fast_transitions_to_att_third: number;
  avg_transition_sec: number | null;
}

export interface TeamSummary {
  team_id: number;
  team_name: string;
  formation: FormationSummary;
  zones: ZonesSummary;
  passes: PassNetworkSummary;
  pressure: PressureSummary;
  buildup: BuildupSummary;
  transitions: TransitionsSummary;
}

export interface MatchSummary {
  match_id?: number;
  match_duration_min: number;
  team_ids: number[];
  teams: Record<string, TeamSummary>;
}

export interface Highlight {
  id: number;
  match_id: number;
  type: string;
  period: number;
  minute: number;
  second: number;
  team_id: number;
  team_name: string;
  xg?: number;
  start_event?: number;
  end_event?: number;
  event_index?: number;
  window_start_sec?: number;
  window_end_sec?: number;
}

export interface FramePlayer {
  player_id?: number;
  player_name?: string;
  team_id?: number;
  is_teammate: boolean;
  is_actor: boolean;
  is_keeper: boolean;
  location: [number, number];
  velocity?: [number, number];
  speed_mps?: number;
  pred_location?: [number, number];
  is_inferred?: boolean;
}

export interface Frame {
  frame_index: number;
  event_index?: number;
  event_id?: string;
  timestamp_sec: number;
  minute: number;
  second: number;
  description?: string;
  ball_location?: [number, number];
  visible_area?: number[]; // [x1, y1, x2, y2, ...]
  players: FramePlayer[];
}

export interface PlayerMeta {
  player_id: number;
  team_id: number;
  team_name: string;
  player_name: string;
  player_nickname?: string;
  jersey_number?: number;
  is_starter: boolean;
  primary_position?: string;
}

export interface HighlightFramesData {
  highlight_id: number;
  match_id: number;
  has_360: boolean;
  frames: Frame[];
  players: PlayerMeta[];
}

export type ViewMode = "tactics" | "highlights";

export type TacticalTab = "formation" | "zones" | "passes" | "pressure" | "buildup" | "transitions";
