// Reports — F3 Tabular spec + Heatmap + CSV/PDF-Export

import { useQuery } from "@tanstack/react-query";
import { Fragment, useState } from "react";
import { fetchHeatmap, fetchSpeedHistogram, fetchCountsToday, QK } from "../api/client";
import { classLabelDE, formatDateTime, formatNumber } from "../lib/format";
import "./Reports.css";

type Range = "24h" | "7d" | "30d";

const RANGE_PRESETS: Record<Range, { since: Date; until: Date }> = {
  "24h": { since: new Date(Date.now() - 24 * 3600 * 1000), until: new Date() },
  "7d":  { since: new Date(Date.now() - 7 * 24 * 3600 * 1000), until: new Date() },
  "30d": { since: new Date(Date.now() - 30 * 24 * 3600 * 1000), until: new Date() },
};

export function Reports() {
  const [rangeKey, setRangeKey] = useState<Range>("7d");
  const range = RANGE_PRESETS[rangeKey];

  const heatmapQ = useQuery({
    queryKey: QK.heatmap({ since: range.since.toISOString(), until: range.until.toISOString() }),
    queryFn: () => fetchHeatmap({ since: range.since.toISOString(), until: range.until.toISOString() }),
  });
  const histQ = useQuery({
    queryKey: QK.speedHistogram({ since: range.since.toISOString(), until: range.until.toISOString() }),
    queryFn: () => fetchSpeedHistogram({ since: range.since.toISOString(), until: range.until.toISOString() }),
  });
  const countsQ = useQuery({ queryKey: QK.countsToday(), queryFn: () => fetchCountsToday() });

  return (
    <div className="reports">
      <header className="reports__header">
        <h1 className="reports__title">Reports</h1>
        <p className="reports__sub">
          Zeitraum: {formatDateTime(range.since)} – {formatDateTime(range.until)}
        </p>
      </header>

      <div className="reports__tabs">
        {(Object.keys(RANGE_PRESETS) as Range[]).map((k) => (
          <button
            key={k}
            className={k === rangeKey ? "reports__tab reports__tab--active" : "reports__tab"}
            onClick={() => setRangeKey(k)}
          >
            {k === "24h" ? "24 Stunden" : k === "7d" ? "7 Tage" : "30 Tage"}
          </button>
        ))}
        <div className="reports__tabs-spacer" />
        <a className="reports__export" href={`/api/reports/export.csv?since=${range.since.toISOString()}&until=${range.until.toISOString()}`} download>
          CSV
        </a>
        <a className="reports__export" href={`/api/reports/export.pdf?since=${range.since.toISOString()}&until=${range.until.toISOString()}`} download>
          PDF
        </a>
      </div>

      {/* F3 Tabular: Counts-by-Class */}
      <section className="reports__section">
        <h2 className="reports__section-title">Counts nach Klasse</h2>
        <table className="spec">
          <thead>
            <tr><th>Klasse</th><th className="num">Anzahl</th><th className="num">Anteil</th></tr>
          </thead>
          <tbody>
            {(() => {
              const data = countsQ.data ?? [];
              const total = data.reduce((s, c) => s + c.count, 0) || 1;
              return data.map((c) => (
                <tr key={c.vehicle_class}>
                  <td>{classLabelDE(c.vehicle_class)}</td>
                  <td className="num mono">{formatNumber(c.count)}</td>
                  <td className="num mono">{((c.count / total) * 100).toFixed(1)} %</td>
                </tr>
              ));
            })()}
          </tbody>
        </table>
      </section>

      {/* Heatmap: Wochentag x Stunde */}
      <section className="reports__section">
        <h2 className="reports__section-title">Heatmap (Wochentag × Stunde)</h2>
        <div className="reports__heatmap">
          <div className="reports__heatmap-grid">
            <div className="reports__heatmap-corner" />
            {Array.from({ length: 24 }).map((_, h) => (
              <div key={h} className="reports__heatmap-hlabel mono">{h}</div>
            ))}
            {Array.from({ length: 7 }).map((_, wd) => (
              <Fragment key={wd}>
                <div className="reports__heatmap-wlabel">
                  {["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"][wd]}
                </div>
                {Array.from({ length: 24 }).map((_, h) => {
                  const cell = heatmapQ.data?.find((c) => c.weekday === wd && c.hour === h);
                  const count = cell?.count ?? 0;
                  const max = Math.max(1, ...(heatmapQ.data?.map((c) => c.count) ?? [1]));
                  const intensity = count / max;
                  return (
                    <div
                      key={`cell-${wd}-${h}`}
                      className="reports__heatmap-cell"
                      style={{
                        background: intensity === 0
                          ? "var(--heat-0)"
                          : intensity < 0.33 ? "var(--heat-1)"
                          : intensity < 0.66 ? "var(--heat-2)"
                          : "var(--heat-3)",
                      }}
                      title={`${["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"][wd]} ${h}:00 — ${count}`}
                    />
                  );
                })}
              </Fragment>
            ))}
          </div>
        </div>
      </section>

      {/* Speed-Histogramm */}
      <section className="reports__section">
        <h2 className="reports__section-title">Geschwindigkeitsverteilung</h2>
        <div className="reports__histogram">
          {(() => {
            const data = histQ.data ?? [];
            const max = Math.max(1, ...data.map((b) => b.count));
            return data.map((b) => {
              const h = (b.count / max) * 100;
              return (
                <div key={b.bin_start_kmh} className="hist-bar" title={`${b.bin_start_kmh}-${b.bin_end_kmh} km/h: ${b.count}`}>
                  <div className="hist-bar__fill" style={{ height: `${h}%` }} />
                  <div className="hist-bar__label mono">{b.bin_start_kmh}</div>
                </div>
              );
            });
          })()}
        </div>
      </section>
    </div>
  );
}
