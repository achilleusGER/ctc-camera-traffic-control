// Violations — F6 Product card grid: jede Verstoß = Card

import { useQuery } from "@tanstack/react-query";
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

      <div className="violations__grid">
        {violations.map((v) => {
          const delta = (v.speed_kmh ?? 0) - (v.speed_limit_kmh ?? 0);
          const evidence = v.evidence_paths[0];
          return (
            <article key={v.id} className="v-card">
              <div className="v-card__img-wrap">
                {evidence ? (
                  <img src={`/api/media/evidence/${evidence}`} alt="" className="v-card__img" />
                ) : (
                  <div className="v-card__img-empty">Kein Beweisfoto</div>
                )}
                <span className="v-card__delta mono">+{formatNumber(delta, 0)}</span>
              </div>
              <div className="v-card__body">
                <div className="v-card__speed">
                  <span className="v-card__speed-value mono">{formatSpeed(v.speed_kmh, 0)}</span>
                  <span className="v-card__speed-limit mono">
                    Limit {formatNumber(v.speed_limit_kmh ?? 0, 0)}
                  </span>
                </div>
                <div className="v-card__meta">
                  <span>{classLabelDE(v.vehicle_class)}</span>
                  <span className="v-card__dir">· {v.direction}</span>
                </div>
                <div className="v-card__time mono">{formatDateTime(v.ts)}</div>
                {v.plates && v.plates.length > 0 && (
                  <div className="v-card__plate mono">
                    {v.plates.map((p) => p.plate_text).join(" · ")}
                  </div>
                )}
              </div>
            </article>
          );
        })}
      </div>
    </div>
  );
}
