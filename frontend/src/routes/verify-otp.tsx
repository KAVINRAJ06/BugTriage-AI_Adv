import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { toast } from "sonner";
import { AuthShell } from "./login";
import { InputOTP, InputOTPGroup, InputOTPSlot } from "@/components/ui/input-otp";
import { api, refreshUser, setToken } from "@/lib/api";

export const Route = createFileRoute("/verify-otp")({
  validateSearch: (s: Record<string, unknown>) => ({
    email: String(s.email ?? ""),
    challenge: String(s.challenge ?? ""),
    returnTo: typeof s.returnTo === "string" ? s.returnTo : "",
  }),
  component: VerifyOtp,
});

function safeReturnTo(value: string) {
  return value.startsWith("/") && !value.startsWith("//") ? value : "";
}

function ticketFromReportLink(value: string) {
  const safe = safeReturnTo(value);
  if (!safe) return "";
  const params = new URLSearchParams(safe.split("?")[1] ?? "");
  return params.get("ticket") ?? "";
}

function VerifyOtp() {
  const { email, challenge, returnTo } = Route.useSearch();
  const nav = useNavigate();
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);

  async function verify() {
    if (code.length !== 6) return;
    setBusy(true);
    try {
      const result = await api<{ access_token: string }>("/auth/verify-otp", {
        method: "POST",
        body: JSON.stringify({ challenge_token: challenge, otp: code }),
      });
      setToken(result.access_token);
      const user = await refreshUser();
      toast.success("Verified");
      const safeTarget = safeReturnTo(returnTo);
      const ticket = ticketFromReportLink(safeTarget);
      if (user.role === "admin" && ticket) {
        nav({ to: "/admin/$id", params: { id: ticket } });
      } else if (user.role === "admin") {
        nav({ to: "/admin" });
      } else if (safeTarget) {
        nav({ to: safeTarget });
      } else {
        nav({ to: "/report" });
      }
    } catch (err: any) {
      toast.error(err.message ?? "Invalid code");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell title="Verify your email" subtitle={`Enter the 6-digit code sent to ${email || "your inbox"}`}>
      <div className="space-y-5">
        <div className="flex justify-center">
          <InputOTP maxLength={6} value={code} onChange={setCode}>
            <InputOTPGroup>
              {[0, 1, 2, 3, 4, 5].map((i) => <InputOTPSlot key={i} index={i} className="h-12 w-11 rounded-xl border-white/10 bg-[#232838] text-lg" />)}
            </InputOTPGroup>
          </InputOTP>
        </div>
        <button disabled={busy || code.length !== 6} onClick={verify} className="mint-btn w-full">{busy ? "Verifying..." : "Verify"}</button>
        <button onClick={() => toast.message("Sign in again to resend the code")} className="w-full text-sm text-muted-foreground hover:text-foreground">Resend code</button>
      </div>
    </AuthShell>
  );
}
