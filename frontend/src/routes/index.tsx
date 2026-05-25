import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowRight, Bug, Shield, Sparkles } from "lucide-react";

export const Route = createFileRoute("/")({
  component: Landing,
});

function Landing() {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="flex items-center justify-between px-6 py-5 md:px-10">
        <div className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[var(--mint-strong)] text-[#0e111a]">
            <Sparkles className="h-4 w-4" />
          </div>
          <div className="font-semibold">BugTriage <span className="text-[var(--mint-strong)]">AI</span></div>
        </div>
        <div className="flex gap-2">
          <Link to="/login" className="rounded-xl px-4 py-2 text-sm text-muted-foreground hover:text-foreground">Sign in</Link>
          <Link to="/register" className="rounded-xl bg-[var(--mint-strong)] px-4 py-2 text-sm font-medium text-[#0e111a]">Get started</Link>
        </div>
      </header>

      <main className="flex-1 flex items-center px-6 md:px-10">
        <div className="mx-auto grid max-w-6xl gap-10 md:grid-cols-2 md:items-center">
          <div>
            <div className="chip bg-white/5 text-[var(--mint-strong)]">
              <span className="h-1.5 w-1.5 rounded-full bg-[var(--mint-strong)] blink" /> AI triage online
            </div>
            <h1 className="mt-5 text-5xl font-bold tracking-tight md:text-6xl">
              Bug reports,<br /><span className="text-[var(--mint-strong)]">auto-triaged.</span>
            </h1>
            <p className="mt-5 max-w-md text-muted-foreground">
              Registered reporters can file bugs after OTP login. AI classifies severity, summarizes, and routes each ticket to ops.
            </p>
            <div className="mt-7 flex gap-3">
              <Link to="/login" className="inline-flex items-center gap-2 rounded-xl bg-[var(--mint-strong)] px-5 py-3 text-sm font-medium text-[#0e111a]">
                Submit a bug <ArrowRight className="h-4 w-4" />
              </Link>
              <Link to="/login" className="inline-flex items-center gap-2 rounded-xl border border-white/10 px-5 py-3 text-sm hover:bg-white/5">
                Ops console
              </Link>
            </div>
          </div>
          <div className="panel p-6 mint-glow">
            <div className="flex items-center justify-between">
              <div className="font-mono text-xs text-muted-foreground">LIVE FEED</div>
              <span className="chip bg-white/5 text-[var(--sev-p2)]">P2 - backend</span>
            </div>
            <div className="mt-4 space-y-3">
              {[
                { code: "BUG-9841", t: "Checkout 500 on staging", s: "P1" },
                { code: "BUG-9840", t: "Typo in onboarding copy", s: "P3" },
                { code: "BUG-9839", t: "Auth loop on Safari mobile", s: "P0" },
              ].map((r) => (
                <div key={r.code} className="panel-inner flex items-center justify-between p-3.5">
                  <div>
                    <div className="font-mono text-[11px] text-muted-foreground">{r.code}</div>
                    <div className="text-sm">{r.t}</div>
                  </div>
                  <span className={`chip ${r.s === "P0" ? "glow-p0 text-[var(--sev-p0)]" : r.s === "P1" ? "glow-p1 text-[var(--sev-p1)]" : "glow-p3 text-[var(--sev-p3)]"}`}>{r.s}</span>
                </div>
              ))}
            </div>
            <div className="mt-5 grid grid-cols-3 gap-3">
              {[{ k: "Open", v: "23" }, { k: "MTTR", v: "4.1h" }, { k: "Today", v: "12" }].map((s) => (
                <div key={s.k} className="panel-inner p-3 text-center">
                  <div className="text-2xl font-semibold">{s.v}</div>
                  <div className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">{s.k}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </main>

      <footer className="px-6 py-6 text-center text-xs text-muted-foreground">
        <Bug className="inline h-3 w-3" /> BugTriage AI - <Shield className="inline h-3 w-3" /> Cloud-secured
      </footer>
    </div>
  );
}
