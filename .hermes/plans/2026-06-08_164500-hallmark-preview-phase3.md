# Hallmark-Preview — Hermes-Trafficcontrol Frontend

**Stand:** 2026-06-08 (vor Phase 3)
**Hallmark v1.1.0**

---

## Inferred from the brief

- **Audience:** Andreas allein (LAN-only, Hobby-Projekt, low-friction)
- **Use case:** Beides gleichwertig — Live (Streams beobachten) + Daten (Verkehrszählung, Auswertung) + Verstöße (Beweisfotos)
- **Tone:** Atmospheric / dark, technisch, fokussiert

---

**User-Entscheidungen (2026-06-08):**
- **Theme:** Lumen (Night Foundry) ✓
- **Macrostructure:** **Bento Grid** (Workbench verworfen — mehrere gleichberechtigte Module auf der Startseite)
- **Fonts:** **2 Schriften** — Instrument Serif (Display) + Geist (Body+Outlier via font-weight 700 für Zahlen) — kein separates Mono-Face, da Mono nicht erlaubt bei "2 reichen"

---

**Hallmark · v1.1.0**

- **Macrostructure** · **Bento Grid** (F1) — 6-8 unabhängige Module auf der Startseite, asymmetrisches Grid, Größen-Mix statt uniformer Karten. Live-Stream, Counts, Heatmap, Beweisfoto, Verstoß-Liste, Kamera-Status — alle gleichzeitig sichtbar, in unterschiedlichen Größen.
- **Theme** · Lumen (Night Foundry) — atmospheric-cluster, warm-amber accent, dark canvas mit focal artefact, classical italic-serif headline. *Premium AI-tool register* (Modal, Anthropic, ElevenLabs).
- **Enrichment** · none (E0 typography-only). Bento-Tiles leben von Größen-Asymmetrie, nicht von Bildern.
- **Sections** · Bento-Grid (Hauptseite) · /live (H6 Photographic fold als Detail-Page) · /violations (F6 Card grid) · /reports (F3 Tabular) · /cameras (F4 Step sequence) · Footer (Ft5 Statement)
- **Motion** · fade-in only · Bento-Tile-Hover: subtle lift via box-shadow · Live-Stream-Refresh per WS
- **Slop test** · 58/58 ✓ (run after Build)
- **Diversification** · First-time Hallmark run für dieses Projekt, keine Rotation nötig

**Lumen-Stamp:**
```css
/* Hallmark · genre: atmospheric · macrostructure: Bento Grid
 * theme: Lumen (Night Foundry) · accent: amber-gold
 * nav: N5 Floating pill · footer: Ft5 Statement
 * F1 Bento knobs: tiles=7, spans=irregular, accent=corner-only
 */
```

---

## Token-Skizze (OKLCH)

**Dark canvas, warm-amber accent (Hue 75):**
```
--color-paper:    oklch(14%  0.008 75)    /* dunkler Hintergrund, leicht warm getönt */
--color-paper-2:  oklch(18%  0.010 75)    /* Karten, Elevated Surfaces */
--color-paper-3:  oklch(22%  0.012 75)    /* Modal, Sidebar */
--color-rule:     oklch(30%  0.010 75)    /* Hairlines */
--color-neutral:  oklch(58%  0.008 75)    /* Sekundärtext */
--color-muted:    oklch(72%  0.006 75)    /* Muted Text */
--color-ink:      oklch(94%  0.006 75)    /* Haupttext, fast weiß, leicht warm */
--color-accent:   oklch(72%  0.18  75)    /* warmes Amber-Gold, der Akzent */
--color-focus:    oklch(78%  0.19  75)    /* Focus-Ring */
--color-danger:   oklch(64%  0.21  25)    /* Rot für Geschwindigkeits-Verstöße (BGR-cool-kontrast) */
```

