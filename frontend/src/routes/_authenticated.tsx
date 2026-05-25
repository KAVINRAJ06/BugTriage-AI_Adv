import { createFileRoute, Outlet, redirect } from "@tanstack/react-router";
import { Sidebar } from "@/components/Sidebar";
import { isAuthed } from "@/lib/api";

export const Route = createFileRoute("/_authenticated")({
  beforeLoad: () => {
    if (typeof window !== "undefined" && !isAuthed()) {
      throw redirect({ to: "/login" });
    }
  },
  component: () => (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-3 pl-0">
        <div className="panel min-h-[calc(100vh-1.5rem)] p-6 md:p-8">
          <Outlet />
        </div>
      </main>
    </div>
  ),
});
