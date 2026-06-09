// LiveView — H6 Photographic fold: 1 Kamera groß, Kamera-Picker
//
// Wenn der Worker fuer die gewaehlte Kamera nicht laeuft, kommt kein
// Frame in Redis und der Stream bleibt schwarz. Wir zeigen dann einen
// klaren Hinweis mit dem passenden systemctl-Befehl, statt ein
// nichtssagendes "Kein Bild" zu zeigen.

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { fetchCameras, QK } from "../api/client";
import "./LiveView.css";

export function LiveView() {
  const { data: cameras = [] } = useQuery({ queryKey: QK.cameras, queryFn: () => fetchCameras() });
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [streamOk, setStreamOk] = useState(true);
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

      {activeId && active ? (
        <>
          <figure className="live__frame">
            <img
              src={`/api/cameras/${activeId}/stream.mjpg?fps=10&t=${Date.now()}`}
              alt={`Live-Stream ${active.name}`}
              className="live__img"
              onLoad={() => setStreamOk(true)}
              onError={() => setStreamOk(false)}
            />
            <figcaption className="live__caption">
              <span className="live__cam-name">{active.name}</span>
              {active.default_speed_limit_kmh != null && (
                <span className="live__limit mono">Limit {active.default_speed_limit_kmh} km/h</span>
              )}
            </figcaption>
          </figure>

          {!streamOk && (
            <div className="live__warn">
              <p><strong>Kein Bild.</strong> Wahrscheinlich läuft der Worker für diese Kamera nicht.</p>
              <p className="mono">
                sudo systemctl status traffic-worker@{activeId}
              </p>
              <p>Starten mit:</p>
              <p className="mono">
                sudo systemctl enable --now traffic-worker@{activeId}
              </p>
            </div>
          )}
        </>
      ) : (
        <div className="live__empty">
          <p>Keine Kamera konfiguriert.</p>
          <p>
            <a href="/cameras">Kamera hinzufügen →</a>
          </p>
        </div>
      )}

      {cameras.length > 0 && (
        <div className="live__picker-wrap">
          <label className="live__picker-label">Kamera:</label>
          <select
            className="live__picker"
            value={activeId ?? ""}
            onChange={(e) => {
              setSelectedId(Number(e.target.value));
              setStreamOk(true);
            }}
          >
            {cameras.map((c) => (
              <option key={c.id} value={c.id}>
                {c.enabled ? "●" : "○"} {c.name}
                {c.street_id ? "" : " (keine Straße)"}
              </option>
            ))}
          </select>
        </div>
      )}
    </div>
  );
}
