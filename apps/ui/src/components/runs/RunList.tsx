"use client";

import { useState, useEffect } from "react";
import { RefreshCw, Filter, Search, Inbox, Plus, Trash2, CheckSquare, Square, X } from "lucide-react";
import Link from "next/link";
import type { RunSummary, RunStatus } from "@/lib/types";
import { api } from "@/lib/api";
import { RunCard } from "./RunCard";
import { LoadingPage, ListSkeleton } from "@/components/common/Loading";
import { ErrorMessage } from "@/components/common/ErrorBoundary";
import { cn } from "@/lib/utils";

const STATUS_FILTERS: Array<{ value: RunStatus | "all"; label: string; color: string }> = [
  { value: "all", label: "すべて", color: "bg-gray-500" },
  { value: "running", label: "実行中", color: "bg-accent-500" },
  { value: "waiting_approval", label: "承認待ち", color: "bg-warning-500" },
  { value: "completed", label: "完了", color: "bg-success-500" },
  { value: "failed", label: "失敗", color: "bg-error-500" },
];

// Statuses that can be deleted (all statuses are deletable)
const DELETABLE_STATUSES: RunStatus[] = ["pending", "running", "waiting_approval", "waiting_image_input", "completed", "failed", "cancelled"];

export function RunList() {
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<RunStatus | "all">("all");
  const [selectMode, setSelectMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [bulkDeleting, setBulkDeleting] = useState(false);

  const fetchRuns = async (isRefresh = false) => {
    if (isRefresh) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }
    setError(null);

    try {
      const params = statusFilter !== "all" ? { status: statusFilter } : {};
      const response = await api.runs.list(params);
      setRuns(response?.items ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch runs");
      setRuns([]);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchRuns();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter]);

  if (loading) {
    return (
      <div className="animate-fade-in">
        <div className="flex items-center justify-between mb-6">
          <div className="shimmer h-10 w-80 rounded-lg" />
          <div className="shimmer h-10 w-20 rounded-lg" />
        </div>
        <ListSkeleton count={6} />
      </div>
    );
  }

  const handleDeleteRun = (runId: string) => {
    setRuns((prevRuns) => prevRuns.filter((run) => run.id !== runId));
  };

  // Get deletable runs (completed, failed, cancelled)
  const deletableRuns = runs.filter((run) => DELETABLE_STATUSES.includes(run.status));

  const toggleSelectMode = () => {
    setSelectMode(!selectMode);
    setSelectedIds(new Set());
  };

  const toggleSelection = (runId: string) => {
    const newSelected = new Set(selectedIds);
    if (newSelected.has(runId)) {
      newSelected.delete(runId);
    } else {
      newSelected.add(runId);
    }
    setSelectedIds(newSelected);
  };

  const selectAllDeletable = () => {
    setSelectedIds(new Set(deletableRuns.map((run) => run.id)));
  };

  const deselectAll = () => {
    setSelectedIds(new Set());
  };

  const handleBulkDelete = async () => {
    if (selectedIds.size === 0) return;

    const confirmed = window.confirm(`${selectedIds.size}件のRunを削除しますか？\nこの操作は取り消せません。`);
    if (!confirmed) return;

    setBulkDeleting(true);
    try {
      const result = await api.runs.bulkDelete(Array.from(selectedIds));

      // Remove deleted runs from state
      if (result.deleted.length > 0) {
        setRuns((prevRuns) => prevRuns.filter((run) => !result.deleted.includes(run.id)));
        setSelectedIds(new Set());
      }

      // Show errors if any
      if (result.failed.length > 0) {
        const errorMessages = result.failed.map((f) => `${f.id.slice(0, 8)}: ${f.error}`).join("\n");
        alert(`一部の削除に失敗しました:\n${errorMessages}`);
      }

      // Exit select mode if all selected were deleted
      if (result.deleted.length === selectedIds.size) {
        setSelectMode(false);
      }
    } catch (err) {
      console.error("Failed to bulk delete runs:", err);
      alert(err instanceof Error ? err.message : "一括削除に失敗しました");
    } finally {
      setBulkDeleting(false);
    }
  };

  if (error) {
    return <ErrorMessage message={error} onRetry={() => fetchRuns()} />;
  }

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
        {/* Filter tabs */}
        <div className="flex items-center gap-2 p-1 bg-gray-100 dark:bg-gray-800 rounded-xl">
          {STATUS_FILTERS.map((filter) => (
            <button
              key={filter.value}
              onClick={() => setStatusFilter(filter.value)}
              className={cn(
                "flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg transition-all duration-200",
                statusFilter === filter.value
                  ? "bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm"
                  : "text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700",
              )}
            >
              <span
                className={cn(
                  "w-2 h-2 rounded-full transition-all",
                  statusFilter === filter.value ? filter.color : "bg-gray-400",
                )}
              />
              {filter.label}
            </button>
          ))}
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-2">
          {/* Bulk delete toggle */}
          <button
            onClick={toggleSelectMode}
            disabled={deletableRuns.length === 0 && !selectMode}
            className={cn(
              "btn btn-ghost",
              selectMode && "bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400",
              deletableRuns.length === 0 && !selectMode && "opacity-50 cursor-not-allowed",
            )}
          >
            {selectMode ? (
              <>
                <X className="h-4 w-4" />
                キャンセル
              </>
            ) : (
              <>
                <Trash2 className="h-4 w-4" />
                一括削除
              </>
            )}
          </button>

          {/* Refresh button */}
          <button onClick={() => fetchRuns(true)} disabled={refreshing} className="btn btn-ghost">
            <RefreshCw className={cn("h-4 w-4", refreshing && "animate-spin")} />
            更新
          </button>
        </div>
      </div>

      {/* Bulk delete controls */}
      {selectMode && (
        <div className="flex flex-wrap items-center gap-3 mb-4 p-3 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
          <span className="text-sm text-red-700 dark:text-red-300">
            {selectedIds.size}件選択中
          </span>
          <div className="flex gap-2">
            <button
              onClick={selectAllDeletable}
              className="text-xs px-2 py-1 text-red-600 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-900/40 rounded transition-colors"
            >
              <CheckSquare className="h-3 w-3 inline mr-1" />
              すべて選択 ({deletableRuns.length})
            </button>
            <button
              onClick={deselectAll}
              className="text-xs px-2 py-1 text-red-600 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-900/40 rounded transition-colors"
            >
              <Square className="h-3 w-3 inline mr-1" />
              選択解除
            </button>
          </div>
          <button
            onClick={handleBulkDelete}
            disabled={selectedIds.size === 0 || bulkDeleting}
            className="ml-auto px-4 py-1.5 text-sm font-medium text-white bg-red-600 hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg transition-colors"
          >
            {bulkDeleting ? "削除中..." : `${selectedIds.size}件を削除`}
          </button>
        </div>
      )}

      {/* Results */}
      {runs.length === 0 ? (
        <EmptyState statusFilter={statusFilter} />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 stagger-children">
          {runs.map((run) => {
            const isDeletable = DELETABLE_STATUSES.includes(run.status);
            const isSelected = selectedIds.has(run.id);

            return (
              <RunCard
                key={run.id}
                run={run}
                onDelete={handleDeleteRun}
                selectMode={selectMode}
                isSelected={isSelected}
                isDeletable={isDeletable}
                onToggleSelect={toggleSelection}
              />
            );
          })}
        </div>
      )}

      {/* Count indicator */}
      {runs.length > 0 && (
        <div className="mt-6 text-center">
          <p className="text-sm text-gray-500">{runs.length}件のRunを表示中</p>
        </div>
      )}
    </div>
  );
}

function EmptyState({ statusFilter }: { statusFilter: RunStatus | "all" }) {
  const isFiltered = statusFilter !== "all";

  return (
    <div className="card p-12 text-center animate-fade-in">
      <div className="flex justify-center mb-4">
        <div className="p-4 bg-gray-100 rounded-2xl">
          <Inbox className="h-8 w-8 text-gray-400" />
        </div>
      </div>
      <h3 className="text-lg font-semibold text-gray-900 mb-2">
        {isFiltered ? "Runが見つかりません" : "まだRunがありません"}
      </h3>
      <p className="text-gray-500 mb-6 max-w-sm mx-auto">
        {isFiltered
          ? "フィルター条件を変更するか、新しいRunを作成してください。"
          : "最初のSEO記事を自動生成してみましょう。"}
      </p>
      <Link href="/settings/runs/new" className="btn btn-primary">
        <Plus className="h-4 w-4" />
        新規Run作成
      </Link>
    </div>
  );
}
