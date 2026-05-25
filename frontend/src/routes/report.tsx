import { createFileRoute, Link, redirect, useNavigate } from "@tanstack/react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import {
  ArrowLeft,
  CheckCircle2,
  FileText,
  Home,
  LogOut,
  RefreshCw,
  Sparkles,
  Upload,
} from "lucide-react";
import {
  api,
  clearSession,
  getStoredUser,
  isAuthed,
  refreshUser,
  type PaginatedTickets,
  type TicketDetail,
} from "@/lib/api";

export const Route = createFileRoute("/report")({
  beforeLoad: () => {
    if (typeof window !== "undefined" && !isAuthed()) {
      throw redirect({ to: "/login" });
    }
  },
  validateSearch: (s: Record<string, unknown>) => ({ ticket: String(s.ticket ?? "") }),
  component: Report,
});

type SubmitResult = {
  ticket_id: string;
  status: string;
  final_triage: Record<string, any>;
  heuristic: Record<string, any>;
  llm: Record<string, any>;
  security_flagged: boolean;
  created_at: string;
};

function Report() {
  const { ticket } = Route.useSearch();
  const nav = useNavigate();
  const qc = useQueryClient();
  const authed = isAuthed();
  const [mode, setMode] = useState<"text" | "file">("text");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [screenshotUrls, setScreenshotUrls] = useState("");
  const [result, setResult] = useState<SubmitResult | null>(null);
  const [busy, setBusy] = useState(false);

  const me = useQuery({
    queryKey: ["me"],
    queryFn: refreshUser,
    enabled: authed,
    initialData: authed ? getStoredUser() ?? undefined : undefined,
  });

  const ticketsQuery = useQuery({
    queryKey: ["reporter-tickets"],
    queryFn: () => api<PaginatedTickets>("/report?page=1&page_size=100"),
    enabled: authed,
  });

  const detailQuery = useQuery({
    queryKey: ["reporter-ticket", ticket],
    queryFn: () => api<TicketDetail>(`/report/${encodeURIComponent(ticket)}`),
    enabled: authed && Boolean(ticket),
  });

  useEffect(() => {
    if (!authed) {
      nav({ to: "/login", replace: true });
      return;
    }
    if (me.data?.role === "admin") {
      nav({ to: "/admin", replace: true });
    }
  }, [authed, me.data?.role, nav]);

  async function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const text = await file.text();
    setTitle((t) => t || file.name);
    setDescription(text.slice(0, 5000));
    toast.success(`Loaded ${file.name}`);
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!me.data?.email) {
      toast.error("Please sign in again before submitting.");
      return;
    }
    setBusy(true);
    try {
      const data = await api<SubmitResult>("/report", {
        method: "POST",
        body: JSON.stringify({
          title: title.trim(),
          description: description.trim(),
          reporter_email: me.data.email,
          screenshot_urls: screenshotUrls
            .split(",")
            .map((s) => s.trim())
            .filter(Boolean),
        }),
      });
      setResult(data);
      setTitle("");
      setDescription("");
      setScreenshotUrls("");
      await qc.invalidateQueries({ queryKey: ["reporter-tickets"] });
      toast.success(`Filed ${data.ticket_id}`);
      nav({ to: "/report", search: { ticket: data.ticket_id }, replace: true });
    } catch (err: any) {
      toast.error(err.message ?? "Submission failed");
    } finally {
      setBusy(false);
    }
  }

  function signOut() {
    clearSession();
    nav({ to: "/login" });
  }

  const tickets = ticketsQuery.data?.items ?? [];

  if (!authed) {
    return (
      <ReportShell>
        <div className="panel mx-auto mt-16 max-w-md p-6 text-center">
          <h1 className="text-xl font-semibold">Sign in to view this ticket</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Reporter ticket links are private. Sign in with the reporter account that submitted the bug.
          </p>
          <Link to="/login" className="mint-btn mt-5 inline-flex">
            Sign in
          </Link>
        </div>
        <FormStyles />
      </ReportShell>
    );
  }

  return (
    <ReportShell>
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <Link to="/" className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground">
          <Home className="h-4 w-4" /> Home
        </Link>
        <div className="flex items-center gap-3">
          <span className="hidden text-xs text-muted-foreground sm:inline">{me.data?.email}</span>
          <button
            onClick={() => ticketsQuery.refetch()}
            className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
          >
            <RefreshCw className="h-4 w-4" /> Refresh
          </button>
          <button onClick={signOut} className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground">
            <LogOut className="h-4 w-4" /> Sign out
          </button>
        </div>
      </div>

      {ticket ? (
        <div className="space-y-4">
          <button
            onClick={() => nav({ to: "/report", search: { ticket: "" } })}
            className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="h-4 w-4" /> Back to my reports
          </button>
          {detailQuery.isLoading && <div className="panel p-6 text-sm text-muted-foreground">Loading ticket...</div>}
          {detailQuery.error && <div className="panel p-6 text-sm text-[var(--sev-p0)]">{(detailQuery.error as Error).message}</div>}
          {detailQuery.data && <TicketPanel ticket={detailQuery.data} viewer />}
        </div>
      ) : (
        <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_420px]">
          <section className="panel p-6 md:p-8 fade-up">
            <div className="flex items-center gap-2">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[var(--mint-strong)] text-[#0e111a]">
                <Sparkles className="h-4 w-4" />
              </div>
              <div>
                <h1 className="text-xl font-semibold">Submit a bug</h1>
                <p className="text-xs text-muted-foreground">Signed-in reporters can file and track their own tickets.</p>
              </div>
            </div>

            <form onSubmit={onSubmit} className="mt-6 space-y-4">
              <div className="inline-flex rounded-xl bg-[#232838] p-1">
                <button
                  type="button"
                  onClick={() => setMode("text")}
                  className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs ${mode === "text" ? "bg-[var(--mint-strong)] text-[#0e111a]" : "text-muted-foreground"}`}
                >
                  <FileText className="h-3.5 w-3.5" /> Text
                </button>
                <button
                  type="button"
                  onClick={() => setMode("file")}
                  className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs ${mode === "file" ? "bg-[var(--mint-strong)] text-[#0e111a]" : "text-muted-foreground"}`}
                >
                  <Upload className="h-3.5 w-3.5" /> File upload
                </button>
              </div>

              <input
                className="auth-input"
                placeholder="Short title..."
                required
                maxLength={200}
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
              {mode === "text" ? (
                <textarea
                  required
                  minLength={10}
                  maxLength={5000}
                  className="auth-input min-h-[180px] resize-y"
                  placeholder="Describe the bug, steps, environment..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                />
              ) : (
                <label className="block cursor-pointer rounded-xl border border-dashed border-white/10 bg-[#232838] p-8 text-center hover:border-[var(--mint-strong)]">
                  <Upload className="mx-auto h-6 w-6 text-muted-foreground" />
                  <div className="mt-2 text-sm">{description ? "File loaded - click to replace" : "Upload a bug report file (.txt, .log, .md)"}</div>
                  <input type="file" className="hidden" accept=".txt,.log,.md,.json,.csv" onChange={onFile} />
                </label>
              )}
              <input
                className="auth-input"
                placeholder="Screenshot URLs, comma separated (optional)"
                value={screenshotUrls}
                onChange={(e) => setScreenshotUrls(e.target.value)}
              />
              <button disabled={busy || me.isLoading} className="mint-btn w-full">
                {busy ? "AI is triaging..." : "Submit report"}
              </button>
            </form>

            {result && (
              <div className="mt-6 panel-inner p-5">
                <div className="flex items-center gap-2 text-[var(--mint-strong)]">
                  <CheckCircle2 className="h-5 w-5" /> <span className="font-medium">Report received</span>
                </div>
                <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
                  <Stat label="Ticket" value={result.ticket_id} mono />
                  <Stat label="Status" value={result.status} />
                  <Stat label="Severity" value={String(result.final_triage?.severity ?? "-")} />
                  <Stat label="Component" value={String(result.final_triage?.component ?? "-")} />
                </div>
              </div>
            )}
          </section>

          <section className="panel p-5 fade-up">
            <div className="mb-4">
              <h2 className="text-lg font-semibold">My bug submissions</h2>
              <p className="text-xs text-muted-foreground">Open a ticket to view its read-only details.</p>
            </div>
            <div className="space-y-2">
              {tickets.map((t) => (
                <Link
                  key={t.ticket_id}
                  to="/report"
                  search={{ ticket: t.ticket_id }}
                  className="block rounded-lg border border-white/5 bg-white/[0.03] p-3 hover:border-[var(--mint-strong)]/50 hover:bg-white/[0.05]"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="font-mono text-[11px] text-[var(--mint-strong)]">{t.ticket_id}</div>
                      <div className="mt-1 truncate text-sm font-medium">{t.title}</div>
                      <div className="mt-1 text-xs text-muted-foreground">{new Date(t.created_at).toLocaleString()}</div>
                    </div>
                    <div className="flex shrink-0 flex-col items-end gap-1">
                      <SeverityChip severity={t.severity} />
                      <span className="text-xs text-muted-foreground">{t.status}</span>
                    </div>
                  </div>
                </Link>
              ))}
              {ticketsQuery.isLoading && <div className="rounded-lg bg-white/[0.03] p-6 text-center text-sm text-muted-foreground">Loading reports...</div>}
              {!ticketsQuery.isLoading && tickets.length === 0 && (
                <div className="rounded-lg bg-white/[0.03] p-6 text-center text-sm text-muted-foreground">No reports submitted yet.</div>
              )}
            </div>
          </section>
        </div>
      )}
      <FormStyles />
    </ReportShell>
  );
}

