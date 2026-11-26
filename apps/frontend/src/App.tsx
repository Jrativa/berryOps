import type { ReactNode } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import LoginPage from "@/modules/auth/ui/Login";
import { HomePage } from "@/modules/home/ui/home-page";
import { InventoryPage } from "@/modules/inventory/ui/inventory-page";
import { PlotDetailPage } from "@/modules/inventory/ui/plot-detail-page";
import { useAuthStore } from "@/modules/auth/application/authStore";

function RootRedirect() {
  const user = useAuthStore((s) => s.user);
  return <Navigate to={user ? "/home" : "/login"} replace />;
}

function Protected({ children }: { children: ReactNode }) {
  const user = useAuthStore((s) => s.user);
  return user ? children : <Navigate to="/login" replace />;
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<RootRedirect />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/home" element={<Protected><HomePage /></Protected>} />
        <Route path="/inventory" element={<Protected><InventoryPage /></Protected>} />
        <Route path="/inventory/plots/:id" element={<Protected><PlotDetailPage /></Protected>} />
        <Route path="*" element={<RootRedirect />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
