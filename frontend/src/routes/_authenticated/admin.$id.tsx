import { createFileRoute, Link } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { ArrowLeft } from "lucide-react";
import { api, type TicketDetail, type TicketStatus } from "@/lib/api";
import { TicketPanel } from "@/routes/report";

export const Route = createFileRoute("/_authenticated/admin/$id")({ component: Detail });

const STATUSES: TicketStatus[] = ["open", "in_progress", "resolved", "closed"];

function Detail() {
  const { id } = Route.useParams();
  const qc = useQueryClient();
  const [status, setStatus] = useState<TicketStatus>("open");
  const [resolutionNote, setResolutionNote] = useState("");

  const query = useQuery({
    queryKey: ["ticket", id],
    queryFn: () => api<TicketDetail>(`/bugs/${encodeURIComponent(id)}`),
  });

  useEffect(() => {
    if (query.data) setStatus(query.data.status);
  }, [query.data]);

  const updateStatus = useMutation({
    mutationFn: () => api<TicketDetail>(`/bugs/${encodeURIComponent(id)}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status, resolution_note: resolutionNote || null }),
    }),
    onSuccess: () => {
      toast.success("Ticket status updated");
      setResolutionNote("");
      qc.invalidateQueries({ queryKey: ["ticket", id] });
      qc.invalidateQueries({ queryKey: ["tickets"] });
      qc.invalidateQueries({ queryKey: ["kpis"] });
    },
    onError: (err: any) => toast.error(err.message ?? "Update failed"),
  });

  return (
    <div className="space-y-6">
      <Link to="/admin" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"><ArrowLeft className="h-4 w-4" /> All tickets</Link>
      {query.isLoading && <div className="panel-inner p-6 text-sm text-muted-foreground">Loading ticket...</div>}
      {query.error && <div className="panel-inner p-6 text-sm text-[var(--sev-p0)]">{(query.error as Error).message}</div>}
      {query.data && (
        <TicketPanel ticket={query.data}>
          <div className="mt-5 panel-inner p-5">
            <h2 className="mb-3 text-sm font-semibold">Update status</h2>
            <div className="grid gap-3 md:grid-cols-[220px_1fr_auto]">
              <label className="block">
                <span className="mb-1 block text-[11px] font-medium text-muted-foreground">Status</span>
                <select value={status} onChange={(e) => setStatus(e.target.value as TicketStatus)} className="ctl">
                  {STATUSES.map((s) => <option key={s} value={s} className="bg-[#232838]">{s}</option>)}
                </select>
              </label>
              <label className="block">
                <span className="mb-1 block text-[11px] font-medium text-muted-foreground">Resolution note</span>
                <input value={resolutionNote} onChange={(e) => setResolutionNote(e.target.value)} className="ctl" placeholder="Optional note for the reporter" />
              </label>
              <button onClick={() => updateStatus.mutate()} disabled={updateStatus.isPending} className="self-end rounded-xl bg-[var(--mint-strong)] px-4 py-2 text-sm font-medium text-[#0e111a]">
                {updateStatus.isPending ? "Saving..." : "Update"}
              </button>
            </div>
            <style>{`.ctl{width:100%;border-radius:.75rem;background:#232838;border:1px solid rgba(255,255,255,0.05);padding:.55rem .75rem;font-size:13px;color:var(--color-foreground);}`}</style>
          </div>
        </TicketPanel>
      )}
    </div>
  );
}
