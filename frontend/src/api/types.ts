// API-Typen — gespiegelt aus backend/app/schemas.py

export interface Street {
  id: number;
  name: string;
  description: string | null;
  created_at: string;
}

export interface Camera {
  id: number;
  name: string;
  rtsp_url_low: string;
  rtsp_url_high: string | null;
  street_id: number | null;
  width: number;
  height: number;
  infer_width: number;
  fps_limit: number;
  default_speed_limit_kmh: number | null;
  alpr_enabled: boolean;
  model_variant: "m" | "s";
  enabled: boolean;
  created_at: string;
}

export interface CountingLine {
  id: number;
  camera_id: number;
  name: string;
  points: [number, number][];
  direction_in_label: string;
  direction_out_label: string;
  speed_limit_kmh: number | null;
  created_at: string;
}

export interface Calibration {
  id: number;
  camera_id: number;
  source_points: [number, number][];
  target_width_m: number;
  target_height_m: number;
  updated_at: string;
}

export interface Plate {
  id: number;
  plate_text: string;
  confidence: number | null;
  captured_at: string;
}

export interface CrossingEvent {
  id: number;
  camera_id: number;
  line_id: number | null;
  ts: string;
  vehicle_class: string;
  direction: string;
  track_id: number | null;
  speed_kmh: number | null;
  speed_limit_kmh: number | null;
  is_speeding: boolean;
  evidence_paths: string[];
  plates: Plate[];
}

export interface CountsByClass {
  vehicle_class: string;
  count: number;
}

export interface CountsByHour {
  hour: number;
  count: number;
}

export interface SpeedBin {
  bin_start_kmh: number;
  bin_end_kmh: number;
  count: number;
}

export interface HeatmapCell {
  weekday: number; // 0=Mon ... 6=Sun
  hour: number;    // 0..23
  count: number;
}

export interface SpeedAverage {
  avg_kmh: number | null;
  max_kmh: number | null;
  n: number;
}

export interface StorageInfo {
  media_dir: string;
  exists: boolean;
  file_count: number;
  size_bytes: number;
}

export interface CleanupResult {
  deleted_events: number;
  deleted_files: number;
  freed_bytes: number;
  older_than_days: number;
}

// WebSocket-Live-Event
export interface LiveEvent {
  type: "event";
  event: {
    id: number;
    camera_id: number;
    ts: string;
    vehicle_class: string;
    direction: string;
    speed_kmh: number | null;
    speed_limit_kmh: number | null;
    is_speeding: boolean;
  };
}
