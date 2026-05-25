import { createFileRoute, Link } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { AlertTriangle, Clock, Search, TrendingUp, X } from "lucide-react";
import { api, type PaginatedTickets, type TicketDetail, type TicketStatus } from "@/lib/api";
import { TicketPanel } from "@/routes/report";

export const Route = createFileRoute("/_authenticated/admin")({
  validateSearch: (s: Record<string, unknown>) => ({
    status: (s.status as string) ?? "all",
    severity: (s.severity as string) ?? "all",
  }),
  component: Admin,
});

const SEVERITY_COLOR: Record<string, string> = { P0: "text-[var(--sev-p0)]", P1: "text-[var(--sev-p1)]", P2: "text-[var(--sev-p2)]", P3: "text-[var(--sev-p3)]" };
const SEVERITY_GLOW: Record<string, string> = { P0: "glow-p0", P1: "glow-p1", P2: "glow-p2", P3: "glow-p3" };
const STATUSES: TicketStatus[] = ["open", "in_progress", "resolved", "closed"];

function Admin() {
  const search = Route.useSearch();
  const qc = useQueryClient();
  const [status, setStatus] = useState(search.status);
  const [severity, setSeverity] = useState(search.severity);
  const [q, setQ] = useState("");
  const [sort, setSort] = useState<"created_at" | "updated_at" | "ticket_id" | "status">("created_at");
  const [dir, setDir] = useState<-1 | 1>(-1);
  const [selectedTicketId, setSelectedTicketId] = useState<string | null>(null);
  const [editStatus, setEditStatus] = useState<TicketStatus>("open");
  const [resolutionNote, setResolutionNote] = useState("");

  const ticketQuery = useQuery({
    queryKey: ["tickets", status, severity, q, sort, dir],
    queryFn: () => {
      const params = new URLSearchParams({ page: "1", page_size: "100", sort_by: sort, sort_dir: String(dir) });
      if (status !== "all") params.set("status", status);
      if (severity !== "all") params.set("severity", severity);
      if (q) params.set("search", q);
      return api<PaginatedTickets>(`/bugs?${params}`);
    },
  });

  const kpis = useQuery({
    queryKey: ["kpis"],
    queryFn: async () => {
      const [volume, severityData, sla] = await Promise.all([
        api<{ series: { date: string; count: number }[] }>("/kpis/volume?days=7"),
        api<{ open_by_severity: Record<string, number>; total_open: number }>("/kpis/severity"),
        api<Record<string, { within_sla_percent: number }>>("/kpis/sla"),
      ]);
      return { volume, severityData, sla };
    },
  });

  const detailQuery = useQuery({
    queryKey: ["ticket", selectedTicketId],
    queryFn: () => api<TicketDetail>(`/bugs/${encodeURIComponent(selectedTicketId ?? "")}`),
    enabled: Boolean(selectedTicketId),
  });

  useEffect(() => {
    if (detailQuery.data) setEditStatus(detailQuery.data.status);
  }, [detailQuery.data]);

  const updateStatus = useMutation({
    mutationFn: () => api<TicketDetail>(`/bugs/${encodeURIComponent(selectedTicketId ?? "")}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status: editStatus, resolution_note: resolutionNote || null }),
    }),
    onSuccess: (ticket) => {
      toast.success("Ticket status updated");
      setResolutionNote("");
      setEditStatus(ticket.status);
      qc.setQueryData(["ticket", ticket.ticket_id], ticket);
      qc.invalidateQueries({ queryKey: ["tickets"] });
      qc.invalidateQueries({ queryKey: ["kpis"] });
    },
    onError: (err: any) => toast.error(err.message ?? "Update failed"),
  });

  const tickets = ticketQuery.data?.items ?? [];
  const maxVol = Math.max(1, ...(kpis.data?.volume.series.map((d) => d.count) ?? [0]));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Ops Dashboard</h1>
          <p className="text-sm text-muted-foreground">Triage queue and live KPIs</p>
        </div>
        <Link to="/" className="rounded-xl bg-white/5 px-4 py-2 text-sm text-muted-foreground hover:text-foreground">Back home</Link>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <KpiCard icon={<TrendingUp className="h-4 w-4" />} label="Last 7 days" value={kpis.data?.volume.series.reduce((sum, p) => sum + p.count, 0) ?? 0}>
          <div className="mt-3 flex h-12 items-end gap-1.5">
            {(kpis.data?.volume.series ?? []).map((p) => (
              <div key={p.date} className="flex-1 rounded-t bg-[var(--mint-strong)]/70" style={{ height: `${(p.count / maxVol) * 100}%`, minHeight: 4 }} title={`${p.date}: ${p.count}`} />
            ))}
          </div>
        </KpiCard>
        <KpiCard icon={<AlertTriangle className="h-4 w-4 text-[var(--sev-p0)]" />} label="Open by severity" value={kpis.data?.severityData.total_open ?? 0}>
          <div className="mt-3 flex flex-wrap gap-2">
            {["P0", "P1", "P2", "P3"].map((s) => (
              <span key={s} className={`chip ${SEVERITY_GLOW[s]} ${SEVERITY_COLOR[s]}`}>{s} / {kpis.data?.severityData.open_by_severity[s] ?? 0}</span>
            ))}
          </div>
        </KpiCard>
        <KpiCard icon={<Clock className="h-4 w-4" />} label="P0 SLA" value={`${kpis.data?.sla.P0?.within_sla_percent ?? "-"}%`} />
      </div>

      <div className="panel-inner flex flex-wrap items-center gap-3 p-3">
        <div className="flex flex-1 items-center gap-2 rounded-xl bg-white/5 px-3 py-2">
          <Search className="h-4 w-4 text-muted-foreground" />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search ticket, title, email..." className="w-full bg-transparent text-sm outline-none" />
        </div>
        <Select value={status} onChange={setStatus} options={["all", "open", "in_progress", "resolved", "closed"]} />
        <Select value={severity} onChange={setSeverity} options={["all", "P0", "P1", "P2", "P3"]} />
        <Select value={sort} onChange={(v) => setSort(v as any)} options={["created_at", "updated_at", "ticket_id", "status"]} />
        <button onClick={() => setDir(dir === -1 ? 1 : -1)} className="rounded-xl bg-white/5 px-3 py-2 text-xs">{dir === -1 ? "DESC" : "ASC"}</button>
      </div>

      <div className="panel-inner overflow-hidden">
        <table className="w-full text-sm">
          <thead className="text-left font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
            <tr><th className="px-4 py-3">Ticket</th><th className="px-4 py-3">Title</th><th className="px-4 py-3">Reporter</th><th className="px-4 py-3">Severity</th><th className="px-4 py-3">Status</th><th className="px-4 py-3">Component</th><th className="px-4 py-3">Created</th></tr>
          </thead>
          <tbody>
            {tickets.map((t) => (
              <tr key={t.ticket_id} className="border-t border-white/5 hover:bg-white/[0.03]">
                <td className="px-4 py-3">
                  <button onClick={() => setSelectedTicketId(t.ticket_id)} className="font-mono text-xs text-[var(--mint-strong)] hover:underline">
                    {t.ticket_id}
                  </button>
                </td>
                <td className="max-w-[300px] truncate px-4 py-3">{t.title}</td>
                <td className="px-4 py-3 text-muted-foreground">{t.reporter_email}</td>
                <td className="px-4 py-3"><span className={`chip ${SEVERITY_GLOW[t.severity] ?? ""} ${SEVERITY_COLOR[t.severity] ?? ""}`}>{t.severity}</span></td>
                <td className="px-4 py-3 text-muted-foreground">{t.status}</td>
                <td className="px-4 py-3 text-muted-foreground">{t.component}</td>
                <td className="px-4 py-3 text-muted-foreground">{new Date(t.created_at).toLocaleString()}</td>
              </tr>
            ))}
            {ticketQuery.isLoading && <tr><td colSpan={7} className="px-4 py-10 text-center text-sm text-muted-foreground">Loading tickets...</td></tr>}
            {!ticketQuery.isLoading && tickets.length === 0 && <tr><td colSpan={7} className="px-4 py-10 text-center text-sm text-muted-foreground">No tickets match these filters.</td></tr>}
          </tbody>
        </table>
      </div>

      {selectedTicketId ? (
        <div className="fixed inset-0 z-50 bg-black/70 p-3 backdrop-blur-sm md:p-6" role="dialog" aria-modal="true">
          <div className="mx-auto flex h-full max-w-6xl flex-col overflow-hidden rounded-xl border border-white/10 bg-[#151925] shadow-2xl">
            <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
              <div>
                <p className="font-mono text-[10px] uppercase tracking-wider text-[var(--mint-strong)]">Ops ticket detail</p>
                <h2 className="text-sm font-semibold">{selectedTicketId}</h2>
              </div>
              <button
                onClick={() => setSelectedTicketId(null)}
                className="flex h-9 w-9 items-center justify-center rounded-lg bg-white/5 text-muted-foreground hover:text-foreground"
                aria-label="Close ticket details"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="overflow-y-auto p-4 md:p-6">
              {detailQuery.isLoading && <div className="panel-inner p-6 text-sm text-muted-foreground">Loading ticket...</div>}
              {detailQuery.error && <div className="panel-inner p-6 text-sm text-[var(--sev-p0)]">{(detailQuery.error as Error).message}</div>}
              {detailQuery.data ? (
                <TicketPanel ticket={detailQuery.data}>
                  <div className="mt-5 panel-inner p-5">
                    <h2 className="mb-3 text-sm font-semibold">Update status</h2>
                    <div className="mb-4">
                      <StatusReadout label="Current status" value={detailQuery.data.status} />
                    </div>
                    <div className="grid gap-3 md:grid-cols-[220px_1fr_auto]">
                      <label className="block">
                        <span className="mb-1 block text-[11px] font-medium text-muted-foreground">Editable ticket status</span>
                        <select value={editStatus} onChange={(e) => setEditStatus(e.target.value as TicketStatus)} className="ctl">
                          {STATUSES.map((s) => <option key={s} value={s} className="bg-[#232838]">{s}</option>)}
                        </select>
                      </label>
                      <label className="block">
                        <span className="mb-1 block text-[11px] font-medium text-muted-foreground">Resolution note</span>
                        <input value={resolutionNote} onChange={(e) => setResolutionNote(e.target.value)} className="ctl" placeholder="Add update notes for the reporter" />
                      </label>
                      <button onClick={() => updateStatus.mutate()} disabled={updateStatus.isPending} className="self-end rounded-xl bg-[var(--mint-strong)] px-4 py-2 text-sm font-medium text-[#0e111a]">
                        {updateStatus.isPending ? "Saving..." : "Update"}
                      </button>
                    </div>
                  </div>
                </TicketPanel>
              ) : null}
            </div>
          </div>
        </div>
      ) : null}
      <style>{`.ctl{width:100%;border-radius:.75rem;background:#232838;border:1px solid rgba(255,255,255,0.05);padding:.55rem .75rem;font-size:13px;color:var(--color-foreground);}`}</style>
    </div>
  );
}

function KpiCard({ icon, label, value, children }: { icon: React.ReactNode; label: string; value: React.ReactNode; children?: React.ReactNode }) {
  return (
    <div className="panel-inner p-5">
      <div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-wider text-muted-foreground">{icon} {label}</div>
      <div className="mt-2 text-3xl font-semibold">{value}</div>
      {children}
    </div>
  );
}

function Select({ value, onChange, options }: { value: string; onChange: (v: string) => void; options: string[] }) {
  return (
    <select value={value} onChange={(e) => onChange(e.target.value)} className="rounded-xl bg-white/5 px-3 py-2 text-xs outline-none">
      {options.map((o) => <option key={o} value={o} className="bg-[#232838]">{o}</option>)}
    </select>
  );
}

function StatusReadout({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-white/5 p-3">
      <div className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">{label}</div>
      <div className="mt-1 text-sm">{value}</div>
    </div>
  );
}
