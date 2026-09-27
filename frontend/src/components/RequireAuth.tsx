import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { Spinner } from "./Feedback";

export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return <Spinner label="Oturum kontrol ediliyor" />;
  if (!user) return <Navigate to="/giris" replace state={{ from: location.pathname + location.search }} />;
  return <>{children}</>;
}
