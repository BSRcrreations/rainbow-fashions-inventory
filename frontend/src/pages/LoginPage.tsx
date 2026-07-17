import { FormEvent, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { AlertCircle, LockKeyhole, Mail } from "lucide-react";
import { useAuth } from "../hooks/useAuth";

export default function LoginPage() {
  const { login, user } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("Rainbow@fashions.com");
  const [password, setPassword] = useState("Fashions123");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  if (user) return <Navigate to="/" replace />;

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      await login(email, password);
      navigate("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <div className="relative hidden flex-col justify-between bg-gradient-to-br from-primary-700 via-primary-800 to-primary-900 p-10 text-white lg:flex">
        <div>
          <div className="text-2xl font-bold tracking-tight">Rainbow Fashions</div>
          <div className="mt-1 text-sm font-medium text-primary-100">Inventory Management System</div>
        </div>
        <div className="max-w-md">
          <h2 className="text-3xl font-bold leading-tight">Manage your inventory with confidence</h2>
          <p className="mt-3 text-base font-medium text-primary-100">
            Track products, stock, purchases, and sales in one elegant dashboard built for growing retail businesses.
          </p>
        </div>
        <div className="text-xs font-medium text-primary-200">© {new Date().getFullYear()} Rainbow Fashions</div>
      </div>
      <div className="grid place-items-center bg-canvas px-4 py-10">
        <form onSubmit={handleSubmit} className="w-full max-w-sm rounded-2xl border border-line bg-surface p-7 shadow-elevated">
          <div className="mb-6 lg:hidden">
            <div className="text-2xl font-bold tracking-tight text-slate-950">Rainbow Fashions</div>
            <p className="text-sm font-medium text-slate-500">Inventory Management</p>
          </div>
          <div className="mb-6 hidden lg:block">
            <h1 className="text-2xl font-bold tracking-tight text-slate-950">Welcome back</h1>
            <p className="mt-1 text-sm font-medium text-slate-500">Sign in to your account</p>
          </div>
          <label className="mb-4 block">
            <span className="mb-1 block text-sm font-medium text-slate-700">Email</span>
            <div className="flex items-center rounded-xl border border-line bg-surface px-3 shadow-sm">
              <Mail size={16} className="text-slate-400" />
              <input
                className="focus-ring h-11 min-w-0 flex-1 border-0 bg-transparent px-2 outline-none"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                type="email"
                required
              />
            </div>
          </label>
          <label className="mb-4 block">
            <span className="mb-1 block text-sm font-medium text-slate-700">Password</span>
            <div className="flex items-center rounded-xl border border-line bg-surface px-3 shadow-sm">
              <LockKeyhole size={16} className="text-slate-400" />
              <input
                className="focus-ring h-11 min-w-0 flex-1 border-0 bg-transparent px-2 outline-none"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                type="password"
                required
              />
            </div>
          </label>
          {error ? <div className="mb-4 flex items-start gap-2 rounded-xl bg-rose-50 px-3 py-2 text-sm font-medium text-rose-700"><AlertCircle size={16} className="mt-0.5 shrink-0" />{error}</div> : null}
          <button className="focus-ring h-11 w-full rounded-xl bg-primary-700 text-sm font-bold text-white shadow-md hover:bg-primary-800 hover:shadow-lg active:scale-[0.99]" disabled={loading}>
            {loading ? "Signing in" : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
