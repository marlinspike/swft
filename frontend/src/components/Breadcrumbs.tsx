import { Link } from "react-router-dom";

export const Breadcrumbs = ({ items }: { items: { label: string; to?: string }[] }) => (
  <nav className="mb-6 text-sm text-slate-500 dark:text-slate-400" aria-label="Breadcrumb">
    <ol className="flex items-center gap-2">
      {items.map((item, index) => (
        <li key={`${item.label}-${index}`} className="flex items-center gap-2">
          {item.to ? <Link to={item.to} className="text-blue-600 transition hover:text-blue-500 dark:text-blue-300 dark:hover:text-blue-200">{item.label}</Link> : <span className="text-slate-700 dark:text-slate-200">{item.label}</span>}
          {index < items.length - 1 && <span className="text-slate-400 dark:text-slate-600">/</span>}
        </li>
      ))}
    </ol>
  </nav>
);
