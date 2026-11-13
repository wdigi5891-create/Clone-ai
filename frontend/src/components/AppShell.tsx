"use client";
import { FolderOpen, LayoutDashboard, LogOut, PlusCircle, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "@/lib/auth";
import { Logo, Spinner } from "./ui";

const NAV = [
  { href: "/dashboard", label: "Tableau de bord", icon: LayoutDashboard },
  { href: "/new", label: "Nouvelle analyse", icon: PlusCircle },
  { href: "/projects", label: "Bibliothèque", icon: FolderOpen },
];

/** Coque de l'espace de travail : protège les routes et fournit la navigation. */
export default function AppShell({ children }: { children: React.ReactNode }) {
  const { user, loading, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!loading && !user) router.replace(`/login?next=${encodeURIComponent(pathname)}`);
  }, [loading, user, router, pathname]);

  if (loading || !user) {
    return <div className="grid min-h-screen place-items-center text-slate-400"><Spinner className="h-6 w-6" /></div>;
  }
  const active = (href: string) => pathname === href || (href === "/projects" && pathname.startsWith("/projects/"));
  return (
    <div className="min-h-screen lg:pl-64">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col border-r border-white/10 bg-ink-900/80 p-5 backdrop-blur-xl lg:flex">
        <Logo href="/dashboard" />
        <nav className="mt-8 flex flex-1 flex-col gap-1">
          {NAV.map((n) => (
            <Link key={n.href} href={n.href}
              className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition ${active(n.href) ? "bg-white/10 text-white" : "text-slate-400 hover:bg-white/5 hover:text-white"}`}>
              <n.icon className={`h-[18px] w-[18px] ${active(n.href) ? "text-brand-cyan" : ""}`} />
              {n.label}
            </Link>
          ))}
          <Link href="/privacy" className="mt-auto flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-slate-400 hover:bg-white/5 hover:text-white">
            <ShieldCheck className="h-[18px] w-[18px]" /> Confidentialité
          </Link>
        </nav>
        <div className="mt-3 flex items-center gap-3 rounded-xl border border-white/10 bg-white/5 p-3">
          <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-brand-gradient text-sm font-bold text-white">
            {(user.name || user.email)[0].toUpperCase()}
          </span>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-white">{user.name || "Mon compte"}</p>
            <p className="truncate text-xs text-slate-400">{user.email}</p>
          </div>
          <button onClick={logout} title="Se déconnecter" aria-label="Se déconnecter" className="rounded-lg p-1.5 text-slate-400 hover:bg-white/10 hover:text-white">
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </aside>

      <header className="sticky top-0 z-20 flex items-center justify-between border-b border-white/10 bg-ink-950/85 px-4 py-3 backdrop-blur-xl lg:hidden">
        <Logo href="/dashboard" />
        <button onClick={logout} aria-label="Se déconnecter" className="rounded-lg p-2 text-slate-400 hover:bg-white/10"><LogOut className="h-5 w-5" /></button>
      </header>

      <main className="mx-auto w-full max-w-6xl px-4 pb-28 pt-6 sm:px-6 lg:px-10 lg:pb-12 lg:pt-10">{children}</main>

      <nav className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-3 border-t border-white/10 bg-ink-900/95 backdrop-blur-xl lg:hidden">
        {NAV.map((n) => (
          <Link key={n.href} href={n.href} className={`flex flex-col items-center gap-1 py-2.5 text-[11px] font-medium ${active(n.href) ? "text-white" : "text-slate-400"}`}>
            <n.icon className={`h-5 w-5 ${active(n.href) ? "text-brand-cyan" : ""}`} />
            {n.label}
          </Link>
        ))}
      </nav>
    </div>
  );
}
