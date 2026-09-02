/**
 * Enterprise Utility Formatters for Currency, Dates, and Text
 */

export function formatCurrency(
  amount?: number | string | null,
  currency: string = "INR"
): string {
  if (amount === undefined || amount === null || amount === "") {
    return "—";
  }

  const num = typeof amount === "string" ? parseFloat(amount) : amount;
  if (isNaN(num)) return "—";

  try {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: currency || "INR",
      maximumFractionDigits: 2,
    }).format(num);
  } catch {
    return `${currency} ${num.toLocaleString("en-IN")}`;
  }
}

export function formatDate(dateStr?: string | null): string {
  if (!dateStr) return "Not set";
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return "Invalid Date";
    return new Intl.DateTimeFormat("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    }).format(d);
  } catch {
    return dateStr;
  }
}

export function formatDateTime(dateStr?: string | null): string {
  if (!dateStr) return "Not set";
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return "Invalid Date";
    return new Intl.DateTimeFormat("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      hour12: true,
    }).format(d);
  } catch {
    return dateStr;
  }
}

export function toDatetimeLocalString(dateStr?: string | null): string {
  if (!dateStr) return "";
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return "";
    const pad = (n: number) => n.toString().padStart(2, "0");
    const year = d.getFullYear();
    const month = pad(d.getMonth() + 1);
    const day = pad(d.getDate());
    const hours = pad(d.getHours());
    const minutes = pad(d.getMinutes());
    return `${year}-${month}-${day}T${hours}:${minutes}`;
  } catch {
    return "";
  }
}

export function formatDeadlineRemaining(deadlineStr?: string | null): {
  text: string;
  isUrgent: boolean;
  isPassed: boolean;
  colorClass: string;
} {
  if (!deadlineStr) {
    return {
      text: "No deadline",
      isUrgent: false,
      isPassed: false,
      colorClass: "text-slate-500 bg-slate-100 border-slate-200",
    };
  }

  const deadline = new Date(deadlineStr);
  const now = new Date();

  if (isNaN(deadline.getTime())) {
    return {
      text: "Invalid date",
      isUrgent: false,
      isPassed: false,
      colorClass: "text-slate-500 bg-slate-100 border-slate-200",
    };
  }

  const diffMs = deadline.getTime() - now.getTime();
  const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays < 0) {
    return {
      text: "Submission Closed",
      isUrgent: false,
      isPassed: true,
      colorClass: "text-slate-600 bg-slate-100 border-slate-200",
    };
  } else if (diffDays === 0) {
    return {
      text: "Closes Today",
      isUrgent: true,
      isPassed: false,
      colorClass: "text-rose-800 bg-rose-50 border-rose-200",
    };
  } else if (diffDays === 1) {
    return {
      text: "Closes Tomorrow",
      isUrgent: true,
      isPassed: false,
      colorClass: "text-rose-800 bg-rose-50 border-rose-200",
    };
  } else if (diffDays <= 5) {
    return {
      text: `${diffDays} days left`,
      isUrgent: true,
      isPassed: false,
      colorClass: "text-amber-800 bg-amber-50 border-amber-200",
    };
  } else {
    return {
      text: `${diffDays} days left`,
      isUrgent: false,
      isPassed: false,
      colorClass: "text-emerald-800 bg-emerald-50 border-emerald-200",
    };
  }
}
