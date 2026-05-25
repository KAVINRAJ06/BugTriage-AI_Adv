import { Link, useLocation, useNavigate } from "@tanstack/react-router";
import { Home, Inbox, BarChart3, Bug, LifeBuoy, Settings, LogOut, Sparkles } from "lucide-react";
import { clearSession } from "@/lib/api";

type Item = { to: "/admin" | "/report"; search?: Record<string, string>; label: string; icon: React.ComponentType<{ className?: string }>; match: string };

const ITEMS: Item[] = [
  { to: "/admin", label: "Dashboard", icon: Home, match: "/admin|all" },
  { to: "/admin", search: { status: "open" }, label: "Open Tickets", icon: Inbox, match: "/admin|open" },
  { to: "/admin", search: { status: "closed" }, label: "Closed", icon: BarChart3, match: "/admin|closed" },
  { to: "/report", label: "Submit Report", icon: Bug, match: "/report|" },
];

export function Sidebar() {
  const loc = useLocation();
  const nav = useNavigate();
  const currentStatus = new URLSearchParams(loc.search).get("status") ?? "all";
  const currentKey = `${loc.pathname}|${loc.pathname === "/admin" ? currentStatus : ""}`;

  return (
    <aside className="flex h-screen sticky top-0 gap-3 p-3">
      <div className="panel-2 flex w-[68px] flex-col items-center gap-3 py-5">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[var(--mint-strong)] text-[#0e111a] font-bold">
          <Sparkles className="h-4 w-4" />
        </div>
        <div className="mt-2 flex flex-1 flex-col items-center gap-1.5">
          {[Home, Inbox, Bug, BarChart3, LifeBuoy, Settings].map((I, i) => (
            <button key={i} className="flex h-10 w-10 items-center justify-center rounded-xl text-muted-foreground hover:bg-white/5 hover:text-foreground">
              <I className="h-4 w-4" />
            </button>
          ))}
        </div>
        <button
          onClick={() => { clearSession(); nav({ to: "/login" }); }}
          className="flex h-10 w-10 items-center justify-center rounded-xl text-muted-foreground hover:bg-white/5 hover:text-foreground"
          title="Sign out"
        >
          <LogOut className="h-4 w-4" />
        </button>
      </div>

      <div className="panel-2 hidden w-[220px] flex-col gap-1.5 p-4 md:flex">
        <div className="mb-3 px-2">
          <div className="font-mono text-[11px] uppercase tracking-widest text-muted-foreground">BugTriage</div>
          <div className="text-sm font-semibold">Ops Console</div>
        </div>
        {ITEMS.map((it) => {
          const active = currentKey.startsWith(it.match);
          return (
            <Link
              key={it.label}
              to={it.to}
              search={it.search as any}
              className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition ${
                active
                  ? "bg-[var(--mint-strong)] text-[#0e111a] font-medium mint-glow"
                  : "text-muted-foreground hover:bg-white/5 hover:text-foreground"
              }`}
            >
              <it.icon className="h-4 w-4" />
              {it.label}
            </Link>
          );
        })}
      </div>
    </aside>
  );
}
