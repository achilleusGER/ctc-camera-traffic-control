// LiveView — H6 Photographic fold: 1 Kamera groß, Kamera-Picker

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { fetchCameras, QK } from "../api/client";
import "./LiveView.css";

export function LiveView() {
  const { data: cameras = [] } = useQuery({ queryKey: QK.cameras, queryFn: () => fetchCameras() });
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const activeId = selectedId ?? cameras[0]?.id ?? null;
  const active = cameras.find((c) => c.id === activeId);

  return (
    <div className="live">
      <header className="live__header">
        <h1 className="live__title">Live</h1>
        <p className="live__sub">
          Annotierter MJPEG-Stream direkt aus dem Worker. Frame-Rate: ~10 fps, Latenz 1-2 s.
        </p>
      </header>

      {activeId ? (
        <figure className="live__frame">
          <img
            src={`/api/cameras/${activeId}/stream.mjpg?fps=10`}
            alt={`Live-Stream ${active?.name ?? activeId}`}
            className="live__img"
          />
          <figcaption className="live__caption">
            <span className="live__cam-name">{active?.name}</span>
            {active?.default_speed_limit_kmh != null && (
              <span className="live__limit mono">Limit {active.default_speed_limit_kmh} km/h</span>
            )}
          </figcaption>
        </figure>
      ) : (
        <div className="live__empty">
          <p>Keine Kamera konfiguriert.</p>
          <p>
            <a href="/cameras">Kamera hinzufügen →</a>
          </p>
        </div>
      )}

      {cameras.length > 1 && (
        <ul className="live__picker">
          {cameras.map((c) => (
            <li key={c.id}>
              <button
                className={c.id === activeId ? "live-picker live-picker--active" : "live-picker"}
                onClick={() => setSelectedId(c.id)}
              >
                <span className={`live-picker__dot live-picker__dot--${c.enabled ? "ok" : "down"}`} />
                {c.name}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
