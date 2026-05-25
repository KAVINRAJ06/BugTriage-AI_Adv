import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { toast } from "sonner";
import { ArrowLeft, Sparkles } from "lucide-react";
import { api, refreshUser, setToken } from "@/lib/api";

export const Route = createFileRoute("/login")({ component: Login });

function Login() {
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      const result = await api<{ flow: "token" | "otp"; access_token?: string; challenge_token?: string; message: string }>("/auth/sign-in", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      if (result.flow === "token" && result.access_token) {
        setToken(result.access_token);
        await refreshUser();
        toast.success("Signed in");
        nav({ to: "/admin" });
        return;
      }
      if (result.flow === "otp" && result.challenge_token) {
        toast.success("OTP sent to your email");
        nav({ to: "/verify-otp", search: { email, challenge: result.challenge_token } });
      }
    } catch (err: any) {
      toast.error(err.message ?? "Sign in failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell title="Sign in" subtitle="Reporter access uses email, password, and OTP">
      <form onSubmit={onSubmit} className="space-y-4">
        <Field label="Email">
          <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className="auth-input" />
        </Field>
        <Field label="Password">
          <input type="password" required value={password} onChange={(e) => setPassword(e.target.value)} className="auth-input" />
        </Field>
        <button disabled={busy} className="mint-btn w-full">{busy ? "Signing in..." : "Continue"}</button>
      </form>
      <p className="mt-5 text-center text-sm text-muted-foreground">
        No account? <Link to="/register" className="text-[var(--mint-strong)]">Create one</Link>
      </p>
    </AuthShell>
  );
}

export function AuthShell({ children, title, subtitle }: { children: React.ReactNode; title: string; subtitle?: string }) {
  return (
    <div className="min-h-screen grid md:grid-cols-2">
      <div className="hidden md:flex flex-col justify-between p-10 panel-2 m-3 rounded-[1.5rem]">
        <div className="flex items-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[var(--mint-strong)] text-[#0e111a]"><Sparkles className="h-4 w-4" /></div>
          <div className="font-semibold">BugTriage <span className="text-[var(--mint-strong)]">AI</span></div>
        </div>
        <div>
          <h2 className="text-4xl font-bold">Triage that <span className="text-[var(--mint-strong)]">just works.</span></h2>
          <p className="mt-3 max-w-sm text-muted-foreground">AI-powered classification, severity scoring, and routing in one dark, focused console.</p>
        </div>
        <div className="font-mono text-[11px] text-muted-foreground">// secure tunnel - v1.0 - demo</div>
      </div>
      <div className="flex items-center justify-center p-6">
        <div className="w-full max-w-sm">
          <Link to="/" className="mb-5 inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground">
            <ArrowLeft className="h-4 w-4" /> Back
          </Link>
          <h1 className="text-2xl font-semibold">{title}</h1>
          {subtitle && <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p>}
          <div className="mt-6">{children}</div>
        </div>
      </div>
      <style>{`
        .auth-input { width:100%; border-radius: .9rem; background:#232838; border:1px solid rgba(255,255,255,0.05); padding:.7rem .9rem; font-size:14px; color:var(--color-foreground); }
        .auth-input:focus { outline:none; border-color: var(--mint-strong); box-shadow: 0 0 0 3px rgba(141,215,192,.15); }
        .mint-btn { background: var(--mint-strong); color:#0e111a; border-radius: .9rem; padding:.7rem 1rem; font-weight:500; font-size:14px; }
        .mint-btn:hover { filter: brightness(1.05); }
        .mint-btn:disabled { opacity:.6; }
      `}</style>
    </div>
  );
}

export function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-medium text-muted-foreground">{label}</span>
      {children}
    </label>
  );
}
