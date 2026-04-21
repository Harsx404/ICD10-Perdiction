import { NavLink, Outlet, useLocation } from "react-router-dom";
import {
  Activity,
  Clock3,
  CreditCard,
  FileText,
  LayoutDashboard,
} from "lucide-react";
import { useAnalysisState } from "../../context/AnalysisContext";

const NAV_ITEMS = [
  { to: "/analysis", label: "Analysis", icon: LayoutDashboard },
  { to: "/history", label: "History", icon: Clock3 },
  { to: "/report", label: "Reports", icon: FileText },
  { to: "/billing", label: "Billing", icon: CreditCard },
];

function ShellChip({
  label,
  value,
  tone = "slate",
}: {
  label: string;
  value: string;
  tone?: "brand" | "emerald" | "amber" | "slate";
}) {
  const tones = {
    brand: "border-brand-100 bg-brand-50 text-brand-700",
    emerald: "border-emerald-100 bg-emerald-50 text-emerald-700",
    amber: "border-amber-100 bg-amber-50 text-amber-700",
    slate: "border-slate-200 bg-white text-slate-700",
  };

  return (
    <div className={`rounded-xl border px-3 py-1.5 shadow-sm ${tones[tone]}`}>
      <p className="text-[9px] font-bold uppercase tracking-[0.2em] opacity-70">{label}</p>
      <p className="text-xs font-semibold">{value}</p>
    </div>
  );
}

export default function Layout() {
  const location = useLocation();
  const { history, isAnalyzing, images, noteText } = useAnalysisState();

  const hasInput = Boolean(noteText.trim() || images.length);
  const sessionStatus = isAnalyzing ? "Running" : hasInput ? "Ready" : "Idle";
  const sessionTone: "brand" | "emerald" | "slate" = isAnalyzing
    ? "brand"
    : hasInput
      ? "emerald"
      : "slate";

  return (
    <div className="relative min-h-screen bg-slate-50/30 overflow-hidden text-slate-900">
      <div className="pointer-events-none absolute left-[-8rem] top-[-10rem] h-72 w-72 rounded-full bg-brand-200/50 blur-3xl" />
      <div className="pointer-events-none absolute right-[-6rem] top-8 h-80 w-80 rounded-full bg-sky-200/40 blur-3xl" />

      <div className="relative flex min-h-screen flex-col">
        <header className="sticky top-0 z-20 border-b border-white/70 bg-white/72 px-4 py-3 backdrop-blur-xl sm:px-6 lg:px-8 shadow-sm">
          <div className="mx-auto flex w-full max-w-[1600px] items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-600 text-white shadow-soft">
                <Activity className="h-5 w-5" />
              </div>
              <div className="hidden sm:block">
                <p className="text-[10px] font-bold uppercase tracking-[0.24em] text-brand-600">
                  Clinical Intelligence
                </p>
                <h1 className="text-sm font-semibold text-slate-900">
                  Coding Workspace
                </h1>
              </div>
            </div>

            <nav className="flex items-center gap-1 sm:gap-2">
              {NAV_ITEMS.map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    className={({ isActive }) =>
                      [
                        "group flex items-center gap-2.5 rounded-xl px-3 py-2 text-sm font-semibold transition-all",
                        isActive || (item.to === "/analysis" && location.pathname === "/")
                          ? "bg-brand-600 text-white shadow-soft"
                          : "text-slate-600 hover:bg-white hover:text-slate-900 hover:shadow-card",
                      ].join(" ")
                    }
                  >
                    {({ isActive }) => {
                      const active = isActive || (item.to === "/analysis" && location.pathname === "/");
                      return (
                        <>
                          <span
                            className={[
                              "flex h-8 w-8 items-center justify-center rounded-lg transition-colors",
                              active
                                ? "bg-white/18 text-white"
                                : "bg-slate-100 text-slate-500 group-hover:bg-brand-50 group-hover:text-brand-600",
                            ].join(" ")}
                          >
                            <Icon className="h-4 w-4" />
                          </span>
                          <span className="hidden md:block">{item.label}</span>
                        </>
                      );
                    }}
                  </NavLink>
                );
              })}
            </nav>

            <div className="hidden items-center gap-2 lg:flex">
              <ShellChip label="Status" value={sessionStatus} tone={sessionTone} />
              <ShellChip
                label="History"
                value={`${history.length} saved`}
                tone="slate"
              />
            </div>
          </div>
        </header>

        <main className="mx-auto flex w-full max-w-[1600px] flex-1 flex-col px-4 pb-8 pt-6 sm:px-6 lg:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