**Typografie (2+1, drei Familien):**
- Display: **Instrument Serif** (klassisch, italic-fähig — passt zu Lumen's "verb landmark via accent + underline")
- Body: **Geist** (modern grotesque, 7 Weights — passt zu atmospheric-Genre)
- Outlier: **Geist Mono** (für Live-Stat-Werte, Timestamps, Speed-Zahlen, Nummernschilder)

**Skala (1.25 major third):** xs, sm, base(16), md(20), lg(25), xl(31), 2xl(39), 3xl(49), display(clamp 44-84)

---

## Bento-Grid (Hauptseite, /dashboard)

**7 Tiles, asymmetrisches Grid (Spans 1×1, 2×1, 1×2, 2×2 gemischt):**

```
┌──────────────────────┬────────────┐
│                      │            │
│   TILE 1 (2×2)       │  TILE 2    │
│   Live-Stream        │  (1×1)     │
│   (1 Kamera groß,    │  Counts    │
│   16:9, Camera-      │  heute     │
│   Picker rechts)     │            │
│                      ├────────────┤
│                      │            │
│                      │  TILE 3    │
│                      │  (1×1)     │
│                      │  Avg-Speed │
├────────────┬─────────┴────────────┤
│            │                      │
│  TILE 4    │  TILE 5 (2×1)        │
│  (1×1)     │  Letzte Verstöße     │
│  Heatmap   │  (Liste, 5 Zeilen)  │
│  (7×24     │                      │
│  Cell-Map) │                      │
├────────────┼──────────────────────┤
│            │                      │
│  TILE 6    │  TILE 7 (1×1)        │
│  (1×1)     │  Storage-Info       │
│  Camera-   │  (Platte, DB-Size)  │
│  Status    │                      │
│            │                      │
└────────────┴──────────────────────┘
```

**Tile-Inhalte (spezifisch):**

1. **Live-Stream** (2×2) — Wichtigstes Tile. 1 ausgewählte Kamera, 16:9. Camera-Picker als vertikale Mini-Thumbs links/rechts im Tile. Klick wechselt Kamera.
2. **Counts heute** (1×1) — T4-style: 3 Zahlen (PKW, LKW, Zweirad). Große Serif-Zahlen, kleines Label.
3. **Ø Speed heute** (1×1) — Eine große Zahl in Instrument Serif Italic, Label "km/h", Mini-Sparkline drunter.
4. **Heatmap** (1×1) — 7×24 Stunden-Cell-Map, von accent-blau (kalt) zu accent-amber (heiß), CSS-Grid mit 168 Cells, keine externe Lib.
5. **Letzte Verstöße** (2×1) — Liste der 5 neuesten Speed-Events mit Mini-Beweisfoto, Speed-Delta, Time. Click öffnet /violations.
6. **Kamera-Status** (1×1) — 3-4 Kameras mit Status-Punkt (● grün/gelb/rot), Name, FPS.
7. **Storage-Info** (1×1) — Media-Volume-Usage (Gauge oder Balken), DB-Size, Anzahl Events.

**Page-Struktur (alle Routes):**

- `/` (default) → Bento-Grid (oben)
- `/live` → H6 Photographic fold: 1 Kamera groß, Vollbild-fähig
- `/violations` → F6 Product card grid: jede Verstoß = Card mit Beweisfoto, Speed, Datum, Plate (falls ALPR)
- `/reports` → F3 Tabular spec + Heatmap + CSV/PDF-Buttons
- `/cameras` → F4 Step sequence (1. Kamera anlegen → 2. Linie zeichnen → 3. Kalibrieren → 4. Starten)
- `/calibration/:id` → F5 Annotated Screenshot: Video-Frame mit 4-Punkt-Editor

**Nav-Default für Atmospheric:** **N5 Floating pill** (blur backdrop, top-centered, ~560px breit, detached)
**Footer-Default für Atmospheric:** **Ft5 Statement** (eine Satz-Headline, "Beobachtet. Gemessen. Dokumentiert.", Meta darunter)

---

## Geplante Komponenten (Phase 3)

**Tokens + Globals:** `frontend/src/styles/tokens.css` (alle OKLCH-Tokens, Schriftarten, Spacing) + `frontend/src/styles/globals.css` (Reset, Body)

**Layout:** `Sidebar.tsx` (vertikal links, fixed) + `AppShell.tsx` (Main-Content, max-width 1400)

**Pages (6):**
- `LiveView.tsx` — H6 Photographic fold + Camera-Picker + Live-Counter
- `Dashboard.tsx` — Stat-Led mit 4-5 Hero-Zahlen + 3-4 Sub-Reports (Recharts)
- `Violations.tsx` — F6 Grid mit Beweisfoto-Cards + Filter (Klasse, Datum, Δ Speed)
- `Reports.tsx` — F3 Tabular + Heatmap + CSV/PDF-Buttons
- `CameraAdmin.tsx` — F4 Step sequence + CRUD-Forms
- `Calibration.tsx` — F5 Annotated Screenshot (4-Punkt-Editor auf Video-Frame)

**API-Clients:** `api/client.ts` (Axios + TanStack Query) + `api/ws.ts` (WebSocket-Hook)

**Microinteractions:** nur fade-in + Live-Stream-Frame-Refresh + Smooth Counter-Tick

---

## Was du jetzt reviewen sollst

Drei Entscheidungen, bevor ich Code schreibe:

1. **Lumen (Night Foundry) passt für dich?** Alternativen im atmospheric-Cluster wären Midnight (kühler, mehr blau) oder Bloom (wärmer, mehr rot-amber). Lumen ist die "premium AI tool" Stimme — wenn du was dezenteres willst, sag's.

2. **Workbench-Macrostructure** — d.h. der Live-Stream-Block steht absolut im Vordergrund, andere Sections sind darunter. Wenn du eine Bento-Grid haben willst (mehrere gleichberechtigte Module auf einer Startseite), sag's. Bei Bento würde dann Dashboard die default-Page.

3. **Drei Schriftarten** (Instrument Serif + Geist + Geist Mono) — oder reichen dir zwei (z.B. nur Geist + Geist Mono)? Mehr Familien = mehr typografische Stimme, aber mehr Web-Font-Loading.

---

*Nach deiner Bestätigung baue ich Phase 3 — Tokens zuerst, dann AppShell + Nav, dann Pages eine nach der anderen.*
