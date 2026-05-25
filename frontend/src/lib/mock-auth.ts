// Frontend-only mock auth + mock ticket data.
const KEY = "mock_auth_user";

export type MockUser = { email: string; name: string; verified: boolean };

export const mockAuth = {
  get(): MockUser | null {
    if (typeof window === "undefined") return null;
    try { return JSON.parse(localStorage.getItem(KEY) || "null"); } catch { return null; }
  },
  set(u: MockUser) { localStorage.setItem(KEY, JSON.stringify(u)); },
  clear() { localStorage.removeItem(KEY); },
  isAuthed() { const u = this.get(); return !!u && u.verified; },
};

// ---- Mock tickets ----
const SEV = ["P0", "P1", "P2", "P3"] as const;
const STATUS = ["open", "triaging", "in_progress", "resolved", "closed"] as const;
const GROUPS = ["auth", "billing", "infra", "frontend", "api"];

function mkTicket(i: number) {
  const sev = SEV[i % 4];
  const st = STATUS[i % 5];
  const created = new Date(Date.now() - i * 3600_000 * 6).toISOString();
  return {
    id: `tk_${i}`,
    ticket_code: `BUG-${9001 + i}`,
    title: [
      "Login OTP not arriving for some users",
      "Checkout fails on Safari 17",
      "Dashboard chart shows wrong totals",
      "API 504 on /reports endpoint",
      "Avatar upload broken > 2MB",
      "Email digest duplicated today",
      "Password reset link expires too fast",
      "Mobile nav overlaps content",
    ][i % 8],
    description: "Reporter pasted stack trace. Steps to reproduce included. Environment: production.",
    reporter_email: ["alex@acme.io", "sam@globex.com", "jules@hooli.net", "rin@initech.co"][i % 4],
    severity: sev,
    status: st,
    assigned_group: GROUPS[i % GROUPS.length],
    created_at: created,
    attachment_url: i % 3 === 0 ? "logs/trace.txt" : null,
    heuristic_output: { score: 0.62, keywords: ["error", "fail"], severity: sev },
    llm_output: { summary: "Likely auth-service regression after deploy.", suggested_group: GROUPS[i % GROUPS.length], severity: sev, confidence: 0.84 },
    ai_summary: "Likely auth-service regression after recent deploy. Investigate token issuance path.",
    ai_confidence: 0.84,
    resolution_notes: st === "closed" ? "Patched in v2.4.1; verified." : null,
  };
}

export const mockTickets = Array.from({ length: 14 }, (_, i) => mkTicket(i));

export type AuditEvent = { id: string; event_type: string; from_value: string | null; to_value: string; note: string | null; created_at: string };
export const mockEvents = (id: string): AuditEvent[] => [
  { id: `${id}-1`, event_type: "created", from_value: null, to_value: "open", note: null, created_at: new Date(Date.now() - 86400_000).toISOString() },
  { id: `${id}-2`, event_type: "ai_classified", from_value: null, to_value: "P2", note: "auto", created_at: new Date(Date.now() - 80000_000).toISOString() },
  { id: `${id}-3`, event_type: "status_change", from_value: "open", to_value: "triaging", note: null, created_at: new Date(Date.now() - 7200_000).toISOString() },
];

export const mockKpis = () => {
  const days = Array.from({ length: 7 }, (_, i) => {
    const d = new Date(); d.setDate(d.getDate() - (6 - i));
    return [d.toISOString().slice(5, 10), Math.floor(2 + Math.random() * 9)] as const;
  });
  return {
    total_7d: days.reduce((s, [, v]) => s + v, 0),
    total_open: mockTickets.filter(t => !["resolved", "closed"].includes(t.status)).length,
    mttr_hours: 18.4,
    volumeByDay: Object.fromEntries(days),
    openBySeverity: { P0: 1, P1: 3, P2: 5, P3: 2 },
  };
};
