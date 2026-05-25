const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
const TOKEN_KEY = "bugtriage_token";
const USER_KEY = "bugtriage_user";

export type User = {
  email: string;
  role: string;
};

export type TicketStatus = "open" | "in_progress" | "resolved" | "closed";

export type TicketListItem = {
  ticket_id: string;
  title: string;
  reporter_email: string;
  status: TicketStatus;
  severity: string;
  component: string;
  created_at: string;
  updated_at: string;
};

export type StatusHistoryEntry = {
  status: TicketStatus;
  previous_status?: TicketStatus | null;
  changed_by: string;
  changed_at: string;
  resolution_note?: string | null;
};

export type TicketDetail = TicketListItem & {
  description: string;
  screenshot_urls: string[];
  assignee?: string | null;
  tags: string[];
  notes?: string | null;
  metadata: Record<string, unknown>;
  security: Record<string, unknown>;
  heuristic: Record<string, unknown>;
  llm: Record<string, unknown>;
  final_triage: Record<string, unknown>;
  status_history: StatusHistoryEntry[];
  closed_at?: string | null;
};

export type PaginatedTickets = {
  items: TicketListItem[];
  total: number;
  page: number;
  page_size: number;
};

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export function getToken() {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null) {
  if (typeof window === "undefined") return;
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

export function getStoredUser(): User | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as User;
  } catch {
    return null;
  }
}

export function setStoredUser(user: User | null) {
  if (typeof window === "undefined") return;
  if (user) localStorage.setItem(USER_KEY, JSON.stringify(user));
  else localStorage.removeItem(USER_KEY);
}

export function clearSession() {
  setToken(null);
  setStoredUser(null);
}

export function isAuthed() {
  return Boolean(getToken());
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (!headers.has("content-type") && init.body) headers.set("content-type", "application/json");
  const token = getToken();
  if (token) headers.set("authorization", `Bearer ${token}`);

  const res = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (!res.ok) {
    let message = `Request failed (${res.status})`;
    try {
      const payload = await res.json();
      message = payload.detail || payload.message || message;
    } catch {
      message = (await res.text()) || message;
    }
    throw new ApiError(res.status, message);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export async function refreshUser() {
  const user = await api<User>("/auth/me");
  setStoredUser(user);
  return user;
}
