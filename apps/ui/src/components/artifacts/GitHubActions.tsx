"use client";

import { useState, useCallback, useEffect, useRef } from "react";
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

interface PullRequestInfo {
  number: number;
  title: string;
  url: string;
  state: string;
  head_branch: string | null;
  base_branch: string | null;
  user: string | null;
  created_at: string | null;
  updated_at: string | null;
  additions: number;
  deletions: number;
  status: string | null;
}

interface BranchInfo {
  name: string;
  url: string;
  compare_url: string;
  last_commit_sha: string | null;
  last_commit_message: string | null;
  last_commit_date: string | null;
  author: string | null;
  additions: number;
  deletions: number;
  status: string | null;
  ahead_by: number;
  behind_by: number;
}

interface DiffResult {
  has_diff: boolean;
  diff: string | null;
  github_sha: string | null;
  minio_digest: string | null;
  open_prs: PullRequestInfo[];
  pending_branches: BranchInfo[];
}

interface IssueStatus {
  issue_number: number;
  issue_url: string;
  status: "open" | "in_progress" | "closed";
  last_comment?: string;
  updated_at?: string;
  pr_url?: string;  // Claude Code が作成した PR の URL
}

/**
 * GitHubActions - GitHub連携アクションボタン群
 *
 * 機能:
 * - 「AI で編集」: GitHub Issue を作成して @codex（デフォルト、コスト効率良）または @claude メンション
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
  const [isCreatingPR, setIsCreatingPR] = useState(false);
  const [isMergingPR, setIsMergingPR] = useState<number | null>(null);
  // Issue tracking state
  const [issueStatus, setIssueStatus] = useState<IssueStatus | null>(null);
  const [showIssueTracker, setShowIssueTracker] = useState(false);

  // Update sync status when initialSyncStatus changes
  useEffect(() => {
    setSyncStatus(initialSyncStatus);
  }, [initialSyncStatus]);

  // Polling interval ref for cleanup
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Track issue number and status separately for stable dependencies
  const issueNumber = issueStatus?.issue_number;
  const issueState = issueStatus?.status;
  const issueUrl = issueStatus?.issue_url;

  // Poll issue status when tracking is active
  useEffect(() => {
    // Only poll if tracker is shown and issue exists and not closed
    if (!showIssueTracker || !issueNumber || issueState === "closed") {
      return;
    }

    // Function to fetch and update issue status
    const pollIssueStatus = async () => {
      try {
        const status = await api.github.getIssueStatus(runId, issueNumber);
        setIssueStatus({
          issue_number: status.issue_number,
          issue_url: status.issue_url || issueUrl || "",
          status: status.status,
          last_comment: status.last_comment || undefined,
          updated_at: status.updated_at || undefined,
          pr_url: status.pr_url || undefined,
        });
      } catch (err) {
        console.error("Failed to poll issue status:", err);
      }
    };

    // Initial poll
    pollIssueStatus();

    // Setup polling interval (every 10 seconds)
    pollIntervalRef.current = setInterval(pollIssueStatus, 10000);

    // Cleanup on unmount or when dependencies change
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    };
  }, [showIssueTracker, issueNumber, issueState, issueUrl, runId]);

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

      // Issue作成後はページ内で状態を表示（URLに飛ばない）
      setIssueStatus({
        issue_number: result.issue_number,
        issue_url: result.issue_url,
        status: "open",
      });
      setShowIssueTracker(true);
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

  // PR を作成
  const handleCreatePR = useCallback(async (branchName: string) => {
    setIsCreatingPR(true);
    setError(null);

    try {
      const result = await api.github.createPR(runId, branchName);
      setSuccessMessage(`PR #${result.number} を作成しました`);
      // 差分を再取得してブランチ情報を更新
      const newDiff = await api.github.getDiff(runId, step);
      setDiffResult(newDiff);
    } catch (err) {
      setError(err instanceof Error ? err.message : "PR の作成に失敗しました");
    } finally {
      setIsCreatingPR(false);
    }
  }, [runId, step]);

  // PR をマージ
  const handleMergePR = useCallback(async (prNumber: number) => {
    if (!confirm("この PR をマージしますか？")) {
      return;
    }

    setIsMergingPR(prNumber);
    setError(null);

    try {
      const result = await api.github.mergePR(runId, prNumber, "squash");
      if (result.merged) {
        setSuccessMessage(`PR #${prNumber} をマージしました`);
        // 差分を再取得してPR情報を更新
        const newDiff = await api.github.getDiff(runId, step);
        setDiffResult(newDiff);
        // 同期ステータスも更新（マージ後は差分がある可能性）
        setSyncStatus("diverged");
        onSyncStatusChange?.(step, "diverged");
      } else {
        setError(result.message || "PR のマージに失敗しました");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "PR のマージに失敗しました");
    } finally {
      setIsMergingPR(null);
    }
  }, [runId, step, onSyncStatusChange]);

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
        {/* AI で編集 */}
        <button
          onClick={() => setShowInstructionModal(true)}
          disabled={disabled || isCreatingIssue}
          className="px-3 py-1.5 text-sm bg-purple-600 text-white rounded hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
          </svg>
          AI で編集
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
            <h3 className="text-lg font-semibold mb-4">AI で編集</h3>
            <p className="text-sm text-gray-600 mb-4">
              GitHub Issue を作成し、AI（@codex または @claude）に編集を依頼します。
              @codex がデフォルト（コスト効率が良い）です。
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
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-6xl mx-4 max-h-[90vh] overflow-hidden flex flex-col">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold">差分確認</h3>
              <button
                onClick={() => setShowDiffModal(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                ✕
              </button>
            </div>

            {/* PR情報セクション */}
            {diffResult.open_prs && diffResult.open_prs.length > 0 && (
              <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <div className="flex items-center gap-2 mb-3">
                  <svg className="w-5 h-5 text-blue-600" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M6 3a3 3 0 00-3 3v12a3 3 0 003 3h12a3 3 0 003-3V6a3 3 0 00-3-3H6zm1 15v-2h2v2H7zm0-4v-2h2v2H7zm0-4V8h2v2H7zm4 8v-2h6v2h-6zm0-4v-2h6v2h-6zm0-4V8h6v2h-6z"/>
                  </svg>
                  <span className="font-medium text-blue-800">
                    このファイルを変更する PR があります ({diffResult.open_prs.length}件)
                  </span>
                </div>
                <div className="space-y-2">
                  {diffResult.open_prs.map((pr) => (
                    <div key={pr.number} className="flex items-center justify-between bg-white p-3 rounded border border-blue-100">
                      <div className="flex-1 min-w-0">
                        <a
                          href={pr.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-sm font-medium text-blue-600 hover:underline truncate block"
                        >
                          #{pr.number} {pr.title}
                        </a>
                        <div className="flex items-center gap-2 mt-1 text-xs text-gray-500">
                          <span className="inline-flex items-center gap-1">
                            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 24 24">
                              <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
                            </svg>
                            {pr.user}
                          </span>
                          <span>{pr.head_branch} → {pr.base_branch}</span>
                          <span className="text-green-600">+{pr.additions}</span>
                          <span className="text-red-600">-{pr.deletions}</span>
                        </div>
                      </div>
                      <button
                        onClick={() => handleMergePR(pr.number)}
                        disabled={isMergingPR === pr.number}
                        className="ml-2 px-3 py-1 text-xs bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {isMergingPR === pr.number ? "マージ中..." : "マージ"}
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* ブランチ情報セクション（PR未作成の変更） */}
            {diffResult.pending_branches && diffResult.pending_branches.length > 0 && (
              <div className="mb-4 p-4 bg-amber-50 border border-amber-200 rounded-lg">
                <div className="flex items-center gap-2 mb-3">
                  <svg className="w-5 h-5 text-amber-600" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>
                  </svg>
                  <span className="font-medium text-amber-800">
                    PR未作成の変更ブランチがあります ({diffResult.pending_branches.length}件)
                  </span>
                </div>
                <div className="space-y-2">
                  {diffResult.pending_branches.map((branch) => (
                    <div key={branch.name} className="flex items-center justify-between bg-white p-3 rounded border border-amber-100">
                      <div className="flex-1 min-w-0">
                        <a
                          href={branch.compare_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-sm font-medium text-amber-700 hover:underline truncate block"
                        >
                          {branch.name}
                        </a>
                        <div className="flex items-center gap-2 mt-1 text-xs text-gray-500">
                          {branch.author && (
                            <span className="inline-flex items-center gap-1">
                              <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 24 24">
                                <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
                              </svg>
                              {branch.author}
                            </span>
                          )}
                          {branch.last_commit_sha && (
                            <span className="font-mono">{branch.last_commit_sha}</span>
                          )}
                          <span className="text-green-600">+{branch.additions}</span>
                          <span className="text-red-600">-{branch.deletions}</span>
                          <span className="text-gray-400">({branch.ahead_by} ahead)</span>
                        </div>
                        {branch.last_commit_message && (
                          <p className="text-xs text-gray-400 mt-1 truncate">
                            {branch.last_commit_message}
                          </p>
                        )}
                      </div>
                      <button
                        onClick={() => handleCreatePR(branch.name)}
                        disabled={isCreatingPR}
                        className="ml-2 px-3 py-1 text-xs bg-amber-600 text-white rounded hover:bg-amber-700 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {isCreatingPR ? "作成中..." : "PR を作成"}
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {diffResult.has_diff ? (
              <>
                <div className="text-sm text-gray-600 mb-4">
                  <p>GitHub (main) と MinIO の間に差分があります。</p>
                  <p className="text-xs text-gray-500 mt-1">
                    GitHub SHA: {diffResult.github_sha?.slice(0, 8) || "N/A"} |
                    MinIO Digest: {diffResult.minio_digest?.slice(0, 8) || "N/A"}
                  </p>
                </div>
                {/* Side-by-side diff view */}
                <div className="flex-1 overflow-auto">
                  <div className="grid grid-cols-2 gap-0 border border-gray-700 rounded overflow-hidden">
                    {/* Header */}
                    <div className="bg-red-900/30 px-3 py-2 border-b border-gray-700 text-red-300 text-xs font-medium">
                      MinIO (ローカル)
                    </div>
                    <div className="bg-green-900/30 px-3 py-2 border-b border-gray-700 text-green-300 text-xs font-medium">
                      GitHub (main)
                    </div>
                    {/* Diff content */}
                    <div className="bg-gray-900 overflow-auto max-h-96">
                      <pre className="text-xs font-mono p-3 whitespace-pre-wrap break-all">
                        {(() => {
                          const lines = (diffResult.diff || "").split("\n");
                          return lines.map((line, i) => {
                            if (line.startsWith("---") || line.startsWith("+++") || line.startsWith("@@")) {
                              return null; // Skip header lines
                            }
                            if (line.startsWith("-")) {
                              return (
                                <div key={i} className="bg-red-900/40 text-red-300 -mx-3 px-3">
                                  {line.slice(1) || " "}
                                </div>
                              );
                            }
                            if (line.startsWith("+")) {
                              return (
                                <div key={i} className="text-gray-500 -mx-3 px-3">
                                  {/* Placeholder for added lines on left side */}
                                </div>
                              );
                            }
                            return (
                              <div key={i} className="text-gray-400 -mx-3 px-3">
                                {line.slice(1) || " "}
                              </div>
                            );
                          });
                        })()}
                      </pre>
                    </div>
                    <div className="bg-gray-900 overflow-auto max-h-96 border-l border-gray-700">
                      <pre className="text-xs font-mono p-3 whitespace-pre-wrap break-all">
                        {(() => {
                          const lines = (diffResult.diff || "").split("\n");
                          return lines.map((line, i) => {
                            if (line.startsWith("---") || line.startsWith("+++") || line.startsWith("@@")) {
                              return null; // Skip header lines
                            }
                            if (line.startsWith("+")) {
                              return (
                                <div key={i} className="bg-green-900/40 text-green-300 -mx-3 px-3">
                                  {line.slice(1) || " "}
                                </div>
                              );
                            }
                            if (line.startsWith("-")) {
                              return (
                                <div key={i} className="text-gray-500 -mx-3 px-3">
                                  {/* Placeholder for removed lines on right side */}
                                </div>
                              );
                            }
                            return (
                              <div key={i} className="text-gray-400 -mx-3 px-3">
                                {line.slice(1) || " "}
                              </div>
                            );
                          });
                        })()}
                      </pre>
                    </div>
                  </div>
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
                  <p className="text-sm text-gray-500 mt-1">GitHub (main) と MinIO は同期しています</p>
                  {diffResult.open_prs && diffResult.open_prs.length > 0 && (
                    <p className="text-sm text-blue-600 mt-2">
                      ただし、上記の PR がマージされると差分が発生します
                    </p>
                  )}
                  {diffResult.pending_branches && diffResult.pending_branches.length > 0 && (
                    <p className="text-sm text-amber-600 mt-2">
                      上記のブランチから PR を作成してマージすると差分が発生します
                    </p>
                  )}
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

      {/* Issue進捗トラッカー（ページ内表示） */}
      {showIssueTracker && issueStatus && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6 w-full max-w-lg mx-4">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                AI 編集状況
              </h3>
              <button
                onClick={() => setShowIssueTracker(false)}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              >
                ✕
              </button>
            </div>

            {/* Issue情報 */}
            <div className="bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-700 rounded-lg p-4 mb-4">
              <div className="flex items-center gap-3 mb-3">
                <div className={`w-3 h-3 rounded-full ${
                  issueStatus.status === "closed" ? "bg-green-500" :
                  issueStatus.status === "in_progress" ? "bg-yellow-500 animate-pulse" :
                  "bg-purple-500"
                }`} />
                <span className="font-medium text-gray-900 dark:text-white">
                  Issue #{issueStatus.issue_number}
                </span>
                <span className={`text-xs px-2 py-0.5 rounded-full ${
                  issueStatus.status === "closed" ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300" :
                  issueStatus.status === "in_progress" ? "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300" :
                  "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300"
                }`}>
                  {issueStatus.status === "closed" ? "完了" :
                   issueStatus.status === "in_progress" ? "編集中" : "待機中"}
                </span>
              </div>

              <p className="text-sm text-gray-600 dark:text-gray-300 mb-3">
                {issueStatus.status === "open" && "AI が Issue を確認するのを待っています..."}
                {issueStatus.status === "in_progress" && "AI が編集を実行中です..."}
                {issueStatus.status === "closed" && (
                  issueStatus.pr_url
                    ? "編集が完了し、PRが作成されました。レビューしてマージしてください。"
                    : "編集が完了しました。差分を確認してください。"
                )}
              </p>

              {issueStatus.last_comment && (
                <div className="bg-white dark:bg-gray-700 rounded p-3 text-sm text-gray-700 dark:text-gray-200 border border-gray-200 dark:border-gray-600">
                  <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">最新コメント:</div>
                  {issueStatus.last_comment}
                </div>
              )}

              {/* PR が作成された場合のマージボタン */}
              {issueStatus.pr_url && (() => {
                // Extract PR number from URL (e.g., https://github.com/owner/repo/pull/123)
                const prMatch = issueStatus.pr_url.match(/\/pull\/(\d+)/);
                const prNumber = prMatch ? parseInt(prMatch[1], 10) : null;
                return (
                  <div className="mt-3 p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-700 rounded-lg">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 text-green-700 dark:text-green-300">
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <span className="font-medium">PR #{prNumber} が作成されました</span>
                      </div>
                      {prNumber && (
                        <button
                          onClick={() => handleMergePR(prNumber)}
                          disabled={isMergingPR === prNumber}
                          className="px-3 py-1.5 text-sm bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          {isMergingPR === prNumber ? "マージ中..." : "マージ"}
                        </button>
                      )}
                    </div>
                  </div>
                );
              })()}
            </div>

            {/* アクションボタン */}
            <div className="flex justify-between items-center">
              <div className="flex items-center gap-3">
                <a
                  href={issueStatus.issue_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-purple-600 dark:text-purple-400 hover:underline flex items-center gap-1"
                >
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
                  </svg>
                  Issue を開く
                </a>
                {issueStatus.status !== "closed" && (
                  <span className="text-xs text-gray-500 dark:text-gray-400">
                    (10秒ごとに自動更新)
                  </span>
                )}
              </div>

              <div className="flex gap-2">
                {issueStatus.status === "closed" && !issueStatus.pr_url && (
                  <button
                    onClick={() => {
                      setShowIssueTracker(false);
                      handleCheckDiff();
                    }}
                    className="px-4 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
                  >
                    差分を確認
                  </button>
                )}
                {issueStatus.status === "closed" && issueStatus.pr_url && (
                  <button
                    onClick={() => {
                      setShowIssueTracker(false);
                      handleCheckDiff();
                    }}
                    className="px-4 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
                  >
                    差分を確認
                  </button>
                )}
                <button
                  onClick={() => setShowIssueTracker(false)}
                  className="px-4 py-2 bg-gray-600 text-white text-sm rounded hover:bg-gray-700"
                >
                  閉じる
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
