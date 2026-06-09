// ErrorBoundary — fängt Render-Crashes in Sub-Trees ab.
//
// Wenn eine Page z.B. eine undefined-Access macht oder ein Bug in der
// TSX-Logik, crasht normalerweise der ganze React-Tree und der User
// sieht eine schwarze Seite. Mit ErrorBoundary zeigt die Page stattdessen
// eine hilfreiche Fehlermeldung + Reload-Button. Nav + Footer bleiben
// stehen, der User kann auf eine andere Page navigieren.
//
// Bewusst KEIN Toast-System (zu gross, LAN-Tool). Bewusst KEIN Sentry
// o.ä. (kein externer Service). Fehler werden in der Console geloggt
// (Browser DevTools), das reicht fürs Debugging.

import { Component, type ErrorInfo, type ReactNode } from "react";
import "./ErrorBoundary.css";

type Props = { children: ReactNode };
type State = { error: Error | null };

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    // eslint-disable-next-line no-console
    console.error("[ErrorBoundary]", error, info);
  }

  render(): ReactNode {
    if (this.state.error) {
      return (
        <div className="errbox">
          <h1 className="errbox__title">Etwas ist schiefgelaufen</h1>
          <p className="errbox__sub">
            Die Seite hat einen Render-Fehler verursacht. Die App läuft weiter — du
            kannst die Seite neu laden oder eine andere öffnen.
          </p>
          <pre className="errbox__trace">{this.state.error.message}</pre>
          <button
            className="errbox__btn"
            onClick={() => {
              this.setState({ error: null });
              // kleiner Reload, der Cache-Buster hilft nicht — der Fehler kommt aus dem JS, nicht aus dem HTML
              window.location.reload();
            }}
          >
            Erneut versuchen
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
