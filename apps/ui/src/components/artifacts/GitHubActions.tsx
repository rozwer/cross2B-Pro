"use client";

import { useState, useCallback, useEffect } from "react";
import { api } from "@/lib/api";
import type { GitHubSyncStatus } from "@/lib/types";

interface GitHubActionsProps {
  runId: string;
  step: string;
  githubRepoUrl?: string;
  githubDirPath?: string;
  disabled?: boolean;
  /** Initial sync status (from parent) to avoid redundant API calls */
  initialSyncStatus?: GitHubSyncStatus;
  /** Callback when sync status changes */
  onSyncStatusChange?: (step: string, status: GitHubSyncStatus) => void;
}

interface DiffResult {
  has_diff: boolean;
  diff: string | null;
  github_sha: string | null;
  minio_digest: string | null;
}

/**
 * GitHubActions - GitHub連携アクションボタン群
 *
 * 機能:
 * - 「Claude Code で編集」: GitHub Issue を作成して @claude メンション
 * - 「GitHub で開く」: 該当ファイルを GitHub で直接表示
 * - 「差分を確認」: GitHub と MinIO の差分を表示
 * - 「同期」: GitHub の変更を MinIO に反映
 */
export function GitHubActions({
  runId,
  step,
  githubRepoUrl,
  githubDirPath,
  disabled = false,
  initialSyncStatus,
  onSyncStatusChange,
}: GitHubActionsProps) {
  // State - All hooks must be called before any conditional returns
  const [isCreatingIssue, setIsCreatingIssue] = useState(false);
  const [isCheckingDiff, setIsCheckingDiff] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [showInstructionModal, setShowInstructionModal] = useState(false);
  const [instruction, setInstruction] = useState("");
  const [diffResult, setDiffResult] = useState<DiffResult | null>(null);
  const [showDiffModal, setShowDiffModal] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [syncStatus, setSyncStatus] = useState<GitHubSyncStatus | undefined>(initialSyncStatus);

  // Update sync status when initialSyncStatus changes
  useEffect(() => {
    setSyncStatus(initialSyncStatus);
  }, [initialSyncStatus]);

  // Claude Code で編集（Issue 作成）
  const handleCreateIssue = useCallback(async () => {
    if (!githubRepoUrl || !githubDirPath) return;
    if (!instruction.trim()) {
      setError("編集指示を入力してください");
      return;
    }

    setIsCreatingIssue(true);
    setError(null);

    try {
      const result = await api.github.createIssue(runId, step, instruction);
      setSuccessMessage(`Issue #${result.issue_number} を作成しました`);
      setShowInstructionModal(false);
      setInstruction("");

      // 新しいタブで Issue を開く
      window.open(result.issue_url, "_blank");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Issue の作成に失敗しました");
    } finally {
      setIsCreatingIssue(false);
    }
  }, [runId, step, instruction, githubRepoUrl, githubDirPath]);

  // 差分を確認
  const handleCheckDiff = useCallback(async () => {
    if (!githubRepoUrl || !githubDirPath) return;
    setIsCheckingDiff(true);
    setError(null);

    try {
      const result = await api.github.getDiff(runId, step);
      setDiffResult(result);
      setShowDiffModal(true);
      // Update sync status based on diff result
      const newStatus: GitHubSyncStatus = result.has_diff ? "diverged" : "synced";
      setSyncStatus(newStatus);
      onSyncStatusChange?.(step, newStatus);
    } catch (err) {
      setError(err instanceof Error ? err.message : "差分の取得に失敗しました");
    } finally {
      setIsCheckingDiff(false);
    }
  }, [runId, step, onSyncStatusChange, githubRepoUrl, githubDirPath]);

  // 同期（GitHub → MinIO）
  const handleSync = useCallback(async () => {
    if (!githubRepoUrl || !githubDirPath) return;
    if (!confirm("GitHub の内容で MinIO を上書きします。よろしいですか？")) {
      return;
    }

    setIsSyncing(true);
    setError(null);

    try {
      const result = await api.github.sync(runId, step);
      if (result.synced) {
        setSuccessMessage("同期が完了しました");
        setDiffResult(null);
        // Update sync status to synced
        setSyncStatus("synced");
        onSyncStatusChange?.(step, "synced");
      } else {
        setSuccessMessage(result.message);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "同期に失敗しました");
    } finally {
      setIsSyncing(false);
    }
  }, [runId, step, onSyncStatusChange, githubRepoUrl, githubDirPath]);

  // GitHub が設定されていない場合は表示しない
  // Note: This must be AFTER all hooks are called
  if (!githubRepoUrl || !githubDirPath) {
    return null;
  }

  // GitHub ファイルの URL を構築
  const githubFileUrl = `${githubRepoUrl}/blob/main/${githubDirPath}/${step}/output.json`;

  return (
    <div className="flex flex-col gap-2">
      {/* エラー表示 */}
      {error && (
        <div className="p-2 bg-red-50 border border-red-200 rounded text-sm text-red-600">
          {error}
          <button
            className="ml-2 text-red-400 hover:text-red-600"
            onClick={() => setError(null)}
          >
            ✕
          </button>
        </div>
      )}

      {/* 成功メッセージ */}
      {successMessage && (
        <div className="p-2 bg-green-50 border border-green-200 rounded text-sm text-green-600">
          {successMessage}
          <button
            className="ml-2 text-green-400 hover:text-green-600"
            onClick={() => setSuccessMessage(null)}
          >
            ✕
          </button>
        </div>
      )}

      {/* 同期状態バッジ (Phase 5) */}
      {syncStatus && syncStatus !== "unknown" && (
        <div className={`inline-flex items-center gap-1.5 px-2 py-1 rounded text-xs font-medium ${
          syncStatus === "synced"
            ? "bg-green-50 text-green-700 border border-green-200"
            : syncStatus === "diverged"
            ? "bg-orange-50 text-orange-700 border border-orange-200"
            : "bg-gray-50 text-gray-700 border border-gray-200"
        }`}>
          {syncStatus === "synced" && (
            <>
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              同期済み
            </>
          )}
          {syncStatus === "diverged" && (
            <>
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              差分あり
            </>
          )}
          {(syncStatus === "github_only" || syncStatus === "minio_only") && (
            <>
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              {syncStatus === "github_only" ? "GitHub のみ" : "MinIO のみ"}
            </>
          )}
        </div>
      )}

      {/* アクションボタン */}
      <div className="flex flex-wrap gap-2">
        {/* Claude Code で編集 */}
        <button
          onClick={() => setShowInstructionModal(true)}
          disabled={disabled || isCreatingIssue}
          className="px-3 py-1.5 text-sm bg-purple-600 text-white rounded hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
          </svg>
          Claude Code で編集
        </button>

        {/* GitHub で開く */}
        <a
          href={githubFileUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="px-3 py-1.5 text-sm bg-gray-800 text-white rounded hover:bg-gray-900 flex items-center gap-1"
        >
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
          </svg>
          GitHub で開く
        </a>

        {/* 差分を確認 */}
        <button
          onClick={handleCheckDiff}
          disabled={disabled || isCheckingDiff}
          className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
        >
          {isCheckingDiff ? (
            <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
          ) : (
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
            </svg>
          )}
          差分を確認
        </button>

        {/* 同期ボタン（差分がある場合またはsyncStatusがdivergedの場合に表示） */}
        {(diffResult?.has_diff || syncStatus === "diverged") && (
          <button
            onClick={handleSync}
            disabled={disabled || isSyncing}
            className="px-3 py-1.5 text-sm bg-orange-600 text-white rounded hover:bg-orange-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
          >
            {isSyncing ? (
              <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            ) : (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            )}
            GitHub から同期
          </button>
        )}
      </div>

      {/* 編集指示入力モーダル */}
      {showInstructionModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-lg mx-4">
            <h3 className="text-lg font-semibold mb-4">Claude Code で編集</h3>
            <p className="text-sm text-gray-600 mb-4">
              GitHub Issue を作成し、Claude Code (@claude) に編集を依頼します。
            </p>
            <textarea
              value={instruction}
              onChange={(e) => setInstruction(e.target.value)}
              placeholder="編集指示を入力してください..."
              className="w-full h-32 p-3 border border-gray-300 rounded-lg resize-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            />
            <div className="flex justify-end gap-2 mt-4">
              <button
                onClick={() => {
                  setShowInstructionModal(false);
                  setInstruction("");
                }}
                className="px-4 py-2 text-gray-600 hover:text-gray-800"
              >
                キャンセル
              </button>
              <button
                onClick={handleCreateIssue}
                disabled={isCreatingIssue || !instruction.trim()}
                className="px-4 py-2 bg-purple-600 text-white rounded hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isCreatingIssue ? "作成中..." : "Issue を作成"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 差分表示モーダル */}
      {showDiffModal && diffResult && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-4xl mx-4 max-h-[80vh] overflow-hidden flex flex-col">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold">差分確認</h3>
              <button
                onClick={() => setShowDiffModal(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                ✕
              </button>
            </div>

            {diffResult.has_diff ? (
              <>
                <div className="text-sm text-gray-600 mb-4">
                  <p>GitHub と MinIO の間に差分があります。</p>
                  <p className="text-xs text-gray-500 mt-1">
                    GitHub SHA: {diffResult.github_sha?.slice(0, 8) || "N/A"} |
                    MinIO Digest: {diffResult.minio_digest?.slice(0, 8) || "N/A"}
                  </p>
                </div>
                <div className="flex-1 overflow-auto bg-gray-900 rounded p-4">
                  <pre className="text-sm text-green-400 font-mono whitespace-pre-wrap">
                    {diffResult.diff || "差分データがありません"}
                  </pre>
                </div>
                <div className="mt-4 flex justify-end gap-2">
                  <button
                    onClick={() => setShowDiffModal(false)}
                    className="px-4 py-2 text-gray-600 hover:text-gray-800"
                  >
                    閉じる
                  </button>
                  <button
                    onClick={() => {
                      setShowDiffModal(false);
                      handleSync();
                    }}
                    className="px-4 py-2 bg-orange-600 text-white rounded hover:bg-orange-700"
                  >
                    GitHub から同期
                  </button>
                </div>
              </>
            ) : (
              <>
                <div className="text-center py-8">
                  <svg className="w-16 h-16 mx-auto text-green-500 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <p className="text-lg text-gray-700">差分はありません</p>
                  <p className="text-sm text-gray-500 mt-1">GitHub と MinIO は同期しています</p>
                </div>
                <div className="mt-4 flex justify-end">
                  <button
                    onClick={() => setShowDiffModal(false)}
                    className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
                  >
                    閉じる
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
