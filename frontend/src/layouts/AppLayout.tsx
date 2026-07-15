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
    <div className="min-h-screen bg-[#f6f8fb] text-ink">
      <aside className="fixed inset-y-0 left-0 hidden w-64 border-r border-line bg-white lg:block">
        <div className="border-b border-line px-6 py-5">
          <div className="text-lg font-semibold">Rainbow fashions</div>
          <div className="mt-1 text-xs uppercase tracking-wide text-teal-700">{user?.role}</div>
        </div>
        <nav className="space-y-1 px-3 py-4">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition ${
                    isActive ? "bg-teal-50 text-teal-800" : "text-slate-600 hover:bg-slate-100 hover:text-slate-950"
                  }`
                }
              >
                <Icon size={18} />
                {item.label}
              </NavLink>
            );
          })}
        </nav>
      </aside>
      <div className="lg:pl-64">
        <header className="sticky top-0 z-10 border-b border-line bg-white/95 px-4 py-3 backdrop-blur lg:px-8">
          <div className="flex items-center justify-between gap-4">
            <div>
              <div className="text-sm font-semibold text-slate-900">{user?.full_name}</div>
              <div className="text-xs text-slate-500">{user?.email}</div>
            </div>
            <button
              type="button"
              onClick={logout}
              className="focus-ring inline-flex h-9 items-center gap-2 rounded-md border border-line bg-white px-3 text-sm text-slate-700 hover:bg-slate-50"
              title="Logout"
            >
              <LogOut size={16} />
              Logout
            </button>
          </div>
          <nav className="mt-3 flex gap-2 overflow-x-auto lg:hidden">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `whitespace-nowrap rounded-md px-3 py-2 text-xs font-medium ${
                    isActive ? "bg-teal-700 text-white" : "bg-slate-100 text-slate-700"
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        </header>
        <main className="px-4 py-6 lg:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
