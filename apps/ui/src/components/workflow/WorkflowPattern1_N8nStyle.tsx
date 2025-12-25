"use client";

import { useState } from "react";
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
  ChevronDown,
  ChevronRight,
  RotateCcw,
  Play,
  Image,
  type LucideIcon,
} from "lucide-react";
import type { Step } from "@/lib/types";
import { STEP_LABELS, STEP_NAMES, normalizeStepName } from "@/lib/types";
import { cn } from "@/lib/utils";
import { SUB_STEPS, getSubStepStatus } from "./subStepsData";

/**
 * Pattern 1: n8n Style
 * - Dark glassmorphism theme
 * - Horizontal flow with curved bezier connections
 * - Nodes as rounded cards with glow effects
 * - Click to expand inline sub-steps
 */

interface WorkflowPattern1Props {
  steps: Step[];
  currentStep: string;
  runStatus?: string;
  waitingApproval: boolean;
  waitingImageGeneration?: boolean;
  onStepClick?: (stepName: string) => void;
  onRetry?: (stepName: string) => void;
  onResumeFrom?: (stepName: string) => void;
  onImageGenerate?: () => void;
  onImageGenSkip?: () => void;
}

const STEP_ICONS: Record<string, LucideIcon> = {
  "step-1": Package,
  step0: Sparkles,
  step1: Search,
  "step1.5": Search,
  step3: FileText,
  step2: Search,
  step3a: Sparkles,
  step3b: Sparkles,
  step3c: Sparkles,
  "step3.5": Sparkles,
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
  step12: FileText,
};

const STEP_COLORS: Record<string, string> = {
  "step-1": "#3b82f6",
  step0: "#8b5cf6",
  step1: "#8b5cf6",
  step3: "#10b981",
  step2: "#10b981",
  step3a: "#f59e0b",
  step3b: "#f59e0b",
  step3c: "#f59e0b",
  "step3.5": "#06b6d4",
  step4: "#06b6d4",
  step5: "#06b6d4",
  step6: "#ec4899",
  "step6.5": "#8b5cf6",
  step7a: "#10b981",
  step7b: "#10b981",
  step8: "#f59e0b",
  step9: "#8b5cf6",
  step10: "#10b981",
  step11: "#ec4899",
  step12: "#10b981",
};

// Simplified step groups for visualization
const STEP_GROUPS = [
  ["step-1"],
  ["step0"],
  ["step1"],
  ["step1.5"],
  ["step2", "step3"],
  ["step3a", "step3b", "step3c"],
  ["step3.5"],
  ["step4"],
  ["step5"],
  ["step6"],
  ["step6.5"],
  ["step7a", "step7b"],
  ["step8"],
  ["step9"],
  ["step10"],
  ["step11"],
  ["step12"],
];

function getStatusIcon(status?: string, isWaiting?: boolean) {
  if (isWaiting) return Pause;
  switch (status) {
    case "completed":
      return CheckCircle;
    case "failed":
      return XCircle;
    case "running":
      return Loader2;
    default:
      return Clock;
  }
}

// Parallel step groups: parent step is completed when ALL children are completed
const PARALLEL_PARENT_CHILDREN: Record<string, string[]> = {
  step3: ["step3a", "step3b", "step3c"],
  step7: ["step7a", "step7b"],
};

// All step names for progress calculation (use STEP_NAMES to avoid duplicates)
const ALL_STEP_NAMES = [...STEP_NAMES];

