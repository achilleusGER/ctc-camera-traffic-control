// App.tsx — Router, TanStack Query, Layout

import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { queryClient } from "./api/client";
import { Layout } from "./components/Layout";
import { Dashboard } from "./pages/Dashboard";
import { LiveView } from "./pages/LiveView";
import { Violations } from "./pages/Violations";
import { Reports } from "./pages/Reports";
import { CameraAdmin } from "./pages/CameraAdmin";
import { Calibration } from "./pages/Calibration";
import "./styles/globals.css";

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="live" element={<LiveView />} />
            <Route path="violations" element={<Violations />} />
            <Route path="reports" element={<Reports />} />
            <Route path="cameras" element={<CameraAdmin />} />
            <Route path="calibration" element={<Navigate to="/cameras" replace />} />
            <Route path="calibration/:id" element={<Calibration />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
