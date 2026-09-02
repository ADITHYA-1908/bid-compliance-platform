import React from "react";
import Link from "next/link";
import { ChevronRight } from "lucide-react";

export interface BreadcrumbItem {
  label: string;
  href?: string;
}

interface PageHeaderProps {
  title: string;
  description?: string;
  breadcrumbs?: BreadcrumbItem[];
  action?: React.ReactNode;
}

export function PageHeader({
  title,
  description,
  breadcrumbs,
  action,
}: PageHeaderProps) {
  return (
    <div className="mb-8 border-b border-slate-800/80 pb-6">
      {breadcrumbs && breadcrumbs.length > 0 && (
        <nav aria-label="Breadcrumb" className="mb-2.5">
          <ol className="flex items-center space-x-1.5 text-xs text-slate-400">
            {breadcrumbs.map((item, idx) => {
              const isLast = idx === breadcrumbs.length - 1;
              return (
                <li key={idx} className="flex items-center space-x-1.5">
                  {idx > 0 && <ChevronRight className="h-3.5 w-3.5 text-slate-500 shrink-0" />}
                  {item.href && !isLast ? (
                    <Link
                      href={item.href}
                      className="hover:text-purple-400 transition-colors"
                    >
                      {item.label}
                    </Link>
                  ) : (
                    <span className={isLast ? "font-semibold text-slate-200" : ""}>
                      {item.label}
                    </span>
                  )}
                </li>
              );
            })}
          </ol>
        </nav>
      )}

      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight text-white sm:text-3xl">
            {title}
          </h1>
          {description && (
            <p className="mt-1.5 text-xs text-slate-400 sm:text-sm leading-relaxed max-w-3xl">
              {description}
            </p>
          )}
        </div>
        {action && <div className="shrink-0">{action}</div>}
      </div>
    </div>
  );
}
