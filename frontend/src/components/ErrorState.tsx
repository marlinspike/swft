export const ErrorState = ({ message }: { message: string }) => (
  <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-rose-700 dark:border-rose-500/40 dark:bg-rose-500/10 dark:text-rose-200">
    <p className="font-medium">Something went wrong</p>
    <p className="text-sm text-rose-600 dark:text-rose-300">{message}</p>
  </div>
);
