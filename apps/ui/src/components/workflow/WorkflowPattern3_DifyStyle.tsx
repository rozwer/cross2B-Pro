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
  Brain,
  Wrench,
  ArrowRight,
  Inbox,
  ThumbsUp,
  ThumbsDown,
  Maximize2,
  Image,
  type LucideIcon,
} from "lucide-react";
import type { Step } from "@/lib/types";
import { STEP_LABELS, STEP_NAMES, normalizeStepName } from "@/lib/types";
import { cn } from "@/lib/utils";

/**
 * Pattern 3: Dify Style
 * - Canvas layout with zoom controls
 * - Cards with colored left border
 * - Friendly, approachable design
 * - Japanese labels with status pills
 * - Mini-map and action bar
 */

interface WorkflowPattern3Props {
  steps: Step[];
  currentStep: string;
  waitingApproval: boolean;
  onApprove?: () => void;
  onReject?: (reason: string) => void;
}

const STEP_TYPES: Record<string, { icon: LucideIcon; color: string; type: string }> = {
  "step-1": { icon: Inbox, color: "#3b82f6", type: "入力" },
  step0: { icon: Sparkles, color: "#8b5cf6", type: "AI" },
  step1: { icon: Search, color: "#8b5cf6", type: "AI" },
  "step1.5": { icon: Search, color: "#8b5cf6", type: "AI" },
  step3: { icon: FileText, color: "#10b981", type: "処理" },
  step2: { icon: Wrench, color: "#f59e0b", type: "ツール" },
  step3a: { icon: Brain, color: "#ec4899", type: "AI" },
  step3b: { icon: Brain, color: "#ec4899", type: "AI" },
  step3c: { icon: Brain, color: "#ec4899", type: "AI" },
  "step3.5": { icon: Sparkles, color: "#06b6d4", type: "AI" },
  step4: { icon: FileText, color: "#06b6d4", type: "処理" },
  step5: { icon: Pencil, color: "#8b5cf6", type: "AI" },
  step6: { icon: Eye, color: "#f59e0b", type: "レビュー" },
  "step6.5": { icon: Package, color: "#6366f1", type: "処理" },
  step7a: { icon: FileText, color: "#10b981", type: "出力" },
  step7b: { icon: FileText, color: "#10b981", type: "出力" },
  step8: { icon: Eye, color: "#f59e0b", type: "検証" },
  step9: { icon: Sparkles, color: "#8b5cf6", type: "AI" },
  step10: { icon: ArrowRight, color: "#10b981", type: "完了" },
  step11: { icon: Image, color: "#ec4899", type: "出力" },
  step12: { icon: FileText, color: "#10b981", type: "出力" },
};

const FLOW_ROWS = [
  ["step-1"],
  ["step0", "step1", "step1.5"],
  ["step2", "step3"],
  ["step3a", "step3b", "step3c"],
  ["step3.5"],
  ["step4", "step5"],
  ["step6", "step6.5"],
  ["step7a", "step7b"],
  ["step8", "step9"],
  ["step10", "step11", "step12"],
];

