// CameraAdmin — F4 Step sequence + CRUD

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { fetchCameras, fetchStreets, QK, api } from "../api/client";
import { formatNumber } from "../lib/format";
import "./CameraAdmin.css";

export function CameraAdmin() {
  const qc = useQueryClient();
  const camerasQ = useQuery({ queryKey: QK.cameras, queryFn: () => fetchCameras() });
  const streetsQ = useQuery({ queryKey: QK.streets, queryFn: () => fetchStreets() });

  const createCam = useMutation({
    mutationFn: (payload: { name: string; rtsp_url_low: string; street_id: number | null; default_speed_limit_kmh: number | null }) =>
      api.post("/cameras/", payload).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: QK.cameras }),
  });

  const toggleCam = useMutation({
    mutationFn: ({ id, enabled }: { id: number; enabled: boolean }) =>
      api.patch(`/cameras/${id}`, { enabled }).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: QK.cameras }),
  });

  const toggleAlpr = useMutation({
    mutationFn: ({ id, alpr_enabled }: { id: number; alpr_enabled: boolean }) =>
      api.patch(`/cameras/${id}`, { alpr_enabled }).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: QK.cameras }),
  });

  const deleteCam = useMutation({
    mutationFn: (id: number) => api.delete(`/cameras/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: QK.cameras }),
  });

  const createStreet = useMutation({
    mutationFn: (payload: { name: string; description?: string }) =>
      api.post("/streets/", payload).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: QK.streets }),
  });

  const deleteStreet = useMutation({
    mutationFn: (id: number) => api.delete(`/streets/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: QK.streets }),
  });

  const [form, setForm] = useState({
    name: "",
    rtsp_url_low: "",
    street_id: "" as string | number,
    default_speed_limit_kmh: 50,
  });

  const [streetForm, setStreetForm] = useState({ name: "", description: "" });

  // Aktiver Tab: 'cameras' (default) oder 'streets'. Kameras ist der
  // haeufigere Use-Case, deshalb zuerst. Tabs persistieren nicht
  // (kein localStorage) — nach Reload ist immer Kameras aktiv.
  const [tab, setTab] = useState<"cameras" | "streets">("cameras");

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name || !form.rtsp_url_low) return;
    createCam.mutate({
      name: form.name,
      rtsp_url_low: form.rtsp_url_low,
      street_id: form.street_id === "" ? null : Number(form.street_id),
      default_speed_limit_kmh: form.default_speed_limit_kmh,
    });
    setForm({ name: "", rtsp_url_low: "", street_id: "", default_speed_limit_kmh: 50 });
  };

  const onStreetSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!streetForm.name.trim()) return;
    createStreet.mutate({
      name: streetForm.name.trim(),
      description: streetForm.description.trim() || undefined,
    });
    setStreetForm({ name: "", description: "" });
  };

  return (
    <div className="cadmin">
      <header className="cadmin__header">
        <h1 className="cadmin__title">Verwaltung</h1>
        <p className="cadmin__sub">
          {formatNumber(camerasQ.data?.length ?? 0)} Kameras · {formatNumber(streetsQ.data?.length ?? 0)} Straßen
        </p>
      </header>

      <nav className="cadmin__tabs" role="tablist" aria-label="Verwaltung-Bereiche">
        <button
          role="tab"
          aria-selected={tab === "cameras"}
          className={`cadmin__tab${tab === "cameras" ? " cadmin__tab--active" : ""}`}
          onClick={() => setTab("cameras")}
        >
          Kameras
        </button>
        <button
          role="tab"
          aria-selected={tab === "streets"}
          className={`cadmin__tab${tab === "streets" ? " cadmin__tab--active" : ""}`}
          onClick={() => setTab("streets")}
        >
          Straßen
        </button>
      </nav>

      {tab === "cameras" ? (
        <>
      <ol className="steps">
        <li className="step">
          <span className="step__num">01</span>
          <h3 className="step__title">Kamera anlegen</h3>
          <p className="step__hint">RTSPS-URL (z. B. UniFi Protect Substream) und Tempolimit eintragen.</p>
        </li>
        <li className="step">
          <span className="step__num">02</span>
          <h3 className="step__title">Zähllinie zeichnen</h3>
          <p className="step__hint">Im Kalibrierungs-Tool pro Kamera eine Linie definieren.</p>
        </li>
        <li className="step">
          <span className="step__num">03</span>
          <h3 className="step__title">Kalibrieren</h3>
          <p className="step__hint">4 Punkte auf einer realen Rechteckfläche markieren + Maße in Metern.</p>
        </li>
        <li className="step">
          <span className="step__num">04</span>
          <h3 className="step__title">Worker starten</h3>
          <p className="step__hint"><code>systemctl enable --now traffic-worker@{`{id}`}</code></p>
        </li>
      </ol>

      <section className="cadmin__form-section">
        <h2 className="cadmin__section-title">Neue Kamera</h2>
        <form onSubmit={onSubmit} className="cadmin__form">
          <div className="cadmin__field">
            <label htmlFor="cam-name">Name</label>
            <input
              id="cam-name"
              type="text"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="z. B. Einfahrt Nord"
              required
            />
          </div>
          <div className="cadmin__field">
            <label htmlFor="cam-url">RTSPS-URL (Low-Substream)</label>
            <input
              id="cam-url"
              type="text"
              value={form.rtsp_url_low}
              onChange={(e) => setForm({ ...form, rtsp_url_low: e.target.value })}
              placeholder="rtsps://10.10.1.252:7441/..."
              required
            />
          </div>
          <div className="cadmin__field">
            <label htmlFor="cam-street">Straße</label>
            <select
              id="cam-street"
              value={form.street_id}
              onChange={(e) => setForm({ ...form, street_id: e.target.value })}
            >
              <option value="">(keine)</option>
              {streetsQ.data?.map((s) => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
          </div>
          <div className="cadmin__field">
            <label htmlFor="cam-limit">Tempolimit (km/h)</label>
            <input
              id="cam-limit"
              type="number"
              min={5}
              max={250}
              value={form.default_speed_limit_kmh}
              onChange={(e) => setForm({ ...form, default_speed_limit_kmh: Number(e.target.value) })}
            />
          </div>
          <button type="submit" className="cadmin__submit" disabled={createCam.isPending}>
            {createCam.isPending ? "Speichere…" : "Kamera anlegen"}
          </button>
        </form>
      </section>

      <section className="cadmin__list-section">
        <h2 className="cadmin__section-title">Vorhandene Kameras</h2>
        {camerasQ.data?.length === 0 && <p className="muted">Noch keine Kameras angelegt.</p>}
        <ul className="cadmin__list">
          {camerasQ.data?.map((c) => (
            <li key={c.id} className="cadmin__row">
              <span className={`cadmin__dot cadmin__dot--${c.enabled ? "ok" : "down"}`} />
              <div className="cadmin__row-info">
                <span className="cadmin__row-name">{c.name}</span>
                <span className="cadmin__row-url mono">{c.rtsp_url_low}</span>
                <span className="cadmin__row-meta">
                  {c.street_id && streetsQ.data?.find((s) => s.id === c.street_id)?.name}
                  {c.default_speed_limit_kmh != null && (
                    <> · Limit <span className="mono">{c.default_speed_limit_kmh} km/h</span></>
                  )}
                  {c.alpr_enabled && <> · ALPR an</>}
                </span>
              </div>
              <div className="cadmin__row-actions">
                <button
                  className="cadmin__toggle"
                  onClick={() => toggleCam.mutate({ id: c.id, enabled: !c.enabled })}
                >
                  {c.enabled ? "Deaktivieren" : "Aktivieren"}
                </button>
                <button
                  className={`cadmin__toggle${c.alpr_enabled ? " cadmin__toggle--alpr-on" : ""}`}
                  onClick={() => toggleAlpr.mutate({ id: c.id, alpr_enabled: !c.alpr_enabled })}
                  title="Kfz-Kennzeichen-Erkennung (DSGVO: nur mit Einwilligung aktivieren)"
                >
                  {c.alpr_enabled ? "ALPR an" : "ALPR aus"}
                </button>
                <button
                  className="cadmin__toggle cadmin__toggle--danger"
                  onClick={() => {
                    if (confirm(`Kamera "${c.name}" wirklich löschen?`)) {
                      deleteCam.mutate(c.id);
                    }
                  }}
                >
                  Löschen
                </button>
              </div>
            </li>
          ))}
        </ul>
      </section>
        </>
      ) : (
        <>
      <section className="cadmin__form-section">
        <h2 className="cadmin__section-title">Neue Straße</h2>
        <form onSubmit={onStreetSubmit} className="cadmin__form">
          <div className="cadmin__field">
            <label htmlFor="street-name">Name</label>
            <input
              id="street-name"
              type="text"
              value={streetForm.name}
              onChange={(e) => setStreetForm({ ...streetForm, name: e.target.value })}
              placeholder="z. B. Bahnhofstraße"
              required
            />
          </div>
          <div className="cadmin__field">
            <label htmlFor="street-desc">Beschreibung (optional)</label>
            <input
              id="street-desc"
              type="text"
              value={streetForm.description}
              onChange={(e) => setStreetForm({ ...streetForm, description: e.target.value })}
              placeholder="z. B. Abschnitt 12–18, beide Richtungen"
            />
          </div>
          <button type="submit" className="cadmin__submit" disabled={createStreet.isPending}>
            {createStreet.isPending ? "Speichere…" : "Straße anlegen"}
          </button>
        </form>
      </section>

      <section className="cadmin__list-section">
        <h2 className="cadmin__section-title">Vorhandene Straßen</h2>
        {streetsQ.data?.length === 0 && <p className="muted">Noch keine Straßen angelegt.</p>}
        <ul className="cadmin__list">
          {streetsQ.data?.map((s) => {
            const camCount = camerasQ.data?.filter((c) => c.street_id === s.id).length ?? 0;
            return (
              <li key={s.id} className="cadmin__row">
                <span className="cadmin__dot cadmin__dot--ok" />
                <div className="cadmin__row-info">
                  <span className="cadmin__row-name">{s.name}</span>
                  {s.description && <span className="cadmin__row-meta">{s.description}</span>}
                  <span className="cadmin__row-meta">
                    {camCount} {camCount === 1 ? "Kamera" : "Kameras"}
                  </span>
                </div>
                <button
                  className="cadmin__toggle cadmin__toggle--danger"
                  onClick={() => {
                    if (camCount > 0) {
                      alert(
                        `Straße "${s.name}" hat noch ${camCount} Kamera(s). ` +
                        `Bitte erst Kameras löschen oder Straße wechseln.`,
                      );
                      return;
                    }
                    if (confirm(`Straße "${s.name}" wirklich löschen?`)) {
                      deleteStreet.mutate(s.id);
                    }
                  }}
                >
                  Löschen
                </button>
              </li>
            );
          })}
        </ul>
      </section>
        </>
      )}
    </div>
  );
}
