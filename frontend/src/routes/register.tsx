import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { toast } from "sonner";
import { AuthShell, Field } from "./login";
import { api } from "@/lib/api";

export const Route = createFileRoute("/register")({ component: Register });

function Register() {
  const nav = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (password.length < 8) {
      toast.error("Password must be 8+ chars");
      return;
    }
    setBusy(true);
    try {
      const result = await api<{ challenge_token: string; message: string }>("/auth/register", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      toast.success("OTP sent to your email");
      nav({ to: "/verify-otp", search: { email, challenge: result.challenge_token } });
    } catch (err: any) {
      toast.error(err.message ?? "Registration failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell title="Create account" subtitle="One-time reporter registration">
      <form onSubmit={onSubmit} className="space-y-4">
        <Field label="Display name"><input value={name} onChange={(e) => setName(e.target.value)} className="auth-input" required maxLength={60} /></Field>
        <Field label="Email"><input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className="auth-input" /></Field>
        <Field label="Password (8+ chars)"><input type="password" required minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} className="auth-input" /></Field>
        <button disabled={busy} className="mint-btn w-full">{busy ? "Creating..." : "Create account"}</button>
      </form>
      <p className="mt-5 text-center text-sm text-muted-foreground">
        Have one? <Link to="/login" className="text-[var(--mint-strong)]">Sign in</Link>
      </p>
    </AuthShell>
  );
}