export function WorkflowPattern3_DifyStyle({
  steps,
  currentStep,
  waitingApproval,
  onApprove,
  onReject,
}: WorkflowPattern3Props) {
  // Normalize step names (step6_5 -> step6.5) for consistent lookup
  const stepMap = new Map(steps.map((s) => [normalizeStepName(s.step_name), s]));
  const completedCount = steps.filter((s) => s.status === "completed").length;
  const totalSteps = STEP_NAMES.length;
  const progress = Math.round((completedCount / totalSteps) * 100);

  const getStatusPill = (status?: string, isWaiting?: boolean) => {
    if (isWaiting)
      return { label: "承認待ち", bg: "bg-amber-100", text: "text-amber-700", dot: "bg-amber-500" };
    switch (status) {
      case "completed":
        return {
          label: "完了",
          bg: "bg-emerald-100",
          text: "text-emerald-700",
          dot: "bg-emerald-500",
        };
      case "running":
        return { label: "実行中", bg: "bg-blue-100", text: "text-blue-700", dot: "bg-blue-500" };
      case "retrying":
        return { label: "リトライ中", bg: "bg-orange-100", text: "text-orange-700", dot: "bg-orange-500" };
      case "failed":
        return { label: "失敗", bg: "bg-red-100", text: "text-red-700", dot: "bg-red-500" };
      default:
        return { label: "待機", bg: "bg-gray-100", text: "text-gray-500", dot: "bg-gray-400" };
    }
  };

  return (
    <div className="rounded-2xl overflow-hidden bg-gradient-to-br from-slate-50 to-violet-50/30 border border-gray-200">
      {/* Header */}
      <div className="px-6 py-4 bg-white/80 backdrop-blur-sm border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center shadow-lg shadow-violet-500/25">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-gray-900">SEO記事生成ワークフロー</h3>
              <p className="text-sm text-gray-500">キーワード分析 → 記事生成 → レビュー</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="text-right">
              <p className="text-2xl font-bold text-violet-600">{progress}%</p>
              <p className="text-xs text-gray-500">
                {completedCount} / {totalSteps} ステップ
              </p>
            </div>
            <button className="p-2 hover:bg-gray-100 rounded-lg transition-colors">
              <Maximize2 className="w-4 h-4 text-gray-500" />
            </button>
          </div>
        </div>
      </div>

      {/* Canvas */}
      <div className="relative p-8 min-h-[400px] overflow-auto">
        <div className="flex flex-col gap-4 items-center">
          {FLOW_ROWS.map((row, rowIndex) => (
            <div key={rowIndex} className="flex items-center gap-4">
              {row.map((stepName) => {
                const step = stepMap.get(stepName);
                const status = step?.status;
                const isCurrent = stepName === currentStep;
                const isWaiting = waitingApproval && isCurrent;
                const config = STEP_TYPES[stepName] || {
                  icon: Sparkles,
                  color: "#8b5cf6",
                  type: "AI",
                };
                const statusPill = getStatusPill(status, isWaiting);
                const Icon = config.icon;

                return (
                  <div
                    key={stepName}
                    className={cn(
                      "relative bg-white rounded-xl shadow-sm border transition-all duration-200",
                      "hover:shadow-md hover:-translate-y-0.5",
                      isCurrent && "ring-2 ring-violet-400 ring-offset-2",
                      isWaiting && "ring-2 ring-amber-400 ring-offset-2",
                    )}
                    style={{ borderLeftWidth: "4px", borderLeftColor: config.color }}
                  >
                    <div className="p-4 min-w-[160px]">
                      {/* Header */}
                      <div className="flex items-center justify-between mb-2">
                        <div
                          className="w-8 h-8 rounded-lg flex items-center justify-center"
                          style={{ backgroundColor: `${config.color}15` }}
                        >
                          <Icon className="w-4 h-4" style={{ color: config.color }} />
                        </div>
                        <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-gray-100 text-gray-500">
                          {config.type}
                        </span>
                      </div>

                      {/* Title */}
                      <h4 className="text-sm font-medium text-gray-900 mb-1">
                        {STEP_LABELS[stepName]}
                      </h4>

                      {/* Status pill */}
                      <div
                        className={cn(
                          "inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium",
                          statusPill.bg,
                          statusPill.text,
                        )}
                      >
                        <span
                          className={cn(
                            "w-1.5 h-1.5 rounded-full",
                            statusPill.dot,
                            status === "running" && "animate-pulse",
                          )}
                        />
                        {statusPill.label}
                      </div>
                    </div>

                    {/* Running animation */}
                    {status === "running" && (
                      <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-gray-100 rounded-b-xl overflow-hidden">
                        <div className="h-full bg-blue-500 animate-progress" />
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ))}
        </div>

        {/* Mini-map */}
        <div className="absolute bottom-4 right-4 w-24 h-16 bg-white/90 backdrop-blur rounded-lg border border-gray-200 shadow-sm p-2">
          <div className="w-full h-full flex flex-col gap-0.5">
            {FLOW_ROWS.map((row, idx) => (
              <div key={idx} className="flex gap-0.5 justify-center flex-1">
                {row.map((stepName) => {
                  const step = stepMap.get(stepName);
                  return (
                    <div
                      key={stepName}
                      className={cn(
                        "flex-1 max-w-[8px] rounded-sm",
                        step?.status === "completed" && "bg-emerald-400",
                        step?.status === "running" && "bg-blue-400",
                        step?.status === "failed" && "bg-red-400",
                        !step?.status && "bg-gray-200",
                      )}
                    />
                  );
                })}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Action Bar (shows when waiting approval) */}
      {waitingApproval && (
        <div className="px-6 py-4 bg-amber-50 border-t border-amber-200">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Pause className="w-5 h-5 text-amber-600" />
              <div>
                <p className="text-sm font-medium text-amber-900">承認が必要です</p>
                <p className="text-xs text-amber-700">
                  レビュー結果を確認して承認または却下してください
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => onReject?.("ユーザーによる却下")}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-red-700 bg-white border border-red-200 rounded-lg hover:bg-red-50 transition-colors"
              >
                <ThumbsDown className="w-4 h-4" />
                却下
              </button>
              <button
                onClick={onApprove}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-emerald-600 rounded-lg hover:bg-emerald-700 transition-colors shadow-sm"
              >
                <ThumbsUp className="w-4 h-4" />
                承認
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Footer */}
      {!waitingApproval && (
        <div className="px-6 py-3 bg-white/50 border-t border-gray-200">
          <div className="flex items-center justify-between text-xs text-gray-500">
            <span>Powered by Dify</span>
            <div className="flex items-center gap-4">
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-emerald-500" /> 完了
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-blue-500" /> 実行中
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-amber-500" /> 承認待ち
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
