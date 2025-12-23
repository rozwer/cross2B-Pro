"use client";

import {
  CheckCircle,
  XCircle,
  Loader2,
  Clock,
  Pause,
  Sparkles,
  Search,
  FileText,
  Pencil,
  Eye,
  Package,
  ChevronRight,
  Image,
} from "lucide-react";
import type { Step } from "@/lib/types";
import { STEP_LABELS, normalizeStepName } from "@/lib/types";
import { cn } from "@/lib/utils";

/**
 * Pattern 2: LangGraph Studio Style
 * - Light theme with subtle grid background
 * - DAG visualization with bezier curves
 * - Clean card-based nodes with shadows
 * - Technical but elegant aesthetic
 */

interface WorkflowPattern2Props {
  steps: Step[];
  currentStep: string;
  waitingApproval: boolean;
}

const STEP_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  "step-1": Package,
  step0: Sparkles,
  step1: Search,
  step3: FileText,
  step2: Search,
  step3a: Sparkles,
  step3b: Sparkles,
  step3c: Sparkles,
  step4: FileText,
  step5: Pencil,
  step6: Eye,
  "step6.5": Package,
  step7a: FileText,
  step7b: FileText,
  step8: Eye,
  step9: Sparkles,
  step10: CheckCircle,
  step11: Image,
};

// Simplified layout: rows with items
const FLOW_LAYOUT = [
  { row: 0, items: ["step-1"] },
  { row: 1, items: ["step0"] },
  { row: 2, items: ["step1"] },
  { row: 3, items: ["step2", "step3"] },
  { row: 4, items: ["step3a", "step3b", "step3c"] },
  { row: 5, items: ["step4"] },
  { row: 6, items: ["step5"] },
  { row: 7, items: ["step6"] },
  { row: 8, items: ["step6.5"] },
  { row: 9, items: ["step7a", "step7b"] },
  { row: 10, items: ["step8"] },
  { row: 11, items: ["step9"] },
  { row: 12, items: ["step10"] },
  { row: 13, items: ["step11"] },
];

