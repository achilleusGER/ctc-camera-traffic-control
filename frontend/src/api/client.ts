// Axios-Client + QueryClient

import axios from "axios";
import { QueryClient } from "@tanstack/react-query";

const baseURL = import.meta.env.VITE_API_BASE || "/api";

export const api = axios.create({
  baseURL,
  timeout: 15_000,
});

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,        // 30s default
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

// Convenience-Funktionen (statt jedes Mal queryClient+queryFn zu schreiben)

import type {
  Camera, Street, CrossingEvent, HeatmapCell, SpeedBin, SpeedAverage,
  CountsByClass, StorageInfo, CountingLine, Calibration,
} from "./types";

// ─── Query-Keys (zentral) ─────────────────────────────────────────────────

export const QK = {
  streets: ["streets"] as const,
  cameras: ["cameras"] as const,
  camerasByStreet: (streetId: number) => ["cameras", { streetId }] as const,
  lines: (cameraId: number) => ["lines", cameraId] as const,
  calibration: (cameraId: number) => ["calibration", cameraId] as const,
  countsToday: (cameraId?: number) => ["counts-today", cameraId ?? null] as const,
  speedAverage: (cameraId?: number) => ["speed-avg", cameraId ?? null] as const,
  heatmap: (range: { since?: string; until?: string; cameraId?: number }) =>
    ["heatmap", range] as const,
  speedHistogram: (range: { since?: string; until?: string; cameraId?: number }) =>
    ["speed-hist", range] as const,
  violations: (range: { cameraId?: number; since?: string; until?: string; limit?: number }) =>
    ["violations", range] as const,
  violation: (id: number) => ["violation", id] as const,
  events: (range: { cameraId?: number; since?: string; until?: string; limit?: number }) =>
    ["events", range] as const,
  storage: ["storage"] as const,
};

// ─── Fetch-Funktionen ─────────────────────────────────────────────────────

export async function fetchStreets(): Promise<Street[]> {
  return (await api.get<Street[]>("/streets/")).data;
}
export async function fetchCameras(streetId?: number): Promise<Camera[]> {
  return (await api.get<Camera[]>("/cameras/", { params: streetId ? { street_id: streetId } : {} })).data;
}
export async function fetchLines(cameraId: number): Promise<CountingLine[]> {
  return (await api.get<CountingLine[]>(`/cameras/${cameraId}/lines/`)).data;
}
export async function fetchCalibration(cameraId: number): Promise<Calibration | null> {
  return (await api.get<Calibration | null>(`/cameras/${cameraId}/calibration/`)).data;
}

// Snapshot-URL für den Kalibrierungs-/Linien-Editor. Der Browser holt das
// JPEG direkt; der Cache-Buster (Date.now()) sorgt dafür, dass beim
// Neuladen der Editor-Seite immer das aktuelle Bild geladen wird, nicht
// der stale Cache. Bewusst KEIN useQuery, weil <img src=...> einfacher ist.
export function snapshotUrl(cameraId: number, bust: number = Date.now()): string {
  return `${baseURL}/cameras/${cameraId}/snapshot?t=${bust}`;
}
export async function fetchCountsToday(cameraId?: number): Promise<CountsByClass[]> {
  return (await api.get<CountsByClass[]>("/stats/today", { params: cameraId ? { camera_id: cameraId } : {} })).data;
}
export async function fetchSpeedAverage(cameraId?: number): Promise<SpeedAverage> {
  return (await api.get<SpeedAverage>("/stats/speed-average", { params: cameraId ? { camera_id: cameraId } : {} })).data;
}
export async function fetchHeatmap(range: { since?: string; until?: string; cameraId?: number }): Promise<HeatmapCell[]> {
  return (await api.get<HeatmapCell[]>("/reports/heatmap", { params: range })).data;
}
export async function fetchSpeedHistogram(range: { since?: string; until?: string; cameraId?: number; bin_kmh?: number }): Promise<SpeedBin[]> {
  return (await api.get<SpeedBin[]>("/reports/speed-histogram", { params: range })).data;
}
export async function fetchViolations(range: { cameraId?: number; since?: string; until?: string; limit?: number }): Promise<CrossingEvent[]> {
  return (await api.get<CrossingEvent[]>("/violations/", { params: range })).data;
}
export async function fetchViolation(id: number): Promise<CrossingEvent> {
  return (await api.get<CrossingEvent>(`/violations/${id}`)).data;
}
export async function fetchStorageInfo(): Promise<StorageInfo> {
  return (await api.get<StorageInfo>("/admin/storage-info")).data;
}
