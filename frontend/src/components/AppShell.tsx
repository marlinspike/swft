import type { ReactNode } from "react";
import { ThemeToggle } from "@components/ThemeToggle";

export const AppShell = ({ children }: { children: ReactNode }) => (
  <div className="min-h-screen bg-slate-50 text-slate-900 transition-colors dark:bg-slate-950 dark:text-slate-100">
    <header className="border-b border-slate-200 bg-white/80 backdrop-blur dark:border-slate-800 dark:bg-slate-900/60">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <div>
          <h1 className="text-xl font-semibold text-slate-900 dark:text-white">SCAI Security Portal</h1>
          <span className="text-sm text-slate-500 dark:text-slate-400">Supply Chain Assurance</span>
        </div>
        <ThemeToggle />
      </div>
    </header>
    <main className="mx-auto max-w-6xl px-6 py-6 transition-colors dark:bg-transparent">{children}</main>
  </div>
);
