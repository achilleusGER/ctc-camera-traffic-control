// Calibration — Mode-Switch: Linien (2 Punkte) ↔ Perspektive (4 Punkte)
//
// Inspiration: Kamera-Trafficcontrol/Calibration.tsx
// - Mode-Switch mit Counter im Button-Text (Linie 1/2, Perspektive 3/4)
// - Snapshot statt Live-Stream (CPU-schonend, der MJPEG-Stream war beim
//   Klicken mit Overlay im Weg)
// - Bestehende Linien als gestricheltes Overlay sichtbar
// - Löschen-Button pro Linie in einer Tabelle
// - Punkte werden resettet bei >max, nicht ueberschrieben

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  api,
  fetchCalibration,
  fetchCameras,
  QK,
  snapshotUrl,
} from "../api/client";
import type { CountingLine } from "../api/types";
import { CameraPicker } from "../components/CameraPicker";
import "./Calibration.css";

type Pt = { x: number; y: number };
type Mode = "line" | "calib";

const MAX_PTS: Record<Mode, number> = { line: 2, calib: 4 };

export function Calibration() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const cameraId = Number(id);
  const qc = useQueryClient();

  const camerasQ = useQuery({ queryKey: QK.cameras, queryFn: () => fetchCameras() });
  // CameraDetail liefert gleich lines+calibration mit (Phase 7.2)
  const camQ = useQuery({
    queryKey: ["camera", cameraId],
    queryFn: async () => (await api.get(`/cameras/${cameraId}/`)).data as {
      id: number;
      name: string;
      width: number;
      height: number;
      lines: CountingLine[];
      calibration: { source_points: number[][]; target_width_m: number; target_height_m: number } | null;
    },
  });
  const calQ = useQuery({ queryKey: QK.calibration(cameraId), queryFn: () => fetchCalibration(cameraId) });

  const camera = camerasQ.data?.find((c) => c.id === cameraId);
  const dims = camQ.data ? { w: camQ.data.width, h: camQ.data.height } : { w: 1920, h: 1080 };

  // Modus
  const [mode, setMode] = useState<Mode>("line");

  // Linien-Modus
  const [linePts, setLinePts] = useState<Pt[]>([]);
  const [lineName, setLineName] = useState("Fahrbahn");
  const [dirIn, setDirIn] = useState("stadteinwärts");
  const [dirOut, setDirOut] = useState("stadtauswärts");
  const [lineLimit, setLineLimit] = useState<number>(50);

  // Perspektive-Modus
  const [calibPts, setCalibPts] = useState<Pt[]>([]);
  const [targetW, setTargetW] = useState(8);
  const [targetH, setTargetH] = useState(6);

  const imgRef = useRef<HTMLImageElement | null>(null);
  const [snapshotBust, setSnapshotBust] = useState(Date.now());

  // Initial-Load der Perspektive aus Backend
  useEffect(() => {
    if (calQ.data) {
      setCalibPts(calQ.data.source_points.map(([x, y]) => ({ x: Math.round(x), y: Math.round(y) })));
      setTargetW(calQ.data.target_width_m);
      setTargetH(calQ.data.target_height_m);
    }
  }, [calQ.data]);

  const activePts = mode === "line" ? linePts : calibPts;
  const setActivePts = mode === "line" ? setLinePts : setCalibPts;

  const onImgClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!imgRef.current) return;
    const rect = imgRef.current.getBoundingClientRect();
    const x = Math.round(((e.clientX - rect.left) / rect.width) * imgRef.current.naturalWidth);
    const y = Math.round(((e.clientY - rect.top) / rect.height) * imgRef.current.naturalHeight);
    setActivePts((prev) => {
      // Bei >max wird resettet (NICHT ueberschrieben wie in der vorigen Version)
      if (prev.length >= MAX_PTS[mode]) return [{ x, y }];
      return [...prev, { x, y }];
    });
  };

  const refreshSnapshot = () => setSnapshotBust(Date.now());

  // Linie speichern
  const createLine = useMutation({
    mutationFn: () =>
      api
        .post(`/cameras/${cameraId}/lines/`, {
          name: lineName,
          points: linePts.map((p) => [p.x, p.y]),
          direction_in_label: dirIn,
          direction_out_label: dirOut,
          speed_limit_kmh: lineLimit || null,
        })
        .then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["camera", cameraId] });
      qc.invalidateQueries({ queryKey: QK.lines(cameraId) });
      setLinePts([]);
      refreshSnapshot();
    },
  });

  const deleteLine = useMutation({
    mutationFn: (lineId: number) => api.delete(`/cameras/${cameraId}/lines/${lineId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["camera", cameraId] }),
  });

  // Kalibrierung speichern
  const saveCalib = useMutation({
    mutationFn: () =>
      api
        .put(`/cameras/${cameraId}/calibration/`, {
          source_points: calibPts.map((p) => [p.x, p.y]),
          target_width_m: targetW,
          target_height_m: targetH,
        })
        .then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QK.calibration(cameraId) });
      qc.invalidateQueries({ queryKey: ["camera", cameraId] });
      setCalibPts([]);
    },
  });

  const lines = camQ.data?.lines ?? [];

  return (
    <div className="cal">
      <header className="cal__header">
        <div className="cal__head-row">
          <div>
            <h1 className="cal__title">Kalibrierung</h1>
            <p className="cal__sub">
              {camera
                ? `Kamera ${camera.id} · ${camera.name}`
                : camerasQ.data && camerasQ.data.length > 0
                  ? "Bitte Kamera wählen"
                  : "Keine Kamera konfiguriert"}{" "}
              {lines.length > 0 && (
                <>· {lines.length} {lines.length === 1 ? "Linie" : "Linien"}</>
              )}{" "}
              {calQ.data && <>· kalibriert</>}
            </p>
          </div>
          <CameraPicker
            value={Number.isFinite(cameraId) && cameraId > 0 ? cameraId : null}
            onChange={(newId) => navigate(`/calibration/${newId}`)}
          />
        </div>
      </header>

      <div className="cal__mode">
        <button
          className={`cal__mode-btn${mode === "line" ? " cal__mode-btn--active" : ""}`}
          onClick={() => setMode("line")}
        >
          Linie ({linePts.length}/{MAX_PTS.line})
        </button>
        <button
          className={`cal__mode-btn${mode === "calib" ? " cal__mode-btn--active" : ""}`}
          onClick={() => setMode("calib")}
        >
          Perspektive ({calibPts.length}/{MAX_PTS.calib})
        </button>
        <button
          className="cal__mode-btn"
          onClick={() => (mode === "line" ? setLinePts([]) : setCalibPts([]))}
        >
          Zurücksetzen
        </button>
        <button className="cal__mode-btn" onClick={refreshSnapshot} title="Neuen Snapshot holen">
          ↻ Snapshot
        </button>
      </div>

      <div className="cal__layout">
        <section className="cal__stage">
          <p className="cal__hint">
            {mode === "line"
              ? "Klicke 2 Punkte: Start und Ende der Zähllinie. Perspektive: Linie quer zur Fahrtrichtung."
              : "Klicke 4 Punkte auf einer realen, rechteckigen Fläche. Reihenfolge: TL → TR → BR → BL."}
          </p>
          <div className="cal__img-wrap" onClick={onImgClick}>
            <img
              ref={imgRef}
              src={snapshotUrl(cameraId, snapshotBust)}
              alt="Snapshot"
              className="cal__img"
              onLoad={() => {
                // Bild geladen — Viewport passt
              }}
              onError={(e) => {
                (e.currentTarget as HTMLImageElement).style.opacity = "0.2";
              }}
            />
            <svg
              className="cal__overlay"
              viewBox={`0 0 ${dims.w} ${dims.h}`}
              preserveAspectRatio="xMidYMid meet"
            >
              {/* bestehende Linien */}
              {lines.map((l) => (
                <g key={l.id} opacity={0.55} className="cal__persisted">
                  <line
                    x1={l.points[0][0]}
                    y1={l.points[0][1]}
                    x2={l.points[1][0]}
                    y2={l.points[1][1]}
                    className="cal__persisted-line"
                  />
                  <circle cx={l.points[0][0]} cy={l.points[0][1]} r={6} className="cal__persisted-dot" />
                  <circle cx={l.points[1][0]} cy={l.points[1][1]} r={6} className="cal__persisted-dot" />
                </g>
              ))}

              {/* aktuelle Linie (2 Punkte) */}
              {mode === "line" && linePts.length === 2 && (
                <line
                  x1={linePts[0].x}
                  y1={linePts[0].y}
                  x2={linePts[1].x}
                  y2={linePts[1].y}
                  className="cal__current-line"
                />
              )}

              {/* aktuelle Perspektive (4 Punkte) */}
              {mode === "calib" && calibPts.length >= 2 && (
                <polygon
                  points={calibPts.map((p) => `${p.x},${p.y}`).join(" ")}
                  className="cal__current-poly"
                />
              )}

              {/* Punkte mit Nummern */}
              {activePts.map((p, i) => (
                <g key={i}>
                  <circle cx={p.x} cy={p.y} r={12} className="cal__current-dot" />
                  <text
                    x={p.x}
                    y={p.y - 18}
                    textAnchor="middle"
                    className="cal__current-num"
                    fontSize={22}
                    fontWeight={700}
                  >
                    {i + 1}
                  </text>
                </g>
              ))}
            </svg>
          </div>
        </section>

        <aside className="cal__panel">
          {mode === "line" ? (
            <>
              <h2 className="cal__panel-title">Zähllinie</h2>
              <label className="cal__field">
                Name
                <input value={lineName} onChange={(e) => setLineName(e.target.value)} />
              </label>
              <label className="cal__field">
                Richtung „rein"
                <input value={dirIn} onChange={(e) => setDirIn(e.target.value)} />
              </label>
              <label className="cal__field">
                Richtung „raus"
                <input value={dirOut} onChange={(e) => setDirOut(e.target.value)} />
              </label>
              <label className="cal__field">
                Tempolimit (km/h)
                <input
                  type="number"
                  min={5}
                  max={250}
                  value={lineLimit}
                  onChange={(e) => setLineLimit(Number(e.target.value))}
                />
              </label>
              <button
                className="cal__save"
                disabled={linePts.length !== 2 || createLine.isPending}
                onClick={() => createLine.mutate()}
              >
                {createLine.isPending ? "Speichere…" : "Linie speichern"}
              </button>

              <h2 className="cal__panel-title" style={{ marginTop: "var(--space-3)" }}>
                Vorhandene Linien
              </h2>
              {lines.length === 0 ? (
                <p className="muted" style={{ margin: 0 }}>Noch keine.</p>
              ) : (
                <table className="cal__lines-table">
                  <tbody>
                    {lines.map((l) => (
                      <tr key={l.id}>
                        <td>
                          <span className="mono">{l.name}</span>
                          <br />
                          <span className="muted" style={{ fontSize: "var(--text-xs)" }}>
                            {l.speed_limit_kmh ?? "—"} km/h
                          </span>
                        </td>
                        <td style={{ textAlign: "right" }}>
                          <button
                            className="cal__btn cal__btn--danger"
                            onClick={() => {
                              if (confirm(`Linie "${l.name}" löschen?`)) deleteLine.mutate(l.id);
                            }}
                          >
                            Löschen
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </>
          ) : (
            <>
              <h2 className="cal__panel-title">Perspektive (Speed)</h2>
              <p className="cal__hint" style={{ margin: 0 }}>
                {calQ.data ? "✓ Kalibrierung vorhanden" : "Noch nicht kalibriert"}
              </p>
              <label className="cal__field">
                Reale Breite (m)
                <input
                  type="number"
                  step={0.1}
                  min={0.1}
                  value={targetW}
                  onChange={(e) => setTargetW(Number(e.target.value))}
                />
              </label>
              <label className="cal__field">
                Reale Länge (m)
                <input
                  type="number"
                  step={0.1}
                  min={0.1}
                  value={targetH}
                  onChange={(e) => setTargetH(Number(e.target.value))}
                />
              </label>
              <button
                className="cal__save"
                disabled={calibPts.length !== 4 || saveCalib.isPending}
                onClick={() => saveCalib.mutate()}
              >
                {saveCalib.isPending ? "Speichere…" : "Kalibrierung speichern"}
              </button>
            </>
          )}
        </aside>
      </div>
    </div>
  );
}