export function TicketPanel({ ticket, viewer = false, children }: { ticket: TicketDetail; viewer?: boolean; children?: React.ReactNode }) {
  const final = ticket.final_triage || {};
  const heuristic = ticket.heuristic || {};
  const llm = ticket.llm || {};
  const security = ticket.security || {};

  return (
    <div className="panel p-6 md:p-8 fade-up">
      <div className="flex flex-wrap justify-between gap-3">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-wider text-[var(--mint-strong)]">{viewer ? "Read-only ticket" : "Ticket detail"}</p>
          <h1 className="mt-1 text-2xl font-semibold">{ticket.ticket_id} - {ticket.title}</h1>
          <p className="mt-2 text-sm text-muted-foreground">{ticket.reporter_email} / {new Date(ticket.created_at).toLocaleString()}</p>
        </div>
        <div className="flex items-start gap-2">
          <SeverityChip severity={String(final.severity || ticket.severity || "P3")} />
          <span className="chip bg-white/5 text-muted-foreground">{ticket.status}</span>
        </div>
      </div>

      <p className="mt-5 whitespace-pre-wrap text-sm leading-6">{ticket.description}</p>

      <div className="mt-5 grid gap-3 md:grid-cols-3">
        <Stat label="Component" value={String(final.component ?? ticket.component ?? "General")} />
        <Stat label="Blast radius" value={String(final.blast_radius ?? "-")} />
        <Stat label="Duplicate" value={formatPercent(final.duplicate_likelihood)} />
      </div>

      <div className="mt-5 grid gap-4 md:grid-cols-2">
        <Section title="Heuristic output">
          <KV label="Severity" value={String(heuristic.severity ?? "-")} />
          <KV label="Component" value={String(heuristic.component ?? "General")} />
          <KV label="Tags" value={Array.isArray(heuristic.tags) && heuristic.tags.length ? heuristic.tags.join(", ") : "None"} />
          <KV label="Confidence" value={formatPercent(heuristic.confidence)} />
        </Section>
        <Section title="LLM output">
          <KV label="One line summary" value={String(llm.one_line_summary ?? llm.summary ?? "-")} />
          <KV label="Suggested severity" value={String(llm.suggested_severity ?? llm.severity ?? "-")} />
          <KV label="Blast radius" value={String(llm.blast_radius ?? "-")} />
          <KV label="Suggested assignee group" value={String(llm.suggested_assignee_group ?? llm.assignee_group ?? "-")} />
          <KV label="Duplicate likelihood" value={formatPercent(llm.duplicate_likelihood)} />
        </Section>
      </div>

      <Section title="Final triage" className="mt-5">
        <KV label="Summary" value={String(final.summary ?? "-")} />
        <KV label="Routing action" value={String(final.routing_action ?? "-")} />
        <KV label="Severity" value={String(final.severity ?? "-")} />
        <KV label="Base severity" value={String(final.base_severity ?? "-")} />
        <KV label="Heuristic severity" value={String(final.heuristic_severity ?? "-")} />
        <KV label="Agent severity" value={String(final.agent_severity ?? "-")} />
        <KV label="Component" value={String(final.component ?? "General")} />
        <KV label="Tags" value={Array.isArray(ticket.tags) && ticket.tags.length ? ticket.tags.join(", ") : "None"} />
        <KV label="Assignee group" value={String(final.assignee_group ?? final.suggested_assignee_group ?? ticket.assignee ?? "-")} />
        <KV label="Blast radius" value={String(final.blast_radius ?? "-")} />
        <KV label="Duplicate likelihood" value={formatPercent(final.duplicate_likelihood)} />
        <KV label="Confidence" value={formatPercent(final.confidence)} />
      </Section>

      {security.security_flagged ? <div className="mt-5 rounded-lg border border-[var(--sev-p0)]/30 bg-[var(--sev-p0)]/10 p-3 text-sm text-[var(--sev-p0)]">Security flagged</div> : null}

      <Section title="Status history" className="mt-5">
        {ticket.status_history.length === 0 ? <p className="text-sm text-muted-foreground">No status changes yet.</p> : ticket.status_history.slice().reverse().map((e, i) => (
          <div key={`${e.changed_at}-${i}`} className="border-l-2 border-[var(--mint-strong)]/40 pl-3 text-sm">
            <div className="font-medium">{e.previous_status ? `${e.previous_status} -> ${e.status}` : e.status}</div>
            <div className="text-xs text-muted-foreground">{e.changed_by} / {new Date(e.changed_at).toLocaleString()}</div>
            {e.resolution_note ? <p className="mt-1 text-muted-foreground">{e.resolution_note}</p> : null}
          </div>
        ))}
      </Section>
      {children}
    </div>
  );
}

