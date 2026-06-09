// AppShell: N5 Floating Pill Nav (top-centered, blur backdrop) + Content + Ft5 Statement Footer.

import { Link, NavLink, Outlet } from "react-router-dom";
import { ErrorBoundary } from "./ErrorBoundary";
import "./Layout.css";

const navItems = [
  { to: "/", label: "Übersicht", end: true },
  { to: "/live", label: "Live" },
  { to: "/violations", label: "Verstöße" },
  { to: "/reports", label: "Reports" },
  { to: "/cameras", label: "Kameras" },
];

export function Layout() {
  return (
    <div className="layout">
      {/* N5 Floating Pill Nav */}
      <nav className="nav-pill" aria-label="Hauptnavigation">
        <Link to="/" className="nav-pill__brand">
          <span className="nav-pill__dot" />
          Hermes
        </Link>
        <ul className="nav-pill__links">
          {navItems.map((item) => (
            <li key={item.to}>
              <NavLink
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  isActive ? "nav-pill__link nav-pill__link--active" : "nav-pill__link"
                }
              >
                {item.label}
              </NavLink>
            </li>
          ))}
        </ul>
        <span className="nav-pill__time mono">
          {new Date().toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" })}
        </span>
      </nav>

      <main className="layout__main">
        <ErrorBoundary>
          <Outlet />
        </ErrorBoundary>
      </main>

      {/* Ft5 Statement Footer */}
      <footer className="footer-statement">
        <p className="footer-statement__line">
          Beobachtet. Gemessen. Dokumentiert.
        </p>
        <p className="footer-statement__meta">
          <span>Hermes-Trafficcontrol</span>
          <span className="footer-statement__dot">·</span>
          <span>Proxmox-LXC</span>
          <span className="footer-statement__dot">·</span>
          <span className="mono">v0.1.0</span>
        </p>
      </footer>
    </div>
  );
}
