// ViolationDetail — Detailansicht eines einzelnen Vorfalls mit Beweisfotos

import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { fetchViolation, QK } from "../api/client";
import { classLabelDE, formatDateTime, formatNumber, formatSpeed } from "../lib/format";
import "./ViolationDetail.css";

export function ViolationDetail() {
  const { id } = useParams<{ id: string }>();
  const violationId = Number(id);

  const { data: v, isLoading, isError } = useQuery({
    queryKey: QK.violation(violationId),
    queryFn: () => fetchViolation(violationId),
    enabled: !isNaN(violationId),
  });

  if (isLoading) {
    return (
      <div className="vd">
        <Link to="/log" className="vd__back">← Zurück zum Log</Link>
        <p className="muted">Lade Vorfall…</p>
      </div>
    );
  }

  if (isError || !v) {
    return (
      <div className="vd">
        <Link to="/log" className="vd__back">← Zurück zum Log</Link>
        <p className="vd__error">Vorfall nicht gefunden.</p>
      </div>
    );
  }

  const delta = (v.speed_kmh ?? 0) - (v.speed_limit_kmh ?? 0);

  return (
    <div className="vd">
      <Link to="/log" className="vd__back">← Zurück zum Log</Link>

      <header className="vd__header">
        <div className="vd__speed-block">
          <span className="vd__speed mono">{formatSpeed(v.speed_kmh, 0)}</span>
          <span className="vd__delta mono">+{formatNumber(delta, 0)} km/h</span>
        </div>
        <div className="vd__meta">
          <p className="vd__time mono">{formatDateTime(v.ts)}</p>
          <p className="vd__class">{classLabelDE(v.vehicle_class)} · {v.direction}</p>
          <p className="vd__limit muted">
            Limit: {formatNumber(v.speed_limit_kmh ?? 0, 0)} km/h
          </p>
          {v.plates && v.plates.length > 0 && (
            <div className="vd__plates">
              {v.plates.map((p) => (
                <span key={p.id} className="vd__plate mono">{p.plate_text}</span>
              ))}
            </div>
          )}
        </div>
      </header>

      <section className="vd__section">
        <h2 className="vd__section-title">Beweisfotos</h2>
        {v.evidence_paths.length === 0 ? (
          <p className="muted">Keine Beweisfotos vorhanden.</p>
        ) : (
          <div className="vd__gallery">
            {v.evidence_paths.map((path, i) => (
              <img
                key={path}
                src={`/api/media/evidence/${path}?v=${v.id}`}
                alt={`Beweisfoto ${i + 1}`}
                className="vd__img"
                loading="lazy"
              />
            ))}
          </div>
        )}
      </section>

      <section className="vd__section">
        <h2 className="vd__section-title">Details</h2>
        <dl className="vd__dl">
          <dt>Vorfall-ID</dt>
          <dd className="mono">#{v.id}</dd>
          <dt>Zeitpunkt</dt>
          <dd className="mono">{formatDateTime(v.ts)}</dd>
          <dt>Kamera-ID</dt>
          <dd className="mono">{v.camera_id}</dd>
          <dt>Track-ID</dt>
          <dd className="mono">{v.track_id ?? "—"}</dd>
          <dt>Fahrzeugklasse</dt>
          <dd>{classLabelDE(v.vehicle_class)}</dd>
          <dt>Richtung</dt>
          <dd>{v.direction}</dd>
          <dt>Gemessene Geschwindigkeit</dt>
          <dd className="mono">{formatSpeed(v.speed_kmh, 1)}</dd>
          <dt>Geschwindigkeitslimit</dt>
          <dd className="mono">{formatNumber(v.speed_limit_kmh ?? 0, 0)} km/h</dd>
          <dt>Überschreitung</dt>
          <dd className="mono vd__detail-delta">+{formatNumber(delta, 0)} km/h</dd>
          {v.plates && v.plates.length > 0 && (
            <>
              <dt>Kennzeichen</dt>
              <dd className="mono">
                {v.plates.map((p) => (
                  <span key={p.id} className="vd__plate">{p.plate_text}</span>
                ))}
              </dd>
            </>
          )}
        </dl>
      </section>
    </div>
  );
}