function ReportShell({ children }: { children: React.ReactNode }) {
  return <div className="min-h-screen p-3 md:p-6"><div className="mx-auto max-w-6xl">{children}</div></div>;
}

function Section({ title, children, className = "" }: { title: string; children: React.ReactNode; className?: string }) {
  return <div className={`panel-inner p-5 ${className}`}><h2 className="mb-3 text-sm font-semibold">{title}</h2><div className="space-y-2">{children}</div></div>;
}

function KV({ label, value }: { label: string; value: string }) {
  return <div className="grid gap-1 text-sm md:grid-cols-[170px_1fr]"><span className="text-muted-foreground">{label}</span><span>{value}</span></div>;
}

function Stat({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return <div className="rounded-lg bg-white/5 p-3"><div className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">{label}</div><div className={`mt-1 text-sm ${mono ? "font-mono" : ""}`}>{value}</div></div>;
}

function SeverityChip({ severity }: { severity: string }) {
  const cls = severity === "P0" ? "glow-p0 text-[var(--sev-p0)]" : severity === "P1" ? "glow-p1 text-[var(--sev-p1)]" : severity === "P3" ? "glow-p3 text-[var(--sev-p3)]" : "glow-p2 text-[var(--sev-p2)]";
  return <span className={`chip ${cls}`}>{severity}</span>;
}

function formatPercent(value: unknown) {
  if (typeof value !== "number") return "-";
  return value <= 1 ? `${Math.round(value * 100)}%` : `${Math.round(value)}%`;
}

function FormStyles() {
  return <style>{`
    .auth-input { width:100%; border-radius: .9rem; background:#232838; border:1px solid rgba(255,255,255,0.05); padding:.7rem .9rem; font-size:14px; color:var(--color-foreground); }
    .auth-input:focus { outline:none; border-color: var(--mint-strong); box-shadow: 0 0 0 3px rgba(141,215,192,.15); }
    .mint-btn { background: var(--mint-strong); color:#0e111a; border-radius: .9rem; padding:.7rem 1rem; font-weight:500; font-size:14px; }
    .mint-btn:disabled { opacity:.6; }
  `}</style>;
}
