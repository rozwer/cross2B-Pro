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
  ThumbsUp,
  ThumbsDown,
  X,
  RotateCcw,
  Play,
  Image,
  type LucideIcon,
} from "lucide-react";
import type { Step } from "@/lib/types";
import { STEP_LABELS, normalizeStepName } from "@/lib/types";
import { cn } from "@/lib/utils";
import { SUB_STEPS, getSubStepStatus } from "./subStepsData";

/**
 * Pattern 5: Radial/Circular Progress
 * - Center hub with overall progress
 * - Steps arranged in a circle
 * - Arc connections with gradients
 * - Futuristic mission control aesthetic
 * - Click node to show inline sub-step details
 */

interface WorkflowPattern5Props {
  steps: Step[];
  currentStep: string;
  runStatus?: string;
  waitingApproval: boolean;
  waitingImageGeneration?: boolean;
  onApprove?: () => void;
  onReject?: (reason: string) => void;
  onStepClick?: (stepName: string) => void;
  onRetry?: (stepName: string) => void;
  onResumeFrom?: (stepName: string) => void;
  onImageGenerate?: () => void;
  onImageGenSkip?: () => void;
}

const STEP_CONFIG: Record<string, { icon: LucideIcon; color: string }> = {
  "step-1": { icon: Package, color: "#3b82f6" },
  step0: { icon: Sparkles, color: "#8b5cf6" },
  step1: { icon: Search, color: "#a855f7" },
  "step1.5": { icon: Search, color: "#a855f7" },
  step2: { icon: Search, color: "#f59e0b" },
  step3: { icon: FileText, color: "#10b981" },
  step3a: { icon: Sparkles, color: "#ec4899" },
  step3b: { icon: Sparkles, color: "#ec4899" },
  step3c: { icon: Sparkles, color: "#ec4899" },
  "step3.5": { icon: Sparkles, color: "#06b6d4" },
  step4: { icon: FileText, color: "#06b6d4" },
  step5: { icon: Pencil, color: "#8b5cf6" },
  step6: { icon: Eye, color: "#f59e0b" },
  "step6.5": { icon: Package, color: "#6366f1" },
  step7a: { icon: FileText, color: "#10b981" },
  step7b: { icon: FileText, color: "#22c55e" },
  step8: { icon: Eye, color: "#eab308" },
  step9: { icon: Sparkles, color: "#a855f7" },
  step10: { icon: CheckCircle, color: "#10b981" },
  step11: { icon: Image, color: "#ec4899" },
  step12: { icon: FileText, color: "#10b981" },
};

// Simplified steps for radial view
const RADIAL_STEPS = [
  "step-1",
  "step0",
  "step1",
  "step1.5",
  "step2",
  "step3a",
  "step3b",
  "step3c",
  "step3.5",
  "step4",
  "step5",
  "step6",
  "step6.5",
  "step7a",
  "step7b",
  "step8",
  "step9",
  "step10",
  "step11",
  "step12",
];

// Parallel step groups: parent step is completed when ALL children are completed
const PARALLEL_PARENT_CHILDREN: Record<string, string[]> = {
  step3: ["step3a", "step3b", "step3c"],
  step7: ["step7a", "step7b"],
};

// Key steps to show labels for (evenly distributed around the circle)
const KEY_LABEL_STEPS = ["step-1", "step4", "step7a", "step10", "step12"];

// All step names for progress calculation (from STEP_LABELS)
const ALL_STEP_NAMES = Object.keys(STEP_LABELS);

