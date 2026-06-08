// WebSocket-Hook für Live-Events

import { useEffect, useRef, useState } from "react";
import type { LiveEvent } from "../api/types";

const WS_BASE = (() => {
  const base = import.meta.env.VITE_API_BASE || "";
  if (base.startsWith("http")) {
    return base.replace(/^http/, "ws");
  }
  // Relativer Pfad: gleicher Host wie Frontend
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${window.location.host}`;
})();

export interface UseLiveEventsOptions {
  onEvent?: (ev: LiveEvent) => void;
}

export function useLiveEvents({ onEvent }: UseLiveEventsOptions = {}): {
  connected: boolean;
  lastEvent: LiveEvent | null;
} {
  const [connected, setConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<LiveEvent | null>(null);
  const handlerRef = useRef(onEvent);
  handlerRef.current = onEvent;

  useEffect(() => {
    const url = `${WS_BASE}/ws`;
    let ws: WebSocket | null = null;
    let retry: number | null = null;

    const connect = () => {
      ws = new WebSocket(url);
      ws.onopen = () => setConnected(true);
      ws.onclose = () => {
        setConnected(false);
        // Reconnect nach 3s
        retry = window.setTimeout(connect, 3000);
      };
      ws.onerror = () => ws?.close();
      ws.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data) as LiveEvent;
          if (data.type === "event") {
            setLastEvent(data);
            handlerRef.current?.(data);
          }
        } catch {
          // ignore malformed
        }
      };
    };

    connect();
    return () => {
      if (retry) clearTimeout(retry);
      ws?.close();
    };
  }, []);

  return { connected, lastEvent };
}
