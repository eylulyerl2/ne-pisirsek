import { Link, Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { RequireAuth } from "./components/RequireAuth";
import { LoginPage, RegisterPage } from "./pages/AuthPages";
import { FamiliesPage } from "./pages/FamiliesPage";
import { FamilyDetailPage } from "./pages/FamilyDetailPage";
import { JoinPage } from "./pages/JoinPage";
import { MealsPage } from "./pages/MealsPage";
import { PlanPage } from "./pages/PlanPage";
import { PreferencesPage } from "./pages/PreferencesPage";
import { ResetPasswordPage } from "./pages/ResetPasswordPage";
import { ShoppingPage } from "./pages/ShoppingPage";

function NotFound() {
  return (
    <div className="auth-wrap">
      <div className="card auth-card" style={{ textAlign: "center" }}>
        <h1>Sayfa bulunamadı</h1>
        <p className="sub">Aradığınız sayfa taşınmış veya hiç var olmamış olabilir.</p>
        <Link className="btn btn-primary" to="/plan">
          Haftalık plana dön
        </Link>
      </div>
    </div>
  );
}

export function App() {
  return (
    <Routes>
      <Route path="/giris" element={<LoginPage />} />
      <Route path="/kayit" element={<RegisterPage />} />
      <Route path="/katil" element={<JoinPage />} />
      <Route path="/sifre-sifirla" element={<ResetPasswordPage />} />
      <Route
        element={
          <RequireAuth>
            <Layout />
          </RequireAuth>
        }
      >
        <Route index element={<Navigate to="/plan" replace />} />
        <Route path="/plan" element={<PlanPage />} />
        <Route path="/alisveris" element={<ShoppingPage />} />
        <Route path="/aile" element={<FamiliesPage />} />
        <Route path="/aile/:familyId" element={<FamilyDetailPage />} />
        <Route path="/yemekler" element={<MealsPage />} />
        <Route path="/tercihler" element={<PreferencesPage />} />
      </Route>
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
