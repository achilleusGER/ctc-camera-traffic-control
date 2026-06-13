// Violations — Log-Liste: jede Überschreitung als klickbare Zeile
// Bilder und Details erscheinen erst auf der Detailseite (/log/:id)

import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { fetchViolations, QK } from "../api/client";
import { classLabelDE, formatDateTime, formatNumber, formatSpeed } from "../lib/format";
import "./Violations.css";

export function Violations() {
  const { data: violations = [], isLoading } = useQuery({
    queryKey: QK.violations({ limit: 200 }),
    queryFn: () => fetchViolations({ limit: 200 }),
  });

  return (
    <div className="violations">
      <header className="violations__header">
        <h1 className="violations__title">Verstöße</h1>
        <p className="violations__sub">
          {formatNumber(violations.length)} dokumentierte Geschwindigkeitsüberschreitungen.
        </p>
      </header>

      {isLoading && <p className="muted">Lade…</p>}

      {!isLoading && violations.length === 0 && (
        <p className="violations__empty">Keine Verstöße in den letzten Tagen.</p>
      )}

      {!isLoading && violations.length > 0 && (
        <div className="vlog">
          <div className="vlog__head" aria-hidden="true">
            <span>Zeitpunkt</span>
            <span>Fahrzeug</span>
            <span>Tempo</span>
            <span>Überschr.</span>
            <span>Richtung</span>
            <span>Kennzeichen</span>
          </div>

          {violations.map((v) => {
            const delta = (v.speed_kmh ?? 0) - (v.speed_limit_kmh ?? 0);
            const hasPlate = v.plates && v.plates.length > 0;
            return (
              <Link key={v.id} to={`/log/${v.id}`} className="vlog__row">
                <span className="vlog__cell vlog__cell--time mono">
                  {formatDateTime(v.ts)}
                </span>
                <span className="vlog__cell">
                  {classLabelDE(v.vehicle_class)}
                </span>
                <span className="vlog__cell mono">
                  {formatSpeed(v.speed_kmh, 0)}
                  <span className="vlog__limit">
                    {" "}/ {formatNumber(v.speed_limit_kmh ?? 0, 0)}
                  </span>
                </span>
                <span className="vlog__cell">
                  <span className="vlog__delta mono">+{formatNumber(delta, 0)}</span>
                </span>
                <span className="vlog__cell vlog__cell--dir">
                  {v.direction}
                </span>
                <span className="vlog__cell vlog__cell--plate mono">
                  {hasPlate
                    ? v.plates.map((p) => p.plate_text).join(" · ")
                    : <span className="muted">—</span>}
                </span>
                <span className="vlog__arrow" aria-hidden="true">›</span>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
