"use client";

import { CheckCircle, XCircle, Clock, Loader2, Pause, Ban, SkipForward, ImagePlus } from "lucide-react";
import { cn } from "@/lib/utils";
import type { RunStatus, StepStatus } from "@/lib/types";

interface RunStatusBadgeProps {
  status: RunStatus | StepStatus;
  showIcon?: boolean;
  size?: "sm" | "md" | "lg";
  pulse?: boolean;
  className?: string;
}

const statusConfig: Record<
  RunStatus | StepStatus,
  {
    label: string;
    bgColor: string;
    textColor: string;
    icon: React.ComponentType<{ className?: string }>;
  }
> = {
  pending: {
    label: "待機中",
    bgColor: "bg-gray-100 dark:bg-gray-700",
    textColor: "text-gray-600 dark:text-gray-300",
    icon: Clock,
  },
  running: {
    label: "実行中",
    bgColor: "bg-accent-100 dark:bg-accent-900/40",
    textColor: "text-accent-700 dark:text-accent-300",
    icon: Loader2,
  },
  waiting_approval: {
    label: "承認待ち",
    bgColor: "bg-warning-100 dark:bg-warning-900/40",
    textColor: "text-warning-700 dark:text-warning-300",
    icon: Pause,
  },
  waiting_image_input: {
    label: "画像入力待ち",
    bgColor: "bg-purple-100 dark:bg-purple-900/40",
    textColor: "text-purple-700 dark:text-purple-300",
    icon: ImagePlus,
  },
  completed: {
    label: "完了",
    bgColor: "bg-success-100 dark:bg-success-900/40",
    textColor: "text-success-700 dark:text-success-300",
    icon: CheckCircle,
  },
  failed: {
    label: "失敗",
    bgColor: "bg-error-100 dark:bg-error-900/40",
    textColor: "text-error-700 dark:text-error-300",
    icon: XCircle,
  },
  cancelled: {
    label: "キャンセル",
    bgColor: "bg-gray-100 dark:bg-gray-700",
    textColor: "text-gray-500 dark:text-gray-400",
    icon: Ban,
  },
  skipped: {
    label: "スキップ",
    bgColor: "bg-gray-100 dark:bg-gray-700",
    textColor: "text-gray-500 dark:text-gray-400",
    icon: SkipForward,
  },
};

const sizeConfig = {
  sm: {
    container: "px-2 py-0.5 text-xs gap-1",
    icon: "h-3 w-3",
  },
  md: {
    container: "px-2.5 py-1 text-xs gap-1.5",
    icon: "h-3.5 w-3.5",
  },
  lg: {
    container: "px-3 py-1.5 text-sm gap-2",
    icon: "h-4 w-4",
  },
};

export function RunStatusBadge({
  status,
  showIcon = true,
  size = "md",
  pulse = false,
  className,
}: RunStatusBadgeProps) {
  // フォールバック: 未知のステータスの場合はpendingとして扱う
  const config = statusConfig[status] || statusConfig.pending;
  const sizeClass = sizeConfig[size];
  const IconComponent = config.icon;
  const shouldAnimate = status === "running";
  const shouldPulse = pulse || status === "waiting_approval" || status === "waiting_image_input";

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full font-medium transition-all",
        config.bgColor,
        config.textColor,
        sizeClass.container,
        shouldPulse && "animate-pulse-soft",
        className,
      )}
    >
      {showIcon && (
        <IconComponent
          className={cn(sizeClass.icon, "flex-shrink-0", shouldAnimate && "animate-spin")}
        />
      )}
      <span>{config.label}</span>
    </span>
  );
}

// Compact dot indicator for tight spaces
export function StatusDot({
  status,
  size = "md",
  pulse = false,
}: {
  status: RunStatus | StepStatus;
  size?: "sm" | "md" | "lg";
  pulse?: boolean;
}) {
  const dotColors: Record<RunStatus | StepStatus, string> = {
    pending: "bg-gray-400",
    running: "bg-accent-500",
    waiting_approval: "bg-warning-500",
    waiting_image_input: "bg-purple-500",
    completed: "bg-success-500",
    failed: "bg-error-500",
    cancelled: "bg-gray-400",
    skipped: "bg-gray-400",
  };

  const dotSizes = {
    sm: "w-1.5 h-1.5",
    md: "w-2 h-2",
    lg: "w-2.5 h-2.5",
  };

  const shouldPulse = pulse || status === "running" || status === "waiting_approval" || status === "waiting_image_input";
  // フォールバック: 未知のステータスの場合はgray
  const dotColor = dotColors[status] || "bg-gray-400";

  return (
    <span className="relative inline-flex">
      <span className={cn("rounded-full", dotColor, dotSizes[size])} />
      {shouldPulse && (
        <span
          className={cn("absolute inset-0 rounded-full animate-ping opacity-75", dotColor)}
        />
      )}
    </span>
  );
}
