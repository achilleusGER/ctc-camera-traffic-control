// Format-Helper: Zahlen, Datum, km/h (de_DE)

const fmtDate = new Intl.DateTimeFormat("de-DE", {
  day: "2-digit", month: "2-digit", year: "numeric",
  hour: "2-digit", minute: "2-digit", second: "2-digit",
});

const fmtTime = new Intl.DateTimeFormat("de-DE", {
  hour: "2-digit", minute: "2-digit", second: "2-digit",
});

const fmtDateShort = new Intl.DateTimeFormat("de-DE", {
  day: "2-digit", month: "2-digit", year: "numeric",
});

export function formatDateTime(iso: string | Date): string {
  const d = typeof iso === "string" ? new Date(iso) : iso;
  return fmtDate.format(d);
}

export function formatTime(iso: string | Date): string {
  const d = typeof iso === "string" ? new Date(iso) : iso;
  return fmtTime.format(d);
}

export function formatDateShort(iso: string | Date): string {
  const d = typeof iso === "string" ? new Date(iso) : iso;
  return fmtDateShort.format(d);
}

export function formatNumber(n: number, digits = 0): string {
  return new Intl.NumberFormat("de-DE", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(n);
}

export function formatSpeed(kmh: number | null | undefined, digits = 1): string {
  if (kmh == null) return "—";
  return `${formatNumber(kmh, digits)} km/h`;
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  return `${(bytes / 1024 / 1024 / 1024).toFixed(2)} GB`;
}

export function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${(seconds % 60).toFixed(0)}s`;
  return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
}

// Vehicle-Class → deutsch
export function classLabelDE(cls: string): string {
  const map: Record<string, string> = {
    person: "Person",
    bicycle: "Fahrrad",
    car: "PKW",
    motorcycle: "Motorrad",
    bus: "Bus",
    truck: "LKW",
  };
  return map[cls] ?? cls;
}

// Status-Dot-Farbe (für Kamera-Status-Tile)
export function statusColor(state: "ok" | "warn" | "down"): string {
  if (state === "ok") return "var(--color-ok)";
  if (state === "warn") return "var(--color-warn)";
  return "var(--color-danger)";
}
