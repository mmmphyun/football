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
  is_starter?: boolean;
  x: number;
  y: number;
  event_count?: number;
}

export interface FormationSummary {
  formation?: string;
  formation_name?: string;
  players?: FormationPlayer[];
  starters?: FormationPlayer[];
  substitutes?: FormationPlayer[];
  all_played_players?: FormationPlayer[];
  players_overall?: FormationPlayer[];
  players_in_possession?: FormationPlayer[];
  players_out_of_possession?: FormationPlayer[];
  team_length?: number;
  team_width?: number;
  team_center_x?: number;
  team_center_y?: number;
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
  position?: string;
  is_starter?: boolean;
  x: number;
  y: number;
  pass_count?: number;
  pass_attempts?: number;
  pass_completions?: number;
  pass_accuracy?: number;
  progressive_passes?: number;
}

export interface PassEdge {
  passer_id: number;
  recipient_id: number;
  count: number;
  progressive_count?: number;
  source_id?: number;
  source_name?: string;
  target_id?: number;
  target_name?: string;
  pass_count?: number;
}

export interface PassNetworkSummary {
  team_id?: number;
  total_passes?: number;
  completed_passes?: number;
  pass_accuracy?: number;
  progressive_passes?: number;
  progressive_pass_ratio?: number;
  avg_pass_progression_m?: number;
  nodes: PassNode[];
  edges: PassEdge[];
}

export interface PressureEvent {
  x: number;
  y: number;
  type: string;
  is_high_press: boolean;
}

export interface BuildupSummary {
  team_id?: number;
  total_possessions?: number;
  avg_passes_per_possession?: number;
  long_buildup_sequences?: number;
  defensive_third_pct?: number;
  middle_third_pct?: number;
  attacking_third_pct?: number;
  progressive_pass_ratio?: number;
  progressive_carry_ratio?: number;
  buildup_start_distribution?: {
    defensive_third: number;
    middle_third: number;
    attacking_third: number;
    defensive_third_ratio: number;
    middle_third_ratio: number;
    attacking_third_ratio: number;
  };
  progression?: {
    total_passes: number;
    progressive_passes: number;
    progressive_pass_ratio: number;
    total_carries: number;
    progressive_carries: number;
    progressive_carry_ratio: number;
  };
}

export interface PressureSummary {
  ppda: number | null;
  high_press_events: number;
  total_pressure_events: number;
  pressure_per_min: number;
  turnovers_forced_att_third: number;
  pressure_events?: PressureEvent[];
  pressures_by_third?: {
    defensive_third: number;
    middle_third: number;
    attacking_third: number;
  };
}

export interface TransitionSequence {
  start: [number, number];
  end: [number, number];
  sec: number;
  speed: number;
  is_fast: boolean;
  reached_final_third: boolean;
}

export interface TransitionsSummary {
  team_id?: number;
  turnovers_won?: number;
  fast_transitions_to_att_third?: number;
  avg_transition_sec?: number | null;
  total_recoveries?: number;
  fast_transitions?: number;
  slow_transitions?: number;
  fast_transition_ratio?: number;
  avg_transition_speed_mps?: number;
  transition_sequences?: TransitionSequence[];
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
