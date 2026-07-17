import { BarChart3, Boxes, ClipboardList, Layers3, LogOut, PackageSearch, Tags } from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

const navItems = [
  { to: "/", label: "Dashboard", icon: BarChart3 },
  { to: "/products", label: "Products", icon: PackageSearch },
  { to: "/categories", label: "Categories", icon: Layers3 },
  { to: "/brands", label: "Brands", icon: Tags },
  { to: "/purchases", label: "Purchases", icon: ClipboardList },
  { to: "/stock", label: "Stock", icon: Boxes }
];

export default function AppLayout() {
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen bg-canvas text-ink">
      <aside className="fixed inset-y-0 left-0 hidden w-64 border-r border-line bg-surface shadow-soft lg:block">
        <div className="border-b border-line bg-gradient-to-br from-primary-700 to-primary-900 px-6 py-6 text-white">
          <div className="text-lg font-bold tracking-tight">Rainbow Fashions</div>
          <div className="mt-1 text-xs font-medium text-primary-100">{user?.role}</div>
        </div>
        <nav className="space-y-1 px-3 py-4">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className="group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition hover:bg-slate-100"
              >
                {({ isActive }) => (
                  <>
                    <span className={`grid h-8 w-8 place-items-center rounded-lg transition ${isActive ? "bg-white text-primary-700 shadow-sm" : "bg-slate-100 text-slate-500 group-hover:bg-white group-hover:text-slate-700"}`}>
                      <Icon size={18} />
                    </span>
                    <span className={isActive ? "text-primary-800" : "text-slate-600 group-hover:text-slate-950"}>{item.label}</span>
                  </>
                )}
              </NavLink>
            );
          })}
        </nav>
      </aside>
      <div className="lg:pl-64">
        <header className="sticky top-0 z-30 border-b border-line bg-surface/95 px-4 py-3 shadow-sm backdrop-blur lg:px-8">
          <div className="flex items-center justify-between gap-4">
            <div className="min-w-0 lg:hidden">
              <div className="text-base font-bold tracking-tight text-slate-950">Rainbow Fashions</div>
            </div>
            <div className="hidden min-w-0 lg:block">
              <div className="truncate text-sm font-semibold text-slate-900">{user?.full_name}</div>
              <div className="truncate text-xs text-slate-500">{user?.email}</div>
            </div>
            <button
              type="button"
              onClick={logout}
              className="focus-ring inline-flex h-10 items-center gap-2 rounded-lg border border-line bg-surface px-3 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-50"
              title="Logout"
            >
              <LogOut size={16} />
              <span className="hidden sm:inline">Logout</span>
            </button>
          </div>
        </header>
        <main className="px-4 py-6 pb-24 lg:px-8 lg:pb-6">
          <Outlet />
        </main>
        <nav className="fixed inset-x-0 bottom-0 z-50 grid h-[4.5rem] grid-cols-6 border-t border-line bg-surface pb-safe shadow-[0_-2px_10px_rgba(15,41,51,0.06)] lg:hidden">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `relative flex flex-col items-center justify-center gap-1 text-[10px] font-semibold transition ${
                    isActive ? "text-primary-700" : "text-slate-500"
                  }`
                }
              >
                {({ isActive }) => (
                  <>
                    {isActive ? <span className="absolute top-0 h-1 w-10 rounded-b bg-primary-600" /> : null}
                    <span className={`grid h-9 w-9 place-items-center rounded-xl transition ${isActive ? "bg-primary-50 text-primary-700" : ""}`}>
                      <Icon size={20} />
                    </span>
                    <span className="truncate px-1">{item.label}</span>
                  </>
                )}
              </NavLink>
            );
          })}
        </nav>
      </div>
    </div>
  );
}
