import { Link, Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { routeAllowed } from "./permissions";

export default function ProtectedRoute() {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) {
    return <div className="grid min-h-screen place-items-center bg-slate-50 text-sm text-slate-600">Loading</div>;
  }
  if (!user) return <Navigate to="/login" replace />;
  if (!routeAllowed(location.pathname, user.role)) return <div className="mx-auto max-w-xl space-y-4 p-8"><h1 className="text-2xl font-bold">This page needs a different permission</h1><p>Ask the owner if you need access to this task.</p><Link to="/" className="inline-flex min-h-12 items-center rounded-lg bg-primary-700 px-5 font-semibold text-white">Back to Dashboard</Link></div>;
  return <Outlet />;
}