export function WorkflowPattern2_LangGraphStyle({
  steps,
  currentStep,
  waitingApproval,
}: WorkflowPattern2Props) {
  // Normalize step names (step6_5 -> step6.5) for consistent lookup
  const stepMap = new Map(steps.map((s) => [normalizeStepName(s.step_name), s]));
  const completedCount = steps.filter((s) => s.status === "completed").length;
  const totalSteps = Object.keys(STEP_LABELS).length;
  const progress = Math.round((completedCount / totalSteps) * 100);

  const getStatusStyles = (status?: string, isWaiting?: boolean) => {
    if (isWaiting)
      return {
        border: "border-amber-400",
        bg: "bg-amber-50",
        text: "text-amber-700",
        icon: "text-amber-500",
      };
    switch (status) {
      case "completed":
        return {
          border: "border-emerald-400",
          bg: "bg-emerald-50",
          text: "text-emerald-700",
          icon: "text-emerald-500",
        };
      case "running":
        return {
          border: "border-blue-400",
          bg: "bg-blue-50",
          text: "text-blue-700",
          icon: "text-blue-500",
        };
      case "failed":
        return {
          border: "border-red-400",
          bg: "bg-red-50",
          text: "text-red-700",
          icon: "text-red-500",
        };
      default:
        return {
          border: "border-gray-200",
          bg: "bg-gray-50",
          text: "text-gray-500",
          icon: "text-gray-400",
        };
    }
  };

  const getStatusIcon = (status?: string, isWaiting?: boolean) => {
    if (isWaiting) return <Pause className="w-3.5 h-3.5" />;
    switch (status) {
      case "completed":
        return <CheckCircle className="w-3.5 h-3.5" />;
      case "running":
        return <Loader2 className="w-3.5 h-3.5 animate-spin" />;
      case "failed":
        return <XCircle className="w-3.5 h-3.5" />;
      default:
        return <Clock className="w-3.5 h-3.5" />;
    }
  };

  return (
    <div className="rounded-2xl overflow-hidden bg-white border border-gray-200">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-100 bg-gray-50/50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-emerald-500" />
              <span className="text-sm font-mono text-gray-600">run_abc123</span>
            </div>
            <div className="h-4 w-px bg-gray-300" />
            <span className="text-sm text-gray-500">{progress}% 完了</span>
            <div className="h-4 w-px bg-gray-300" />
            <span className="text-sm text-gray-500">経過: 2:34</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="px-2 py-1 text-xs font-medium bg-blue-100 text-blue-700 rounded">
              {completedCount} / {totalSteps} steps
            </span>
          </div>
        </div>
      </div>

      {/* Graph Canvas */}
      <div
        className="relative p-8 overflow-x-auto"
        style={{
          backgroundImage: "radial-gradient(circle, #e5e7eb 1px, transparent 1px)",
          backgroundSize: "24px 24px",
        }}
      >
        <div className="flex flex-col gap-3 min-w-max">
          {FLOW_LAYOUT.map((row, rowIndex) => (
            <div key={rowIndex} className="flex items-center justify-center gap-4">
              {row.items.map((stepName, itemIndex) => {
                const step = stepMap.get(stepName);
                const status = step?.status;
                const isCurrent = stepName === currentStep;
                const isWaiting = waitingApproval && isCurrent;
                const styles = getStatusStyles(status, isWaiting);
                const Icon = STEP_ICONS[stepName] || Sparkles;

                return (
                  <div key={stepName} className="flex items-center gap-4">
                    {/* Node */}
                    <div
                      className={cn(
                        "relative flex items-center gap-3 px-4 py-3",
                        "bg-white rounded-xl border-2 shadow-sm",
                        "transition-all duration-200 hover:shadow-md",
                        styles.border,
                        isCurrent && "ring-2 ring-blue-200",
                      )}
                    >
                      {/* Icon */}
                      <div
                        className={cn(
                          "w-8 h-8 rounded-lg flex items-center justify-center",
                          styles.bg,
                        )}
                      >
                        <Icon className={cn("w-4 h-4", styles.icon)} />
                      </div>

                      {/* Content */}
                      <div className="min-w-[100px]">
                        <div className="flex items-center gap-2">
                          <span className={cn("text-sm font-medium", styles.text)}>
                            {STEP_LABELS[stepName]}
                          </span>
                          <span className={styles.icon}>{getStatusIcon(status, isWaiting)}</span>
                        </div>
                        <span className="text-xs font-mono text-gray-400">{stepName}</span>
                      </div>

                      {/* Running indicator */}
                      {status === "running" && (
                        <div className="absolute -top-1 -right-1 w-3 h-3 bg-blue-500 rounded-full animate-pulse" />
                      )}
                    </div>

                    {/* Horizontal connector for multi-item rows */}
                    {itemIndex < row.items.length - 1 && (
                      <div className="flex items-center text-gray-300">
                        <div className="w-8 h-0.5 bg-gray-200" />
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ))}
        </div>

        {/* Vertical connectors - simplified arrows */}
        <div className="absolute inset-0 pointer-events-none flex flex-col items-center justify-around py-16">
          {FLOW_LAYOUT.slice(0, -1).map((_, idx) => (
            <ChevronRight key={idx} className="w-5 h-5 text-gray-300 rotate-90 -my-2" />
          ))}
        </div>
      </div>

      {/* Footer */}
      <div className="px-6 py-3 border-t border-gray-100 bg-gray-50/30 flex items-center justify-between">
        <div className="flex items-center gap-4 text-xs text-gray-500">
          <span className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-full bg-emerald-500" /> Completed
          </span>
          <span className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" /> Running
          </span>
          <span className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-full bg-amber-500" /> Waiting
          </span>
          <span className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-full bg-gray-300" /> Pending
          </span>
        </div>
        <span className="text-xs font-mono text-gray-400">LangGraph Studio</span>
      </div>
    </div>
  );
}
