"use client";

import React from "react";
import { QualityLevel } from "@/types/document_quality";
import {
  CheckCircle2,
  AlertTriangle,
  AlertOctagon,
  Eye,
  FileWarning,
} from "lucide-react";

interface DocumentQualityBadgeProps {
  score?: number | null;
  level?: QualityLevel | string | null;
  isBlurry?: boolean;
  hasBlankPages?: boolean;
  hasUnreadablePages?: boolean;
  isCorrupted?: boolean;
  isPasswordProtected?: boolean;
  showScore?: boolean;
  className?: string;
  onClick?: () => void;
}

export const DocumentQualityBadge: React.FC<DocumentQualityBadgeProps> = ({
  score,
  level = "GOOD",
  isBlurry = false,
  hasBlankPages = false,
  hasUnreadablePages = false,
  isCorrupted = false,
  isPasswordProtected = false,
  showScore = true,
  className = "",
  onClick,
}) => {
  const normLevel = (level || "GOOD").toUpperCase();

  let badgeStyle = "bg-emerald-50 text-emerald-800 border-emerald-200";
  let icon = <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 shrink-0" />;
  let label = "Quality: GOOD";

  if (normLevel === "UNUSABLE" || isCorrupted || isPasswordProtected) {
    badgeStyle = "bg-rose-50 text-rose-800 border-rose-200";
    icon = <AlertOctagon className="h-3.5 w-3.5 text-rose-600 shrink-0" />;
    label = isCorrupted ? "Corrupted File" : isPasswordProtected ? "Password Locked" : "Quality: UNUSABLE";
  } else if (normLevel === "POOR" || hasUnreadablePages || isBlurry) {
    badgeStyle = "bg-amber-50 text-amber-800 border-amber-200";
    icon = <AlertTriangle className="h-3.5 w-3.5 text-amber-600 shrink-0" />;
    label = "Quality: POOR";
  } else if (normLevel === "ACCEPTABLE") {
    badgeStyle = "bg-blue-50 text-blue-800 border-blue-200";
    icon = <Eye className="h-3.5 w-3.5 text-blue-600 shrink-0" />;
    label = "Quality: ACCEPTABLE";
  }

  const scoreText = score !== undefined && score !== null ? ` (${Math.round(score)}%)` : "";

  return (
    <div
      onClick={onClick}
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold border ${badgeStyle} ${
        onClick ? "cursor-pointer hover:opacity-90 transition-opacity" : ""
      } ${className}`}
      title={
        hasUnreadablePages
          ? "Unreadable pages detected"
          : isBlurry
          ? "Blur detected"
          : hasBlankPages
          ? "Blank pages detected"
          : `Document Quality: ${normLevel}`
      }
    >
      {icon}
      <span>
        {label}
        {showScore ? scoreText : ""}
      </span>
      {(isBlurry || hasUnreadablePages || hasBlankPages) && normLevel !== "UNUSABLE" && (
        <FileWarning className="h-3 w-3 text-amber-600 opacity-80" />
      )}
    </div>
  );
};
