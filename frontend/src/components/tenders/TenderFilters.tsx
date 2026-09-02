"use client";

import React, { useState, useEffect } from "react";
import { Search, Filter, RefreshCw, X } from "lucide-react";

interface TenderFiltersProps {
  search: string;
  status: string;
  includeArchived: boolean;
  onSearchChange: (search: string) => void;
  onStatusChange: (status: string) => void;
  onIncludeArchivedChange: (includeArchived: boolean) => void;
  onReset: () => void;
}

export function TenderFilters({
  search,
  status,
  includeArchived,
  onSearchChange,
  onStatusChange,
  onIncludeArchivedChange,
  onReset,
}: TenderFiltersProps) {
  const [searchInput, setSearchInput] = useState(search);

  // Debounce search input
  useEffect(() => {
    const handler = setTimeout(() => {
      onSearchChange(searchInput);
    }, 350);
    return () => clearTimeout(handler);
  }, [searchInput, onSearchChange]);

  const hasActiveFilters = search.trim() !== "" || status !== "" || includeArchived;

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs space-y-3">
      <div className="flex flex-col sm:flex-row sm:items-center gap-3">
        {/* Search Bar */}
        <div className="relative flex-1">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <input
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Search by tender number, title, or department..."
            className="block w-full rounded-lg border border-slate-300 bg-white pl-9 pr-8 py-2 text-xs text-slate-900 placeholder:text-slate-400 focus:border-purple-600 focus:outline-none focus:ring-1 focus:ring-purple-600"
          />
          {searchInput && (
            <button
              type="button"
              onClick={() => {
                setSearchInput("");
                onSearchChange("");
              }}
              className="absolute right-2.5 top-2.5 text-slate-400 hover:text-slate-600"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>

        {/* Status Dropdown */}
        <div className="flex items-center gap-2">
          <div className="relative min-w-[160px]">
            <select
              value={status}
              onChange={(e) => onStatusChange(e.target.value)}
              className="block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs text-slate-900 focus:border-purple-600 focus:outline-none focus:ring-1 focus:ring-purple-600 font-medium"
            >
              <option value="">All Statuses</option>
              <option value="DRAFT">Draft</option>
              <option value="PUBLISHED">Published</option>
              <option value="OPEN">Open for Bidding</option>
              <option value="CLOSED">Closed</option>
              <option value="UNDER_EVALUATION">Under Evaluation</option>
              <option value="AWARDED">Awarded</option>
              <option value="ARCHIVED">Archived</option>
            </select>
          </div>

          {/* Include Archived Toggle */}
          <label className="flex items-center gap-2 text-xs text-slate-600 font-medium select-none cursor-pointer pl-1">
            <input
              type="checkbox"
              checked={includeArchived}
              onChange={(e) => onIncludeArchivedChange(e.target.checked)}
              className="rounded border-slate-300 text-purple-900 focus:ring-purple-600 h-3.5 w-3.5"
            />
            <span>Show Archived</span>
          </label>

          {/* Reset Filters */}
          {hasActiveFilters && (
            <button
              type="button"
              onClick={() => {
                setSearchInput("");
                onReset();
              }}
              className="inline-flex items-center gap-1 text-xs text-slate-500 hover:text-slate-800 transition-colors px-2 py-1.5 rounded-md hover:bg-slate-100 cursor-pointer"
              title="Reset all filters"
            >
              <RefreshCw className="h-3 w-3" />
              Reset
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
