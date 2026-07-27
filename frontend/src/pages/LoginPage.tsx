import { FormEvent, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { LockKeyhole, Mail } from "lucide-react";
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
    <div className="grid min-h-screen place-items-center bg-background px-4">
      <form onSubmit={handleSubmit} className="w-full max-w-sm rounded-md border border-line bg-white p-6 shadow-sm">
        <div className="mb-6">
          <h1 className="text-2xl font-semibold text-slate-950">Rainbow fashions</h1>
          <p className="mt-1 text-sm text-slate-500">Inventory Management</p>
        </div>
        <label className="mb-4 block">
          <span className="mb-1 block text-sm font-medium text-slate-700">Email</span>
          <div className="flex items-center rounded-md border border-line bg-white px-3">
            <Mail size={16} className="text-slate-400" />
            <input
              className="focus-ring h-10 min-w-0 flex-1 border-0 px-2 outline-none"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              type="email"
              required
            />
          </div>
        </label>
        <label className="mb-4 block">
          <span className="mb-1 block text-sm font-medium text-slate-700">Password</span>
          <div className="flex items-center rounded-md border border-line bg-white px-3">
            <LockKeyhole size={16} className="text-slate-400" />
            <input
              className="focus-ring h-10 min-w-0 flex-1 border-0 px-2 outline-none"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              type="password"
              required
            />
          </div>
        </label>
        {error ? <div className="mb-4 rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</div> : null}
        <button className="focus-ring h-10 w-full rounded-md bg-teal-700 text-sm font-semibold text-white hover:bg-teal-800" disabled={loading}>
          {loading ? "Signing in" : "Sign in"}
        </button>
      </form>
    </div>
  );
}
