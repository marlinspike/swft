import { useEffect, useRef, useState, type ReactNode } from "react";

type InfoPopoverProps = {
  title: string;
  description?: string;
  items?: Array<{ label?: string; content: ReactNode }>;
  align?: "left" | "right";
};

export const InfoPopover = ({ title, description, items, align = "right" }: InfoPopoverProps) => {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handleClick = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  const alignmentClass = align === "left" ? "left-0" : "right-0";

  return (
    <div className="relative inline-block" ref={containerRef}>
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        aria-label={`More information about ${title}`}
        className="inline-flex h-6 w-6 items-center justify-center rounded-full border border-slate-300 bg-white text-xs font-semibold text-slate-600 shadow-sm transition hover:border-slate-400 hover:text-slate-900 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200 dark:hover:border-slate-500 dark:hover:text-slate-50"
      >
        ?
      </button>
      {open && (
        <div className={`absolute z-20 mt-2 w-72 rounded-lg border border-slate-200 bg-white text-left shadow-lg dark:border-slate-700 dark:bg-slate-900 ${alignmentClass}`}>
          <div className="space-y-3 p-4 text-sm text-slate-600 dark:text-slate-300">
            <h4 className="text-sm font-semibold text-slate-800 dark:text-slate-100">{title}</h4>
            {description ? <p className="text-xs leading-relaxed text-slate-500 dark:text-slate-400">{description}</p> : null}
            {items && items.length > 0 ? (
              <ul className="space-y-2 text-xs leading-relaxed">
                {items.map((item, index) => (
                  <li key={item.label ?? index}>
                    {item.label ? <span className="font-semibold text-slate-700 dark:text-slate-200">{item.label}: </span> : null}
                    <span>{item.content}</span>
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
};

