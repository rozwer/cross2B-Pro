"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Clock, Zap, ArrowRight, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { RunSummary } from "@/lib/types";
import { RunStatusBadge } from "./RunStatusBadge";
import { formatRelativeTime, truncate } from "@/lib/utils";
import { STEP_LABELS } from "@/lib/types";
import { api } from "@/lib/api";

interface RunCardProps {
  run: RunSummary;
  onDelete?: (runId: string) => void;
  selectMode?: boolean;
  isSelected?: boolean;
  isDeletable?: boolean;
  onToggleSelect?: (runId: string) => void;
}

export function RunCard({ run, onDelete, selectMode, isSelected, isDeletable, onToggleSelect }: RunCardProps) {
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const handleDelete = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setShowDeleteConfirm(true);
  };

  const confirmDelete = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDeleting(true);
    try {
      // For running/pending runs, cancel first then delete
      const isRunning = run.status === "running" || run.status === "pending" || run.status === "waiting_approval" || run.status === "waiting_image_input";
      if (isRunning) {
        await api.runs.cancel(run.id);
      }
      // Always delete after cancel (or directly if already stopped)
      await api.runs.delete(run.id);
      onDelete?.(run.id);
    } catch (err) {
      console.error("Failed to delete run:", err);
      alert(err instanceof Error ? err.message : "削除に失敗しました");
    } finally {
      setDeleting(false);
      setShowDeleteConfirm(false);
    }
  };

  const cancelDelete = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setShowDeleteConfirm(false);
  };
  const stepLabel = run.current_step ? STEP_LABELS[run.current_step] || run.current_step : "待機中";
  const isActive = run.status === "running" || run.status === "waiting_approval" || run.status === "waiting_image_input";

  // Handle card click in select mode
  const handleCardClick = (e: React.MouseEvent) => {
    if (selectMode && isDeletable && onToggleSelect) {
      e.preventDefault();
      e.stopPropagation();
      onToggleSelect(run.id);
    }
  };

  const cardContent = (
    <div
      className={cn(
        "group card card-hover p-5 cursor-pointer relative overflow-hidden",
        selectMode && isDeletable && isSelected && "ring-2 ring-red-500 bg-red-50/50 dark:bg-red-900/20",
        selectMode && !isDeletable && "opacity-50 cursor-not-allowed"
      )}
      onClick={selectMode ? handleCardClick : undefined}
    >
      {/* Active indicator */}
      {isActive && (
        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-primary-400 via-primary-500 to-primary-400 animate-shimmer" />
      )}

      {/* Delete confirmation overlay */}
      {showDeleteConfirm && (
        <div className="absolute inset-0 bg-white/95 dark:bg-gray-800/95 backdrop-blur-sm z-10 flex flex-col items-center justify-center p-4 animate-fade-in">
          <p className="text-sm text-gray-700 dark:text-gray-300 mb-4 text-center">
            このRunを削除しますか？
          </p>
          <div className="flex gap-2">
            <button
              onClick={cancelDelete}
              className="px-3 py-1.5 text-sm text-gray-600 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
            >
              キャンセル
            </button>
            <button
              onClick={confirmDelete}
              disabled={deleting}
              className="px-3 py-1.5 text-sm text-white bg-red-500 rounded-lg hover:bg-red-600 disabled:opacity-50 transition-colors"
            >
              {deleting ? "削除中..." : "削除"}
            </button>
          </div>
        </div>
      )}

      {/* Selection checkbox in select mode (replaces delete button position) */}
      {selectMode && isDeletable ? (
        <div
          className={cn(
            "absolute top-3 right-3 z-20 w-6 h-6 rounded border-2 flex items-center justify-center transition-all",
            isSelected
              ? "bg-red-600 border-red-600 text-white"
              : "bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600"
          )}
        >
          {isSelected && (
            <svg className="w-4 h-4" viewBox="0 0 12 12" fill="none">
              <path
                d="M2 6L5 9L10 3"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          )}
        </div>
      ) : !selectMode && (
        /* Delete button - only show when not in select mode */
        <button
          onClick={handleDelete}
          className="absolute top-3 right-3 p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/30 rounded-lg opacity-0 group-hover:opacity-100 transition-all z-5"
          title="削除"
        >
          <Trash2 className="h-4 w-4" />
        </button>
      )}

        {/* Header */}
        <div className="flex items-start justify-between gap-3 mb-4">
          <div className="flex-1 min-w-0">
            <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100 group-hover:text-primary-700 dark:group-hover:text-primary-400 transition-colors line-clamp-1">
              {truncate(run.keyword, 50)}
            </h3>
            <p className="text-xs text-gray-400 dark:text-gray-500 mt-1 font-mono">
              {run.id.slice(0, 8)}
            </p>
          </div>
          <RunStatusBadge status={run.status} className="mr-8" />
        </div>

        {/* Info rows */}
        <div className="space-y-2.5">
          <div className="flex items-center gap-2.5 text-sm">
            <div className="flex items-center justify-center w-7 h-7 rounded-lg bg-primary-50 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400">
              <Zap className="h-3.5 w-3.5" />
            </div>
            <span className="text-gray-600 dark:text-gray-400">{stepLabel}</span>
          </div>

          <div className="flex items-center gap-2.5 text-sm">
            <div className="flex items-center justify-center w-7 h-7 rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400">
              <Clock className="h-3.5 w-3.5" />
            </div>
            <span className="text-gray-500 dark:text-gray-400">
              {formatRelativeTime(run.updated_at)}
            </span>
          </div>
        </div>

        {/* Grounding status */}
        <div className="mt-4 pt-4 border-t border-gray-100 dark:border-gray-700">
          {run.model_config.options?.grounding ? (
            <span className="badge badge-primary">
              Grounding有効
            </span>
          ) : (
            <span className="badge badge-secondary">
              Grounding無効
            </span>
          )}
        </div>

        {/* Hover action hint - only show when not in select mode */}
        {!selectMode && (
          <div className="absolute bottom-5 right-5 opacity-0 group-hover:opacity-100 transition-all transform group-hover:translate-x-0 translate-x-2">
            <div className="flex items-center gap-1 text-xs text-primary-600 dark:text-primary-400 font-medium">
              詳細を見る
              <ArrowRight className="h-3.5 w-3.5" />
            </div>
          </div>
        )}
    </div>
  );

  // In select mode, don't wrap with Link to prevent navigation
  if (selectMode) {
    return cardContent;
  }

  return (
    <Link href={`/runs/${run.id}`}>
      {cardContent}
    </Link>
  );
}
