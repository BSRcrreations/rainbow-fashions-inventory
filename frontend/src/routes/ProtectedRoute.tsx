import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

export default function ProtectedRoute() {
  const { user, loading } = useAuth();
  if (loading) {
    return <div className="grid min-h-screen place-items-center bg-slate-50 text-sm text-slate-600">Loading</div>;
  }
  return user ? <Outlet /> : <Navigate to="/login" replace />;
}
