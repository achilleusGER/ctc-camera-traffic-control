// Bento Grid — 7 Tiles, asymmetrisch (Startseite /)

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import {
  fetchCameras, fetchCountsToday, fetchSpeedAverage, fetchHeatmap,
  fetchViolations, fetchStorageInfo, QK,
} from "../api/client";
import { classLabelDE, formatBytes, formatDateTime, formatNumber, formatSpeed } from "../lib/format";
import "./Dashboard.css";

export function Dashboard() {
  const camerasQ = useQuery({ queryKey: QK.cameras, queryFn: () => fetchCameras() });
  const countsQ = useQuery({ queryKey: QK.countsToday(), queryFn: () => fetchCountsToday() });
  const speedQ = useQuery({ queryKey: QK.speedAverage(), queryFn: () => fetchSpeedAverage() });
  const heatmapQ = useQuery({ queryKey: QK.heatmap({}), queryFn: () => fetchHeatmap({}) });
  const violationsQ = useQuery({ queryKey: QK.violations({ limit: 5 }), queryFn: () => fetchViolations({ limit: 5 }) });
  const storageQ = useQuery({ queryKey: QK.storage, queryFn: fetchStorageInfo });

  const cameras = camerasQ.data ?? [];
  const [selectedCamId, setSelectedCamId] = useState<number | null>(null);
  const activeCameraId = selectedCamId ?? cameras[0]?.id ?? null;

  return (
    <div className="bento">
      {/* TILE 1 (2x2) — Live-Stream */}
      <section className="bento__tile bento__tile--stream">
        <header className="tile__header">
          <h2 className="tile__title">Live</h2>
          {cameras.length > 0 && (
            <span className="tile__sub">
              {cameras.find((c) => c.id === activeCameraId)?.name ?? "—"}
            </span>
          )}
        </header>
        <div className="tile__stream">
          {activeCameraId ? (
            <img
              src={`/api/cameras/${activeCameraId}/stream.mjpg?fps=10`}
              alt="Live-Stream"
              className="tile__stream-img"
            />
          ) : (
            <div className="tile__stream-empty">Keine Kameras konfiguriert</div>
          )}
        </div>
        {cameras.length > 1 && (
          <ul className="tile__camera-picker">
            {cameras.map((c) => (
              <li key={c.id}>
                <button
                  className={c.id === activeCameraId ? "picker-btn picker-btn--active" : "picker-btn"}
                  onClick={() => setSelectedCamId(c.id)}
                  aria-label={`Kamera ${c.name} auswählen`}
                >
                  <span className={`picker-btn__dot picker-btn__dot--${c.enabled ? "ok" : "down"}`} />
                  {c.name}
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* TILE 2 (1x1) — Counts heute */}
      <section className="bento__tile">
        <header className="tile__header">
          <h3 className="tile__title">Heute</h3>
        </header>
        <div className="tile__counts">
          {(["car", "truck", "motorcycle", "bicycle", "bus", "person"] as const).map((cls) => {
            const cnt = countsQ.data?.find((c) => c.vehicle_class === cls)?.count ?? 0;
            return (
              <div key={cls} className="count-row">
                <span className="count-row__label">{classLabelDE(cls)}</span>
                <span className="count-row__value mono">{formatNumber(cnt)}</span>
              </div>
            );
          })}
        </div>
      </section>

      {/* TILE 3 (1x1) — Avg-Speed */}
      <section className="bento__tile">
        <header className="tile__header">
          <h3 className="tile__title">Ø Geschwindigkeit</h3>
        </header>
        <div className="tile__speed">
          <div className="speed-big mono">
            {speedQ.data?.avg_kmh != null ? formatNumber(speedQ.data.avg_kmh, 0) : "—"}
            <span className="speed-big__unit">km/h</span>
          </div>
          <div className="speed-meta">
            <span>Max: <span className="mono">{speedQ.data?.max_kmh != null ? formatNumber(speedQ.data.max_kmh, 0) : "—"}</span></span>
            <span>·</span>
            <span><span className="mono">{formatNumber(speedQ.data?.n ?? 0)}</span> Messungen</span>
          </div>
        </div>
      </section>

      {/* TILE 4 (1x1) — Heatmap */}
      <section className="bento__tile">
        <header className="tile__header">
          <h3 className="tile__title">Wochentrend</h3>
        </header>
        <div className="tile__heatmap">
          <div className="heatmap">
            {Array.from({ length: 7 }).map((_, wd) => (
              <div key={wd} className="heatmap__row">
                {Array.from({ length: 24 }).map((_, hr) => {
                  const cell = heatmapQ.data?.find((c) => c.weekday === wd && c.hour === hr);
                  const count = cell?.count ?? 0;
                  const max = Math.max(1, ...(heatmapQ.data?.map((c) => c.count) ?? [1]));
                  const intensity = Math.min(1, count / max);
                  return (
                    <div
                      key={hr}
                      className="heatmap__cell"
                      style={{
                        background: intensity === 0
                          ? "var(--heat-0)"
                          : intensity < 0.33
                            ? "var(--heat-1)"
                            : intensity < 0.66
                              ? "var(--heat-2)"
                              : "var(--heat-3)",
                      }}
                      title={`${["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"][wd]} ${hr}:00 — ${count} Events`}
                    />
                  );
                })}
              </div>
            ))}
          </div>
          <div className="heatmap__legend">
            <span>0</span>
            <div className="heatmap__gradient" />
            <span>max</span>
          </div>
        </div>
      </section>

      {/* TILE 5 (2x1) — Letzte Verstöße */}
      <section className="bento__tile bento__tile--wide">
        <header className="tile__header">
          <h3 className="tile__title">Letzte Verstöße</h3>
        </header>
        {violationsQ.data && violationsQ.data.length > 0 ? (
          <ul className="violations-list">
            {violationsQ.data.map((v) => {
              const delta = (v.speed_kmh ?? 0) - (v.speed_limit_kmh ?? 0);
              const evidence = v.evidence_paths[0];
              return (
                <li key={v.id} className="violation-row">
                  {evidence && (
                    <img
                      src={`/api/media/evidence/${evidence}`}
                      alt=""
                      className="violation-row__thumb"
                    />
                  )}
                  <div className="violation-row__info">
                    <span className="violation-row__class">{classLabelDE(v.vehicle_class)}</span>
                    <span className="violation-row__dir muted">{v.direction}</span>
                    <span className="violation-row__time mono">{formatDateTime(v.ts)}</span>
                  </div>
                  <div className="violation-row__speed">
                    <span className="violation-row__value mono">{formatSpeed(v.speed_kmh, 0)}</span>
                    <span className="violation-row__delta mono">+{formatNumber(delta, 0)}</span>
                  </div>
                </li>
              );
            })}
          </ul>
        ) : (
          <p className="muted">Keine Verstöße in den letzten Tagen.</p>
        )}
      </section>

      {/* TILE 6 (1x1) — Kamera-Status */}
      <section className="bento__tile">
        <header className="tile__header">
          <h3 className="tile__title">Kameras</h3>
        </header>
        <ul className="camera-list">
          {cameras.length === 0 && <li className="muted">Keine Kameras</li>}
          {cameras.slice(0, 4).map((c) => (
            <li key={c.id} className="camera-row">
              <span className={`camera-row__dot camera-row__dot--${c.enabled ? "ok" : "down"}`} />
              <span className="camera-row__name">{c.name}</span>
              <span className="camera-row__fps mono">{c.fps_limit} fps</span>
            </li>
          ))}
        </ul>
      </section>

      {/* TILE 7 (1x1) — Storage */}
      <section className="bento__tile">
        <header className="tile__header">
          <h3 className="tile__title">Speicher</h3>
        </header>
        <div className="storage">
          <div className="storage__row">
            <span className="storage__label">Media</span>
            <span className="storage__value mono">{formatBytes(storageQ.data?.size_bytes ?? 0)}</span>
          </div>
          <div className="storage__row">
            <span className="storage__label">Dateien</span>
            <span className="storage__value mono">{formatNumber(storageQ.data?.file_count ?? 0)}</span>
          </div>
          <div className="storage__row">
            <span className="storage__label">Pfad</span>
            <span className="storage__value storage__path mono">{storageQ.data?.media_dir ?? "—"}</span>
          </div>
        </div>
      </section>
    </div>
  );
}
