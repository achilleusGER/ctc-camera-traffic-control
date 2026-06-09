// Calibration — F5 Annotated Screenshot: 4-Punkt-Editor für eine reale Rechteckfläche

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { fetchCameras, fetchCalibration, api, QK } from "../api/client";
import "./Calibration.css";

type Point = { x: number; y: number };

export function Calibration() {
  const { id } = useParams<{ id: string }>();
  const cameraId = Number(id);
  const qc = useQueryClient();
  const camerasQ = useQuery({ queryKey: QK.cameras, queryFn: () => fetchCameras() });
  const calQ = useQuery({ queryKey: QK.calibration(cameraId), queryFn: () => fetchCalibration(cameraId) });
  const camera = camerasQ.data?.find((c) => c.id === cameraId);

  const imgRef = useRef<HTMLImageElement | null>(null);
  const [points, setPoints] = useState<Point[]>([
    { x: 200, y: 600 }, { x: 1500, y: 600 }, { x: 1500, y: 900 }, { x: 200, y: 900 },
  ]);
  const [width, setWidth] = useState(8);
  const [height, setHeight] = useState(6);
  const [imgLoaded, setImgLoaded] = useState(false);

  useEffect(() => {
    if (calQ.data) {
      // Backend liefert source_points als [number, number][],
      // lokaler State erwartet Point[] mit x/y-Feldern.
      setPoints(
        calQ.data.source_points.map(([x, y]) => ({
          x: Math.round(x),
          y: Math.round(y),
        })),
      );
      setWidth(calQ.data.target_width_m);
      setHeight(calQ.data.target_height_m);
    }
  }, [calQ.data]);

  const save = useMutation({
    mutationFn: () =>
      api.put(`/cameras/${cameraId}/calibration/`, {
        source_points: points,
        target_width_m: width,
        target_height_m: height,
      }).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: QK.calibration(cameraId) }),
  });

  const onImageClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!imgRef.current) return;
    const rect = imgRef.current.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * imgRef.current.naturalWidth;
    const y = ((e.clientY - rect.top) / rect.height) * imgRef.current.naturalHeight;
    // Zyklischer Override: jüngster Punkt wird ersetzt, Reihenfolge rotiert
    setPoints((prev) => {
      const next = [...prev];
      next[prev.length - 1] = { x: Math.round(x), y: Math.round(y) };
      // [A, B, C, D] → [D, A, B, C] — der zuletzt gesetzte wird zum "ersten"
      return [next[3], next[0], next[1], next[2]];
    });
  };

  return (
    <div className="cal">
      <header className="cal__header">
        <h1 className="cal__title">Kalibrierung</h1>
        <p className="cal__sub">
          {camera ? `Kamera ${camera.id} · ${camera.name}` : `Kamera ${cameraId}`}
        </p>
      </header>

      <div className="cal__layout">
        <section className="cal__stage">
          <p className="cal__hint">
            4 Punkte auf einer realen, rechteckigen Fläche markieren (Einfahrt, Spur, Zebrastreifen).
            Reihenfolge: TL → TR → BR → BL.
          </p>
          <div className="cal__img-wrap" onClick={onImageClick}>
            {camera ? (
              <img
                ref={imgRef}
                src={`/api/cameras/${cameraId}/stream.mjpg?fps=2`}
                alt="Live-Frame"
                className="cal__img"
                onLoad={() => setImgLoaded(true)}
                crossOrigin="anonymous"
              />
            ) : (
              <div className="cal__no-cam">Kamera nicht gefunden</div>
            )}
            {imgLoaded && (
              <svg className="cal__overlay" viewBox="0 0 1920 1080" preserveAspectRatio="xMidYMid meet">
                <polygon
                  points={points.map((p) => `${p.x},${p.y}`).join(" ")}
                  fill="oklch(72% 0.18 75 / 0.15)"
                  stroke="oklch(72% 0.18 75)"
                  strokeWidth={3}
                />
                {points.map((p, i) => (
                  <g key={i}>
                    <circle cx={p.x} cy={p.y} r={12} fill="oklch(72% 0.18 75)" />
                    <text x={p.x} y={p.y - 18} textAnchor="middle" fill="oklch(94% 0.006 75)" fontSize={20}>
                      {i + 1}
                    </text>
                  </g>
                ))}
              </svg>
            )}
          </div>
        </section>

        <aside className="cal__panel">
          <h2 className="cal__panel-title">Eckpunkte (Pixel)</h2>
          <ul className="cal__points">
            {points.map((p, i) => (
              <li key={i} className="cal__point">
                <span className="cal__point-num">{i + 1}</span>
                <label>x<input type="number" value={p.x} onChange={(e) => {
                  const next = [...points]; next[i] = { ...p, x: Number(e.target.value) }; setPoints(next);
                }} /></label>
                <label>y<input type="number" value={p.y} onChange={(e) => {
                  const next = [...points]; next[i] = { ...p, y: Number(e.target.value) }; setPoints(next);
                }} /></label>
              </li>
            ))}
          </ul>

          <h2 className="cal__panel-title">Reale Maße (Meter)</h2>
          <div className="cal__meters">
            <label>Breite<input type="number" step={0.1} min={0.1} value={width} onChange={(e) => setWidth(Number(e.target.value))} /></label>
            <label>Höhe<input type="number" step={0.1} min={0.1} value={height} onChange={(e) => setHeight(Number(e.target.value))} /></label>
          </div>

          <button
            onClick={() => save.mutate()}
            disabled={save.isPending}
            className="cal__save"
          >
            {save.isPending ? "Speichere…" : "Kalibrierung speichern"}
          </button>
          {save.isSuccess && <p className="cal__msg cal__msg--ok">Gespeichert ✓</p>}
          {save.isError && <p className="cal__msg cal__msg--err">Fehler beim Speichern</p>}
        </aside>
      </div>
    </div>
  );
}
