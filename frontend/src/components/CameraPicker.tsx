// CameraPicker — Drop-Down-Liste der Kameras mit Status-Dot.
//
// Wird in LiveView + Calibration benutzt. Der Parent verwaltet den
// ausgewaehlten Wert via useState (oder URL-Param, siehe Calibration).
//
// Bewusst KEIN useSearchParams — der Parent hat die Kontrolle, das macht
// die Komponente wiederverwendbar in beiden Kontexten (Page-Local-State
// in Live, URL-Param in Calibration).

import { fetchCameras, QK } from "../api/client";
import { useQuery } from "@tanstack/react-query";
import "./CameraPicker.css";

type Props = {
  value: number | null;
  onChange: (cameraId: number) => void;
  /** Optional: leere Option "Keine Auswahl" anzeigen. */
  allowEmpty?: boolean;
  /** Label fuer die leere Option, default "— Kamera waehlen —". */
  emptyLabel?: string;
};

export function CameraPicker({
  value,
  onChange,
  allowEmpty = false,
  emptyLabel = "— Kamera wählen —",
}: Props) {
  const { data: cameras = [] } = useQuery({
    queryKey: QK.cameras,
    queryFn: () => fetchCameras(),
  });

  if (cameras.length === 0) {
    return (
      <p className="cam-picker__empty">
        Keine Kamera konfiguriert. <a href="/cameras">Kamera anlegen →</a>
      </p>
    );
  }

  return (
    <select
      className="cam-picker"
      value={value ?? ""}
      onChange={(e) => onChange(Number(e.target.value))}
    >
      {allowEmpty && <option value="">{emptyLabel}</option>}
      {cameras.map((c) => (
        <option key={c.id} value={c.id}>
          {c.enabled ? "●" : "○"} {c.name}
          {c.street_id ? "" : " (keine Straße)"}
        </option>
      ))}
    </select>
  );
}
