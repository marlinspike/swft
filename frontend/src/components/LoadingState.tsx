// Minimal loading indicator for async fetches.
export const LoadingState = ({ message = "Loading" }: { message?: string }) => (
  <div className="flex items-center gap-3 rounded-lg border border-slate-200 bg-slate-100 px-4 py-3 text-slate-600 dark:border-slate-800 dark:bg-slate-900/70 dark:text-slate-300">
    <span className="h-3 w-3 animate-ping rounded-full bg-blue-400" />
    <span>{message}…</span>
  </div>
);