export function WorkflowPattern5_RadialProgress({
  steps,
  currentStep,
  runStatus,
  waitingApproval,
  waitingImageGeneration,
  onApprove,
  onReject,
  onRetry,
  onResumeFrom,
  onImageGenerate,
  onImageGenSkip,
}: WorkflowPattern5Props) {
  // Normalize step names (step6_5 -> step6.5) for consistent lookup
  const stepMap = new Map(steps.map((s) => [normalizeStepName(s.step_name), s]));

  // Selected step for detail view
  const [selectedStep, setSelectedStep] = useState<string | null>(null);

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

  // Calculate positions for radial layout
  const centerX = 200;
  const centerY = 200;
  const radius = 150;
  const stepPositions = RADIAL_STEPS.map((step, index) => {
    const angle = (index / RADIAL_STEPS.length) * 2 * Math.PI - Math.PI / 2;
    return {
      step,
      x: centerX + radius * Math.cos(angle),
      y: centerY + radius * Math.sin(angle),
      angle,
    };
  });

  const getStatusStyle = (status?: string, isWaiting?: boolean) => {
    if (isWaiting)
      return { stroke: "#f59e0b", fill: "#f59e0b", glow: "drop-shadow(0 0 8px #f59e0b)" };
    switch (status) {
      case "completed":
        return { stroke: "#10b981", fill: "#10b981", glow: "drop-shadow(0 0 6px #10b981)" };
      case "running":
        return { stroke: "#06b6d4", fill: "#06b6d4", glow: "drop-shadow(0 0 10px #06b6d4)" };
      case "failed":
        return { stroke: "#ef4444", fill: "#ef4444", glow: "drop-shadow(0 0 8px #ef4444)" };
      default:
        return { stroke: "#4b5563", fill: "#374151", glow: "" };
    }
  };

  // Progress ring calculation
  const progressRadius = 70;
  const progressCircumference = 2 * Math.PI * progressRadius;
  const progressOffset = progressCircumference - (progress / 100) * progressCircumference;

  const handleNodeClick = (stepName: string) => {
    setSelectedStep(selectedStep === stepName ? null : stepName);
  };

  const selectedSubSteps = selectedStep ? SUB_STEPS[selectedStep] || [] : [];
  // Use effective status for selected step (handles always-completed and parent-child)
  const selectedEffectiveStatus = selectedStep ? getEffectiveStatus(selectedStep) : undefined;

  return (
    <div className="rounded-2xl overflow-hidden bg-gradient-to-br from-gray-50 via-gray-100 to-gray-50 dark:from-indigo-950 dark:via-slate-900 dark:to-indigo-950">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200 dark:border-white/10">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-cyan-500 flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-gray-900 dark:text-white">ミッションコントロール</h3>
              <p className="text-sm text-gray-500 dark:text-gray-400">SEO Article Generation Pipeline</p>
            </div>
          </div>
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-gray-200 dark:bg-white/10">
            <span
              className={cn(
                "w-2 h-2 rounded-full",
                steps.some((s) => s.status === "failed")
                  ? "bg-red-500"
                  : steps.some((s) => s.status === "running")
                    ? "bg-cyan-500 animate-pulse"
                    : steps.every((s) => s.status === "completed")
                      ? "bg-emerald-500"
                      : "bg-amber-500",
              )}
            />
            <span className="text-sm text-gray-900 dark:text-white font-medium">
              {steps.some((s) => s.status === "failed")
                ? "失敗"
                : steps.some((s) => s.status === "running")
                  ? "実行中"
                  : steps.every((s) => s.status === "completed")
                    ? "完了"
                    : "処理中"}
            </span>
          </div>
        </div>
      </div>

      {/* Radial View + Detail Panel */}
      <div className="relative p-8 flex items-start justify-center gap-4">
        <svg width="400" height="400" className="overflow-visible flex-shrink-0">
          <defs>
            {/* Glow filter */}
            <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
            {/* Gradient for progress ring */}
            <linearGradient id="progressGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#06b6d4" />
              <stop offset="50%" stopColor="#8b5cf6" />
              <stop offset="100%" stopColor="#10b981" />
            </linearGradient>
          </defs>

          {/* Background circles */}
          <circle
            cx={centerX}
            cy={centerY}
            r="180"
            fill="none"
            className="stroke-gray-200/50 dark:stroke-white/[0.03]"
            strokeWidth="40"
          />
          <circle
            cx={centerX}
            cy={centerY}
            r="120"
            fill="none"
            className="stroke-gray-300/50 dark:stroke-white/[0.02]"
            strokeWidth="1"
          />

          {/* Connection arcs */}
          {stepPositions.map((pos, index) => {
            const nextPos = stepPositions[(index + 1) % stepPositions.length];
            // Use effective status for connection arc display
            const isCompleted = getEffectiveStatus(pos.step) === "completed";

            return (
              <path
                key={`arc-${index}`}
                d={`M ${pos.x} ${pos.y} Q ${centerX} ${centerY} ${nextPos.x} ${nextPos.y}`}
                fill="none"
                stroke={isCompleted ? STEP_CONFIG[pos.step]?.color || "#8b5cf6" : "#374151"}
                strokeWidth="2"
                strokeDasharray={isCompleted ? "0" : "4 4"}
                opacity={isCompleted ? 0.6 : 0.3}
              />
            );
          })}

          {/* Step nodes */}
          {stepPositions.map((pos) => {
            const step = stepMap.get(pos.step);
            // Get effective status using helper (handles always-completed and parent-child)
            const status = getEffectiveStatus(pos.step);
            const isCurrent = pos.step === currentStep;
            const isWaiting = waitingApproval && isCurrent;
            const isSelected = selectedStep === pos.step;
            const config = STEP_CONFIG[pos.step];
            const statusStyle = getStatusStyle(status, isWaiting);
            const Icon = config?.icon || Sparkles;

            return (
              <g
                key={pos.step}
                transform={`translate(${pos.x}, ${pos.y})`}
                onClick={() => handleNodeClick(pos.step)}
                className="cursor-pointer"
                style={{ cursor: "pointer" }}
              >
                {/* Selection ring */}
                {isSelected && (
                  <circle
                    r="26"
                    fill="none"
                    stroke="#8b5cf6"
                    strokeWidth="2"
                    strokeDasharray="4 2"
                  />
                )}
                {/* Hover area */}
                <circle r="22" fill="transparent" className="hover:fill-white/5" />
                {/* Outer glow for active */}
                {(status === "running" || isWaiting) && (
                  <circle
                    r="24"
                    fill="none"
                    stroke={statusStyle.stroke}
                    strokeWidth="2"
                    opacity="0.5"
                    className="animate-pulse"
                  />
                )}
                {/* Node background */}
                <circle
                  r="18"
                  fill={status ? statusStyle.fill : "#1f2937"}
                  stroke={isSelected ? "#8b5cf6" : statusStyle.stroke}
                  strokeWidth={isSelected ? 3 : 2}
                  style={{ filter: status ? statusStyle.glow : "" }}
                />
                {/* Icon */}
                <foreignObject x="-10" y="-10" width="20" height="20">
                  <div className="w-full h-full flex items-center justify-center">
                    {status === "running" ? (
                      <Loader2 className="w-4 h-4 text-white animate-spin" />
                    ) : status === "completed" ? (
                      <CheckCircle className="w-4 h-4 text-white" />
                    ) : isWaiting ? (
                      <Pause className="w-4 h-4 text-white" />
                    ) : status === "failed" ? (
                      <XCircle className="w-4 h-4 text-white" />
                    ) : (
                      <Icon className="w-4 h-4 text-gray-400" />
                    )}
                  </div>
                </foreignObject>
              </g>
            );
          })}

          {/* Center hub */}
          <g transform={`translate(${centerX}, ${centerY})`}>
            {/* Background */}
            <circle r="85" className="fill-white dark:fill-slate-900 stroke-gray-200 dark:stroke-white/10" strokeWidth="1" />
            {/* Progress track */}
            <circle r={progressRadius} fill="none" className="stroke-gray-200 dark:stroke-white/10" strokeWidth="8" />
            {/* Progress ring */}
            <circle
              r={progressRadius}
              fill="none"
              stroke="url(#progressGradient)"
              strokeWidth="8"
              strokeLinecap="round"
              strokeDasharray={progressCircumference}
              strokeDashoffset={progressOffset}
              transform="rotate(-90)"
              style={{ transition: "stroke-dashoffset 0.5s ease-out" }}
            />
            {/* Center text */}
            <text y="-8" textAnchor="middle" className="text-4xl font-bold fill-gray-900 dark:fill-white">
              {progress}%
            </text>
            <text y="15" textAnchor="middle" className="text-sm fill-gray-500 dark:fill-gray-400">
              完了
            </text>
            <text y="35" textAnchor="middle" className="text-xs fill-gray-400 dark:fill-gray-500">
              {completedCount} / {totalSteps}
            </text>
          </g>
        </svg>

        {/* Detail Panel - appears when step is selected */}
        {selectedStep && (
          <div
            className={cn(
              "w-64 rounded-xl",
              "bg-white dark:bg-slate-900/95 backdrop-blur-lg border border-gray-200 dark:border-white/20",
              "shadow-xl shadow-gray-200/50 dark:shadow-black/30 overflow-hidden",
            )}
          >
            {/* Panel header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 dark:border-white/10">
              <div className="flex items-center gap-2">
                <div
                  className="w-6 h-6 rounded-lg flex items-center justify-center"
                  style={{ backgroundColor: `${STEP_CONFIG[selectedStep]?.color}30` }}
                >
                  {(() => {
                    const Icon = STEP_CONFIG[selectedStep]?.icon || Sparkles;
                    return (
                      <Icon
                        className="w-3.5 h-3.5"
                        style={{ color: STEP_CONFIG[selectedStep]?.color }}
                      />
                    );
                  })()}
                </div>
                <span className="text-sm font-medium text-gray-900 dark:text-white truncate">
                  {STEP_LABELS[selectedStep]}
                </span>
              </div>
              <button
                onClick={() => setSelectedStep(null)}
                className="p-1 hover:bg-gray-100 dark:hover:bg-white/10 rounded transition-colors"
              >
                <X className="w-4 h-4 text-gray-400" />
              </button>
            </div>

            {/* Sub-steps */}
            <div className="p-3 max-h-[300px] overflow-y-auto">
              {selectedSubSteps.length > 0 ? (
                <div className="space-y-1.5">
                  {selectedSubSteps.map((subStep, idx) => {
                    const subStatus = getSubStepStatus(
                      selectedEffectiveStatus,
                      idx,
                      selectedSubSteps.length,
                    );
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
                          {subStatus === "failed" && <XCircle className="w-2.5 h-2.5 text-white" />}
                          {subStatus === "pending" && <Clock className="w-2.5 h-2.5 text-white" />}
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
              ) : (
                <p className="text-xs text-gray-400 dark:text-gray-500 text-center py-4">サブステップなし</p>
              )}
            </div>

            {/* Status info and action buttons */}
            {selectedStep && (
              <div className="px-3 pb-3 space-y-2">
                <div
                  className={cn(
                    "p-2 rounded-lg text-xs",
                    selectedEffectiveStatus === "completed" && "bg-emerald-100 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
                    selectedEffectiveStatus === "running" && "bg-cyan-100 dark:bg-cyan-500/10 text-cyan-600 dark:text-cyan-400",
                    selectedEffectiveStatus === "failed" && "bg-red-100 dark:bg-red-500/10 text-red-600 dark:text-red-400",
                    !selectedEffectiveStatus && "bg-gray-100 dark:bg-gray-500/10 text-gray-600 dark:text-gray-400",
                  )}
                >
                  {selectedEffectiveStatus === "completed" && "✓ 完了"}
                  {selectedEffectiveStatus === "running" && "処理中..."}
                  {selectedEffectiveStatus === "failed" && "エラー発生"}
                  {!selectedEffectiveStatus && "待機中"}
                </div>

                {/* Step11: Image Generation Yes/No buttons - 常に表示 */}
                {selectedStep === "step11" && (
                  <div className="space-y-2 pt-2 border-t border-gray-200 dark:border-white/10">
                    <p className="text-xs font-medium text-purple-600 dark:text-purple-400">
                      画像を生成しますか？
                    </p>
                    <button
                      onClick={() => {
                        onImageGenerate?.();
                        setSelectedStep(null);
                      }}
                      className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 text-white text-xs font-medium rounded-lg transition-colors"
                    >
                      <Sparkles className="w-3.5 h-3.5" />
                      画像を生成する
                    </button>
                    <button
                      onClick={() => {
                        onImageGenSkip?.();
                        setSelectedStep(null);
                      }}
                      className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-gray-500 hover:bg-gray-600 text-white text-xs font-medium rounded-lg transition-colors"
                    >
                      スキップして完了
                    </button>
                  </div>
                )}

                {/* Action buttons - show retry for failed, resume for completed/failed */}
                {(selectedEffectiveStatus === "failed" || selectedEffectiveStatus === "completed") &&
                 (onRetry || onResumeFrom) && (
                  <div className="space-y-1.5 pt-2 border-t border-gray-200 dark:border-white/10">
                    {/* Retry button - only for failed */}
                    {selectedEffectiveStatus === "failed" && onRetry && (
                      <button
                        onClick={() => {
                          onRetry(selectedStep);
                          setSelectedStep(null);
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
                        onClick={() => {
                          onResumeFrom(selectedStep);
                          setSelectedStep(null);
                        }}
                        className={cn(
                          "w-full flex items-center justify-center gap-2 px-3 py-2 text-white text-xs font-medium rounded-lg transition-colors",
                          selectedEffectiveStatus === "failed"
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
        )}

        {/* Floating labels for key steps - rendered inside SVG for proper positioning */}
        {!selectedStep && (
          <svg
            width="400"
            height="400"
            className="absolute pointer-events-none"
            style={{ left: 0, top: 0 }}
          >
            {stepPositions
              .filter((pos) => KEY_LABEL_STEPS.includes(pos.step))
              .map((pos) => {
                // Use effective status for label styling
                const effectiveStatus = getEffectiveStatus(pos.step);
                // Position label outside the node
                const isRight = pos.x > centerX;
                const labelX = isRight ? pos.x + 28 : pos.x - 28;
                const labelY = pos.y;

                // Determine colors based on status
                let bgColor = "rgba(229, 231, 235, 0.8)"; // gray-200
                let textColor = "#6b7280"; // gray-500
                if (effectiveStatus === "completed") {
                  bgColor = "rgba(16, 185, 129, 0.2)"; // emerald-500/20
                  textColor = "#10b981"; // emerald-500
                } else if (effectiveStatus === "running") {
                  bgColor = "rgba(6, 182, 212, 0.2)"; // cyan-500/20
                  textColor = "#06b6d4"; // cyan-500
                }

                return (
                  <g key={`label-${pos.step}`}>
                    <rect
                      x={isRight ? labelX : labelX - 80}
                      y={labelY - 10}
                      width="80"
                      height="20"
                      rx="10"
                      fill={bgColor}
                    />
                    <text
                      x={isRight ? labelX + 40 : labelX - 40}
                      y={labelY + 4}
                      textAnchor="middle"
                      fontSize="11"
                      fontWeight="500"
                      fill={textColor}
                    >
                      {STEP_LABELS[pos.step]}
                    </text>
                  </g>
                );
              })}
          </svg>
        )}
      </div>

      {/* Action bar for approval */}
      {waitingApproval && (
        <div className="mx-6 mb-6 p-4 rounded-xl bg-amber-100 dark:bg-amber-500/10 border border-amber-300 dark:border-amber-500/30">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Pause className="w-5 h-5 text-amber-500" />
              <div>
                <p className="text-sm font-medium text-amber-600 dark:text-amber-400">承認が必要です</p>
                <p className="text-xs text-amber-500/70">レビュー結果を確認してください</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => onReject?.("ユーザーによる却下")}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-red-600 dark:text-red-400 bg-red-100 dark:bg-red-500/10 border border-red-300 dark:border-red-500/30 rounded-lg hover:bg-red-200 dark:hover:bg-red-500/20 transition-colors"
              >
                <ThumbsDown className="w-4 h-4" />
                却下
              </button>
              <button
                onClick={onApprove}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-emerald-600 rounded-lg hover:bg-emerald-500 transition-colors"
              >
                <ThumbsUp className="w-4 h-4" />
                承認
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="px-6 py-3 border-t border-gray-200 dark:border-white/10 flex items-center justify-between text-xs">
        <span className="text-gray-500">ノードをクリックで詳細表示</span>
        <div className="flex items-center gap-4 text-gray-500 dark:text-gray-400">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-emerald-500" /> 完了
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-cyan-500 animate-pulse" /> 実行中
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-amber-500" /> 待機中
          </span>
        </div>
      </div>
    </div>
  );
}