export function WorkflowPattern1_N8nStyle({
  steps,
  currentStep,
  runStatus,
  waitingApproval,
  waitingImageGeneration,
  onRetry,
  onResumeFrom,
  onImageGenerate,
  onImageGenSkip,
}: WorkflowPattern1Props) {
  // Normalize step names (step6_5 -> step6.5) for consistent lookup
  const stepMap = new Map(steps.map((s) => [normalizeStepName(s.step_name), s]));

  // Track expanded steps
  const [expandedStep, setExpandedStep] = useState<string | null>(null);

  // Helper: Get effective status for a step (handles parent-child relationships)
  // If the run has failed, treat "running" steps as "failed"
  const getEffectiveStatus = (stepName: string): string | undefined => {
    // Always completed steps (input/preparation)
    const alwaysCompletedSteps = ["step-1", "step0"];
    if (alwaysCompletedSteps.includes(stepName)) {
      return "completed";
    }

    // Helper to adjust status based on run status
    const adjustForRunFailure = (status: string | undefined): string | undefined => {
      if (runStatus === "failed" && status === "running") {
        return "failed";
      }
      return status;
    };

    // Check if this is a parent step with parallel children
    const children = PARALLEL_PARENT_CHILDREN[stepName];
    if (children) {
      // Parent is completed when ALL children are completed
      const allChildrenCompleted = children.every(
        (childName) => stepMap.get(childName)?.status === "completed"
      );
      if (allChildrenCompleted) {
        return "completed";
      }
      // Parent is running if any child is running (but check run failure)
      const anyChildRunning = children.some(
        (childName) => stepMap.get(childName)?.status === "running"
      );
      if (anyChildRunning) {
        return adjustForRunFailure("running");
      }
      // Parent is failed if any child failed (and none running)
      const anyChildFailed = children.some(
        (childName) => stepMap.get(childName)?.status === "failed"
      );
      if (anyChildFailed) {
        return "failed";
      }
      // Otherwise pending
      return "pending";
    }

    // Regular step: use actual status, adjusted for run failure
    return adjustForRunFailure(stepMap.get(stepName)?.status);
  };

  // Calculate progress using effective status for all steps
  const completedCount = ALL_STEP_NAMES.filter(
    (name) => getEffectiveStatus(name) === "completed"
  ).length;
  const totalSteps = ALL_STEP_NAMES.length;
  const progress = Math.round((completedCount / totalSteps) * 100);

  const handleStepClick = (stepName: string) => {
    setExpandedStep(expandedStep === stepName ? null : stepName);
  };

  return (
    <div className="rounded-2xl overflow-hidden bg-gradient-to-br from-gray-50 to-gray-100 dark:from-slate-900 dark:to-indigo-950">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200 dark:border-white/10">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center">
              <Sparkles className="w-4 h-4 text-white" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-gray-900 dark:text-white">ワークフロー</h3>
              <p className="text-xs text-gray-500 dark:text-gray-400">SEO Article Generation</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-2xl font-bold text-gray-900 dark:text-white">{progress}%</span>
            <span className="text-xs text-gray-500 dark:text-gray-400">完了</span>
          </div>
        </div>
        {/* Progress bar */}
        <div className="h-1.5 bg-gray-200 dark:bg-white/10 rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{
              width: `${progress}%`,
              background: "linear-gradient(90deg, #8b5cf6 0%, #06b6d4 50%, #10b981 100%)",
            }}
          />
        </div>
      </div>

      {/* Flow Canvas */}
      <div className="p-6 overflow-x-auto">
        <div className="flex items-start gap-2 min-w-max">
          {STEP_GROUPS.map((group, groupIndex) => (
            <div key={groupIndex} className="flex items-start gap-2">
              {/* Node Group */}
              <div className={cn("flex gap-2", group.length > 1 ? "flex-col" : "")}>
                {group.map((stepName) => {
                  const step = stepMap.get(stepName);
                  // Get effective status using helper (handles always-completed and parent-child)
                  const status = getEffectiveStatus(stepName);
                  const isCurrent = stepName === currentStep;
                  const isWaiting = waitingApproval && isCurrent;
                  const Icon = STEP_ICONS[stepName] || Sparkles;
                  const StatusIcon = getStatusIcon(status, isWaiting);
                  const color = STEP_COLORS[stepName] || "#8b5cf6";
                  const isExpanded = expandedStep === stepName;
                  const subSteps = SUB_STEPS[stepName] || [];

                  return (
                    <div key={stepName} className="relative">
                      <button
                        onClick={() => handleStepClick(stepName)}
                        className={cn(
                          "relative group text-left",
                          "px-4 py-3 rounded-xl",
                          "border transition-all duration-300",
                          "backdrop-blur-sm cursor-pointer",
                          "hover:scale-105 hover:z-10",
                          status === "completed" &&
                            "bg-emerald-50 dark:bg-white/5 border-emerald-500/50 hover:border-emerald-400",
                          status === "running" &&
                            "bg-cyan-50 dark:bg-white/10 border-cyan-500/50 hover:border-cyan-400",
                          status === "failed" &&
                            "bg-red-50 dark:bg-white/5 border-red-500/50 hover:border-red-400",
                          isWaiting && "bg-amber-50 dark:bg-amber-500/10 border-amber-500/50 hover:border-amber-400",
                          !status && "bg-gray-50 dark:bg-white/5 border-gray-200 dark:border-white/10 opacity-50 hover:opacity-70",
                          isCurrent && !isWaiting && "ring-2 ring-cyan-500/50",
                          isExpanded && "ring-2 ring-violet-500/50",
                        )}
                        style={{
                          boxShadow:
                            status === "completed"
                              ? `0 0 20px ${color}30`
                              : status === "running"
                                ? `0 0 30px ${color}40`
                                : "none",
                        }}
                      >
                        <div className="flex items-center gap-3">
                          {/* Icon */}
                          <div
                            className="w-8 h-8 rounded-lg flex items-center justify-center"
                            style={{ backgroundColor: `${color}20` }}
                          >
                            <Icon className="w-4 h-4" style={{ color }} />
                          </div>
                          {/* Label */}
                          <div className="min-w-[80px]">
                            <p className="text-xs font-medium text-gray-900 dark:text-white truncate">
                              {STEP_LABELS[stepName]}
                            </p>
                          </div>
                          {/* Status indicator */}
                          <div
                            className={cn(
                              "w-5 h-5 rounded-full flex items-center justify-center",
                              status === "completed" && "bg-emerald-500",
                              status === "running" && "bg-cyan-500",
                              status === "failed" && "bg-red-500",
                              isWaiting && "bg-amber-500",
                              !status && "bg-gray-600",
                            )}
                          >
                            <StatusIcon
                              className={cn(
                                "w-3 h-3 text-white",
                                status === "running" && "animate-spin",
                              )}
                            />
                          </div>
                          {/* Expand indicator */}
                          {subSteps.length > 0 && (
                            <div className="text-gray-400 dark:text-white/50">
                              {isExpanded ? (
                                <ChevronDown className="w-4 h-4" />
                              ) : (
                                <ChevronRight className="w-4 h-4" />
                              )}
                            </div>
                          )}
                        </div>

                        {/* Glow effect for running */}
                        {status === "running" && (
                          <div
                            className="absolute inset-0 rounded-xl animate-pulse-soft pointer-events-none"
                            style={{ boxShadow: `0 0 30px ${color}50` }}
                          />
                        )}
                      </button>

                      {/* Expanded Sub-steps */}
                      {isExpanded && subSteps.length > 0 && (
                        <div
                          className={cn(
                            "absolute left-0 top-full mt-2 z-20",
                            "min-w-[200px] p-3 rounded-xl",
                            "bg-white dark:bg-slate-900/95 backdrop-blur-lg border border-gray-200 dark:border-white/20",
                            "shadow-xl shadow-gray-200/50 dark:shadow-black/30",
                          )}
                        >
                          <div className="text-xs font-medium text-gray-600 dark:text-white/70 mb-2 px-1">
                            内部ステップ
                          </div>
                          <div className="space-y-1.5">
                            {subSteps.map((subStep, idx) => {
                              const subStatus = getSubStepStatus(status, idx, subSteps.length);
                              return (
                                <div
                                  key={subStep.id}
                                  className={cn(
                                    "flex items-center gap-2 px-2 py-1.5 rounded-lg",
                                    "transition-colors",
                                    subStatus === "completed" && "bg-emerald-100 dark:bg-emerald-500/10",
                                    subStatus === "running" && "bg-cyan-100 dark:bg-cyan-500/10",
                                    subStatus === "failed" && "bg-red-100 dark:bg-red-500/10",
                                    subStatus === "pending" && "bg-gray-100 dark:bg-white/5 opacity-50",
                                  )}
                                >
                                  <div
                                    className={cn(
                                      "w-4 h-4 rounded-full flex items-center justify-center flex-shrink-0",
                                      subStatus === "completed" && "bg-emerald-500",
                                      subStatus === "running" && "bg-cyan-500",
                                      subStatus === "failed" && "bg-red-500",
                                      subStatus === "pending" && "bg-gray-600",
                                    )}
                                  >
                                    {subStatus === "completed" && (
                                      <CheckCircle className="w-2.5 h-2.5 text-white" />
                                    )}
                                    {subStatus === "running" && (
                                      <Loader2 className="w-2.5 h-2.5 text-white animate-spin" />
                                    )}
                                    {subStatus === "failed" && (
                                      <XCircle className="w-2.5 h-2.5 text-white" />
                                    )}
                                    {subStatus === "pending" && (
                                      <Clock className="w-2.5 h-2.5 text-white" />
                                    )}
                                  </div>
                                  <div className="flex-1 min-w-0">
                                    <p
                                      className={cn(
                                        "text-xs font-medium truncate",
                                        subStatus === "completed" && "text-emerald-400",
                                        subStatus === "running" && "text-cyan-400",
                                        subStatus === "failed" && "text-red-400",
                                        subStatus === "pending" && "text-gray-400",
                                      )}
                                    >
                                      {subStep.name}
                                    </p>
                                  </div>
                                  {subStatus === "running" && (
                                    <span className="text-[10px] text-cyan-400">処理中</span>
                                  )}
                                </div>
                              );
                            })}
                          </div>

                          {/* Step11: Image Generation Yes/No buttons - 常に表示 */}
                          {stepName === "step11" && (
                            <div className="mt-3 pt-3 border-t border-gray-200 dark:border-white/10 space-y-2">
                              <div className="text-xs font-medium text-purple-600 dark:text-purple-400 mb-2">
                                画像を生成しますか？
                              </div>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  onImageGenerate?.();
                                }}
                                className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 text-white text-xs font-medium rounded-lg transition-colors"
                              >
                                <Sparkles className="w-3.5 h-3.5" />
                                画像を生成する
                              </button>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  onImageGenSkip?.();
                                }}
                                className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-gray-500 hover:bg-gray-600 text-white text-xs font-medium rounded-lg transition-colors"
                              >
                                スキップして完了
                              </button>
                            </div>
                          )}

                          {/* Action buttons for completed or failed steps */}
                          {(status === "completed" || status === "failed") && (onRetry || onResumeFrom) && (
                            <div className="mt-3 pt-3 border-t border-gray-200 dark:border-white/10 space-y-2">
                              {status === "failed" && (
                                <div className="text-xs font-medium text-red-500 dark:text-red-400 mb-2">
                                  このステップで失敗しました
                                </div>
                              )}
                              {/* Retry button - only for failed */}
                              {status === "failed" && onRetry && (
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    onRetry(stepName);
                                  }}
                                  className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-red-500 hover:bg-red-600 text-white text-xs font-medium rounded-lg transition-colors"
                                >
                                  <RotateCcw className="w-3.5 h-3.5" />
                                  このステップを再実行
                                </button>
                              )}
                              {/* Resume button - for completed or failed */}
                              {onResumeFrom && (
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    onResumeFrom(stepName);
                                  }}
                                  className={cn(
                                    "w-full flex items-center justify-center gap-2 px-3 py-2 text-white text-xs font-medium rounded-lg transition-colors",
                                    status === "failed"
                                      ? "bg-gray-500 hover:bg-gray-600"
                                      : "bg-violet-500 hover:bg-violet-600"
                                  )}
                                >
                                  <Play className="w-3.5 h-3.5" />
                                  ここから再開
                                </button>
                              )}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>

              {/* Connector */}
              {groupIndex < STEP_GROUPS.length - 1 && (
                <div className="flex items-center pt-3">
                  <svg width="40" height="20" className="text-white/30">
                    <defs>
                      <linearGradient id={`grad-${groupIndex}`} x1="0%" y1="0%" x2="100%" y2="0%">
                        <stop
                          offset="0%"
                          stopColor={STEP_COLORS[group[0]] || "#8b5cf6"}
                          stopOpacity="0.5"
                        />
                        <stop
                          offset="100%"
                          stopColor={STEP_COLORS[STEP_GROUPS[groupIndex + 1]?.[0]] || "#8b5cf6"}
                          stopOpacity="0.5"
                        />
                      </linearGradient>
                    </defs>
                    <path
                      d="M 0 10 Q 20 10 40 10"
                      stroke={`url(#grad-${groupIndex})`}
                      strokeWidth="2"
                      fill="none"
                      strokeDasharray={
                        stepMap.get(group[group.length - 1])?.status === "completed" ? "0" : "4 4"
                      }
                    />
                    <polygon
                      points="35,7 40,10 35,13"
                      fill={STEP_COLORS[STEP_GROUPS[groupIndex + 1]?.[0]] || "#8b5cf6"}
                      opacity="0.5"
                    />
                  </svg>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Legend */}
      <div className="px-6 py-3 border-t border-gray-200 dark:border-white/10 flex items-center gap-6 text-xs">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-emerald-500" />
          <span className="text-gray-500 dark:text-gray-400">完了</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-cyan-500 animate-pulse" />
          <span className="text-gray-500 dark:text-gray-400">実行中</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-amber-500" />
          <span className="text-gray-500 dark:text-gray-400">承認待ち</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-gray-400 dark:bg-gray-600" />
          <span className="text-gray-500 dark:text-gray-400">待機中</span>
        </div>
        <div className="ml-auto text-gray-400 dark:text-gray-500">クリックで内部ステップを表示</div>
      </div>
    </div>
  );
}
