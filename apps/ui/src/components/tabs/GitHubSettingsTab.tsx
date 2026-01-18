"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Github,
  Save,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  ExternalLink,
  FolderGit2,
  GitBranch,
  Trash2,
  Search,
  CheckSquare,
  Square,
  Shield,
  GitMerge,
} from "lucide-react";
import api from "@/lib/api";
import type { ApiSettingResponse, ServiceConfig } from "@/lib/types";

interface GitHubConfig {
  default_repo_url: string;
  default_dir_path: string;
}

interface BranchInfo {
  name: string;
  protected: boolean;
  commit_sha: string | null;
  commit_date: string | null;
  commit_message: string | null;
  commit_author: string | null;
  is_default: boolean;
  is_merged: boolean;
}

// Protected branch patterns (must match backend)
const PROTECTED_BRANCH_PATTERNS = ["main", "master", "develop", "release"];

function isProtectedBranch(branchName: string): boolean {
  const nameLower = branchName.toLowerCase();
  return PROTECTED_BRANCH_PATTERNS.some(
    (pattern) => nameLower === pattern || nameLower.startsWith(`${pattern}/`)
  );
}

export function GitHubSettingsTab() {
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isValidating, setIsValidating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [setting, setSetting] = useState<ApiSettingResponse | null>(null);

  // Form state
  const [repoUrl, setRepoUrl] = useState("");
  const [dirPath, setDirPath] = useState("");
  const [hasChanges, setHasChanges] = useState(false);

  // Validation state
  const [repoValid, setRepoValid] = useState<boolean | null>(null);
  const [repoError, setRepoError] = useState<string | null>(null);

  // Branch management state
  const [branchRepoUrl, setBranchRepoUrl] = useState("");
  const [branches, setBranches] = useState<BranchInfo[]>([]);
  const [isLoadingBranches, setIsLoadingBranches] = useState(false);
  const [branchError, setBranchError] = useState<string | null>(null);
  const [selectedBranches, setSelectedBranches] = useState<Set<string>>(new Set());
  const [branchFilter, setBranchFilter] = useState<"all" | "merged" | "unmerged">("all");
  const [branchSearch, setBranchSearch] = useState("");
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteResult, setDeleteResult] = useState<{
    deleted: string[];
    failed: Array<{ name: string; reason: string | null }>;
    skipped: Array<{ name: string; reason: string | null }>;
  } | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  // Load current settings
  const loadSettings = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await api.settings.get("github");
      setSetting(response);

      // Load config values
      const config = response.config as GitHubConfig | null;
      setRepoUrl(config?.default_repo_url || "");
      setDirPath(config?.default_dir_path || "");
      setHasChanges(false);
      // Initialize branch management URL from default repo or latest run
      if (config?.default_repo_url) {
        setBranchRepoUrl(config.default_repo_url);
      } else {
        // Try to get repo URL from latest run
        try {
          const runsResponse = await api.runs.list({ limit: 1 });
          if (runsResponse.items.length > 0) {
            const latestRun = await api.runs.get(runsResponse.items[0].id);
            if (latestRun.github_repo_url) {
              setBranchRepoUrl(latestRun.github_repo_url);
            }
          }
        } catch {
          // Ignore errors when fetching runs
        }
      }
    } catch (err) {
      // 404 is expected if no settings exist yet
      if (err instanceof Error && err.message.includes("404")) {
        setSetting(null);
        setRepoUrl("");
        setDirPath("");
        // Try to get repo URL from latest run even when settings don't exist
        try {
          const runsResponse = await api.runs.list({ limit: 1 });
          if (runsResponse.items.length > 0) {
            const latestRun = await api.runs.get(runsResponse.items[0].id);
            if (latestRun.github_repo_url) {
              setBranchRepoUrl(latestRun.github_repo_url);
            }
          }
        } catch {
          // Ignore errors when fetching runs
        }
      } else {
        setError(err instanceof Error ? err.message : "設定の読み込みに失敗しました");
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSettings();
  }, [loadSettings]);

  // Track changes
  useEffect(() => {
    const config = setting?.config as GitHubConfig | null;
    const originalRepoUrl = config?.default_repo_url || "";
    const originalDirPath = config?.default_dir_path || "";
    setHasChanges(repoUrl !== originalRepoUrl || dirPath !== originalDirPath);
  }, [repoUrl, dirPath, setting]);

  // Validate repository URL format
  const validateRepoUrlFormat = (url: string): boolean => {
    if (!url) return true; // Empty is valid (clears the setting)
    const githubUrlPattern = /^https:\/\/github\.com\/[\w.-]+\/[\w.-]+\/?$/;
    return githubUrlPattern.test(url);
  };

  // Validate repository access
  const handleValidateRepo = async () => {
    if (!repoUrl) {
      setRepoValid(null);
      setRepoError(null);
      return;
    }

    if (!validateRepoUrlFormat(repoUrl)) {
      setRepoValid(false);
      setRepoError("URLの形式が正しくありません。例: https://github.com/owner/repo");
      return;
    }

    setIsValidating(true);
    setRepoError(null);
    try {
      const result = await api.github.checkAccess(repoUrl);
      setRepoValid(result.accessible);
      if (!result.accessible) {
        setRepoError(result.error || "リポジトリにアクセスできません");
      }
    } catch (err) {
      setRepoValid(false);
      setRepoError(err instanceof Error ? err.message : "検証に失敗しました");
    } finally {
      setIsValidating(false);
    }
  };

  // Save settings
  const handleSave = async () => {
    setIsSaving(true);
    setError(null);
    setSuccess(null);

    // Validate format before saving
    if (repoUrl && !validateRepoUrlFormat(repoUrl)) {
      setError("リポジトリURLの形式が正しくありません");
      setIsSaving(false);
      return;
    }

    try {
      const config: ServiceConfig = {
        ...setting?.config,
        default_repo_url: repoUrl || undefined,
        default_dir_path: dirPath || undefined,
      };

      // Remove undefined values
      if (!config.default_repo_url) delete config.default_repo_url;
      if (!config.default_dir_path) delete config.default_dir_path;

      await api.settings.update("github", {
        config: Object.keys(config).length > 0 ? config : undefined,
        is_active: true,
      });

      setSuccess("設定を保存しました");
      setHasChanges(false);
      // Reload to get updated state
      await loadSettings();
    } catch (err) {
      setError(err instanceof Error ? err.message : "保存に失敗しました");
    } finally {
      setIsSaving(false);
    }
  };

  // Load branches from repository
  const loadBranches = async () => {
    if (!branchRepoUrl) {
      setBranchError("リポジトリURLを入力してください");
      return;
    }

    setIsLoadingBranches(true);
    setBranchError(null);
    setDeleteResult(null);
    setBranches([]);
    setSelectedBranches(new Set());

    try {
      const result = await api.github.listBranches(branchRepoUrl);
      setBranches(result.branches);
    } catch (err) {
      setBranchError(err instanceof Error ? err.message : "ブランチの取得に失敗しました");
    } finally {
      setIsLoadingBranches(false);
    }
  };

  // Filter branches based on search and filter
  const filteredBranches = branches.filter((branch) => {
    // Search filter
    if (branchSearch && !branch.name.toLowerCase().includes(branchSearch.toLowerCase())) {
      return false;
    }
    // Merge status filter
    if (branchFilter === "merged" && !branch.is_merged) return false;
    if (branchFilter === "unmerged" && branch.is_merged) return false;
    return true;
  });

  // Get selectable branches (non-protected, non-default)
  const selectableBranches = filteredBranches.filter(
    (b) => !b.is_default && !isProtectedBranch(b.name)
  );

  // Toggle branch selection
  const toggleBranchSelection = (branchName: string) => {
    const branch = branches.find((b) => b.name === branchName);
    if (!branch || branch.is_default || isProtectedBranch(branchName)) return;

    const newSelected = new Set(selectedBranches);
    if (newSelected.has(branchName)) {
      newSelected.delete(branchName);
    } else {
      newSelected.add(branchName);
    }
    setSelectedBranches(newSelected);
  };

  // Select all selectable branches
  const selectAllBranches = () => {
    setSelectedBranches(new Set(selectableBranches.map((b) => b.name)));
  };

  // Clear selection
  const clearSelection = () => {
    setSelectedBranches(new Set());
  };

  // Delete selected branches
  const handleDeleteBranches = async () => {
    if (selectedBranches.size === 0) return;

    setIsDeleting(true);
    setDeleteResult(null);
    setBranchError(null);

    try {
      const result = await api.github.deleteBranches(
        branchRepoUrl,
        Array.from(selectedBranches)
      );
      setDeleteResult(result);
      setSelectedBranches(new Set());
      setShowDeleteConfirm(false);

      // Reload branches to reflect changes
      if (result.deleted.length > 0) {
        await loadBranches();
      }
    } catch (err) {
      setBranchError(err instanceof Error ? err.message : "削除に失敗しました");
    } finally {
      setIsDeleting(false);
    }
  };

  // Format date for display
  const formatDate = (dateString: string | null) => {
    if (!dateString) return "-";
    const date = new Date(dateString);
    return date.toLocaleDateString("ja-JP", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  // Count unmerged selected branches (for warning)
  const unmergedSelectedCount = Array.from(selectedBranches).filter((name) => {
    const branch = branches.find((b) => b.name === name);
    return branch && !branch.is_merged;
  }).length;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <RefreshCw className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    );
  }

  const hasGitHubToken = setting?.api_key_masked && setting.api_key_masked !== "";

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="p-2 bg-gray-100 dark:bg-gray-800 rounded-lg">
          <Github className="h-6 w-6 text-gray-700 dark:text-gray-300" />
        </div>
        <div>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            GitHub設定
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            デフォルトリポジトリを設定して、新規Run作成時に自動入力
          </p>
        </div>
      </div>

      {/* Token status warning */}
      {!hasGitHubToken && (
        <div className="flex items-start gap-3 p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
          <AlertCircle className="h-5 w-5 text-yellow-600 dark:text-yellow-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-yellow-800 dark:text-yellow-200">
              GitHubトークンが設定されていません
            </p>
            <p className="text-sm text-yellow-700 dark:text-yellow-300 mt-1">
              GitHub連携機能を使用するには、APIキータブでGitHubトークンを設定してください。
            </p>
            <a
              href="/settings?tab=apikeys"
              className="inline-flex items-center gap-1 text-sm text-yellow-700 dark:text-yellow-300 hover:underline mt-2"
            >
              APIキー設定へ移動
              <ExternalLink className="h-3 w-3" />
            </a>
          </div>
        </div>
      )}

      {/* Form */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 space-y-6">
        {/* Repository URL */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            デフォルトリポジトリURL
          </label>
          <div className="flex gap-2">
            <div className="flex-1 relative">
              <div className="absolute left-3 top-1/2 -translate-y-1/2">
                <Github className="h-4 w-4 text-gray-400" />
              </div>
              <input
                type="url"
                value={repoUrl}
                onChange={(e) => {
                  setRepoUrl(e.target.value);
                  setRepoValid(null);
                  setRepoError(null);
                }}
                placeholder="https://github.com/owner/repository"
                className="w-full pl-10 pr-10 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
              {repoValid !== null && (
                <div className="absolute right-3 top-1/2 -translate-y-1/2">
                  {repoValid ? (
                    <CheckCircle2 className="h-5 w-5 text-green-500" />
                  ) : (
                    <AlertCircle className="h-5 w-5 text-red-500" />
                  )}
                </div>
              )}
            </div>
            <button
              onClick={handleValidateRepo}
              disabled={isValidating || !repoUrl || !hasGitHubToken}
              className="inline-flex items-center gap-2 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 transition-colors"
            >
              {isValidating ? (
                <RefreshCw className="h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4" />
              )}
              検証
            </button>
          </div>
          {repoError && (
            <p className="mt-2 text-sm text-red-600 dark:text-red-400">{repoError}</p>
          )}
          {repoValid && (
            <p className="mt-2 text-sm text-green-600 dark:text-green-400">
              リポジトリへのアクセスを確認しました
            </p>
          )}
          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
            新規Run作成時に自動で入力されるリポジトリURL
          </p>
        </div>

        {/* Directory path */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            デフォルトディレクトリパス
          </label>
          <div className="relative">
            <div className="absolute left-3 top-1/2 -translate-y-1/2">
              <FolderGit2 className="h-4 w-4 text-gray-400" />
            </div>
            <input
              type="text"
              value={dirPath}
              onChange={(e) => setDirPath(e.target.value)}
              placeholder="articles/seo"
              className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>
          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
            記事ファイルを保存するリポジトリ内のパス（例: articles/seo）
          </p>
        </div>

        {/* Messages */}
        {error && (
          <div className="flex items-center gap-2 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
            <AlertCircle className="h-5 w-5 text-red-600 dark:text-red-400" />
            <span className="text-sm text-red-700 dark:text-red-300">{error}</span>
          </div>
        )}

        {success && (
          <div className="flex items-center gap-2 p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
            <CheckCircle2 className="h-5 w-5 text-green-600 dark:text-green-400" />
            <span className="text-sm text-green-700 dark:text-green-300">{success}</span>
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center justify-between pt-4 border-t border-gray-200 dark:border-gray-700">
          <div className="text-sm text-gray-500 dark:text-gray-400">
            {hasChanges ? (
              <span className="text-yellow-600 dark:text-yellow-400">変更があります</span>
            ) : (
              <span>変更なし</span>
            )}
          </div>
          <button
            onClick={handleSave}
            disabled={isSaving || !hasChanges}
            className="inline-flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 transition-colors"
          >
            {isSaving ? (
              <RefreshCw className="h-4 w-4 animate-spin" />
            ) : (
              <Save className="h-4 w-4" />
            )}
            保存
          </button>
        </div>
      </div>

      {/* Branch Management Section */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 space-y-6">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
            <GitBranch className="h-5 w-5 text-purple-600 dark:text-purple-400" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900 dark:text-gray-100">
              ブランチ管理
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              リポジトリのブランチを一覧表示・一括削除
            </p>
          </div>
        </div>

        {/* Repository URL input for branch management */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            リポジトリURL
          </label>
          <div className="flex gap-2">
            <div className="flex-1 relative">
              <div className="absolute left-3 top-1/2 -translate-y-1/2">
                <Github className="h-4 w-4 text-gray-400" />
              </div>
              <input
                type="url"
                value={branchRepoUrl}
                onChange={(e) => setBranchRepoUrl(e.target.value)}
                placeholder="https://github.com/owner/repository"
                className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>
            <button
              onClick={loadBranches}
              disabled={isLoadingBranches || !branchRepoUrl || !hasGitHubToken}
              className="inline-flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 transition-colors"
            >
              {isLoadingBranches ? (
                <RefreshCw className="h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4" />
              )}
              ブランチ取得
            </button>
          </div>
          {!hasGitHubToken && (
            <p className="mt-1 text-xs text-yellow-600 dark:text-yellow-400">
              GitHubトークンが必要です
            </p>
          )}
        </div>

        {/* Branch error message */}
        {branchError && (
          <div className="flex items-center gap-2 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
            <AlertCircle className="h-5 w-5 text-red-600 dark:text-red-400" />
            <span className="text-sm text-red-700 dark:text-red-300">{branchError}</span>
          </div>
        )}

        {/* Delete result message */}
        {deleteResult && (
          <div className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg space-y-2">
            {deleteResult.deleted.length > 0 && (
              <div className="flex items-center gap-2 text-green-600 dark:text-green-400">
                <CheckCircle2 className="h-4 w-4" />
                <span className="text-sm">
                  {deleteResult.deleted.length}件のブランチを削除しました
                </span>
              </div>
            )}
            {deleteResult.skipped.length > 0 && (
              <div className="flex items-start gap-2 text-yellow-600 dark:text-yellow-400">
                <Shield className="h-4 w-4 mt-0.5" />
                <div className="text-sm">
                  <span>{deleteResult.skipped.length}件スキップ：</span>
                  <ul className="mt-1 space-y-0.5">
                    {deleteResult.skipped.map((s) => (
                      <li key={s.name} className="text-xs">
                        {s.name}: {s.reason}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            )}
            {deleteResult.failed.length > 0 && (
              <div className="flex items-start gap-2 text-red-600 dark:text-red-400">
                <AlertCircle className="h-4 w-4 mt-0.5" />
                <div className="text-sm">
                  <span>{deleteResult.failed.length}件失敗：</span>
                  <ul className="mt-1 space-y-0.5">
                    {deleteResult.failed.map((f) => (
                      <li key={f.name} className="text-xs">
                        {f.name}: {f.reason}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Branch list */}
        {branches.length > 0 && (
          <>
            {/* Filter and search */}
            <div className="flex flex-wrap gap-3 items-center">
              <div className="flex-1 min-w-[200px] relative">
                <div className="absolute left-3 top-1/2 -translate-y-1/2">
                  <Search className="h-4 w-4 text-gray-400" />
                </div>
                <input
                  type="text"
                  value={branchSearch}
                  onChange={(e) => setBranchSearch(e.target.value)}
                  placeholder="ブランチ名で検索..."
                  className="w-full pl-10 pr-4 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
              </div>
              <div className="flex gap-1">
                {(["all", "merged", "unmerged"] as const).map((filter) => (
                  <button
                    key={filter}
                    onClick={() => setBranchFilter(filter)}
                    className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
                      branchFilter === filter
                        ? "bg-purple-600 text-white"
                        : "bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600"
                    }`}
                  >
                    {filter === "all" ? "すべて" : filter === "merged" ? "マージ済" : "未マージ"}
                  </button>
                ))}
              </div>
            </div>

            {/* Selection actions */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <button
                  onClick={selectAllBranches}
                  disabled={selectableBranches.length === 0}
                  className="text-sm text-purple-600 dark:text-purple-400 hover:underline disabled:opacity-50"
                >
                  全選択 ({selectableBranches.length})
                </button>
                <button
                  onClick={clearSelection}
                  disabled={selectedBranches.size === 0}
                  className="text-sm text-gray-600 dark:text-gray-400 hover:underline disabled:opacity-50"
                >
                  選択解除
                </button>
                {selectedBranches.size > 0 && (
                  <span className="text-sm text-gray-600 dark:text-gray-400">
                    {selectedBranches.size}件選択中
                  </span>
                )}
              </div>
              <button
                onClick={() => setShowDeleteConfirm(true)}
                disabled={selectedBranches.size === 0 || isDeleting}
                className="inline-flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 transition-colors"
              >
                <Trash2 className="h-4 w-4" />
                削除 ({selectedBranches.size})
              </button>
            </div>

            {/* Branch table */}
            <div className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 dark:bg-gray-700/50">
                  <tr>
                    <th className="w-10 px-3 py-2"></th>
                    <th className="px-3 py-2 text-left font-medium text-gray-700 dark:text-gray-300">
                      ブランチ名
                    </th>
                    <th className="px-3 py-2 text-left font-medium text-gray-700 dark:text-gray-300">
                      状態
                    </th>
                    <th className="px-3 py-2 text-left font-medium text-gray-700 dark:text-gray-300 hidden sm:table-cell">
                      最終コミット
                    </th>
                    <th className="px-3 py-2 text-left font-medium text-gray-700 dark:text-gray-300 hidden md:table-cell">
                      日時
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                  {filteredBranches.map((branch) => {
                    const isSelectable = !branch.is_default && !isProtectedBranch(branch.name);
                    const isSelected = selectedBranches.has(branch.name);

                    return (
                      <tr
                        key={branch.name}
                        onClick={() => isSelectable && toggleBranchSelection(branch.name)}
                        className={`${
                          isSelectable ? "cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700/50" : ""
                        } ${isSelected ? "bg-purple-50 dark:bg-purple-900/20" : ""}`}
                      >
                        <td className="px-3 py-2">
                          {isSelectable ? (
                            isSelected ? (
                              <CheckSquare className="h-5 w-5 text-purple-600 dark:text-purple-400" />
                            ) : (
                              <Square className="h-5 w-5 text-gray-400" />
                            )
                          ) : (
                            <span title="保護されたブランチ">
                              <Shield className="h-5 w-5 text-gray-300 dark:text-gray-600" />
                            </span>
                          )}
                        </td>
                        <td className="px-3 py-2">
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-gray-900 dark:text-gray-100">
                              {branch.name}
                            </span>
                            {branch.is_default && (
                              <span className="px-1.5 py-0.5 text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded">
                                default
                              </span>
                            )}
                            {branch.protected && (
                              <span className="px-1.5 py-0.5 text-xs bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300 rounded">
                                protected
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="px-3 py-2">
                          {branch.is_merged ? (
                            <span className="inline-flex items-center gap-1 text-green-600 dark:text-green-400">
                              <GitMerge className="h-4 w-4" />
                              マージ済
                            </span>
                          ) : (
                            <span className="text-gray-500 dark:text-gray-400">未マージ</span>
                          )}
                        </td>
                        <td className="px-3 py-2 hidden sm:table-cell">
                          <span className="text-gray-600 dark:text-gray-400 truncate max-w-[200px] block" title={branch.commit_message || ""}>
                            {branch.commit_message?.substring(0, 40) || "-"}
                            {(branch.commit_message?.length || 0) > 40 && "..."}
                          </span>
                        </td>
                        <td className="px-3 py-2 hidden md:table-cell">
                          <span className="text-gray-500 dark:text-gray-400 text-xs">
                            {formatDate(branch.commit_date)}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              {filteredBranches.length === 0 && (
                <div className="p-4 text-center text-gray-500 dark:text-gray-400">
                  条件に一致するブランチがありません
                </div>
              )}
            </div>
          </>
        )}
      </div>

      {/* Delete Confirmation Dialog */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-md w-full mx-4 p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
              ブランチの削除確認
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
              以下の{selectedBranches.size}件のブランチを削除しますか？
              この操作は取り消せません。
            </p>
            {unmergedSelectedCount > 0 && (
              <div className="flex items-start gap-2 p-3 mb-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
                <AlertCircle className="h-5 w-5 text-yellow-600 dark:text-yellow-400 flex-shrink-0" />
                <span className="text-sm text-yellow-700 dark:text-yellow-300">
                  {unmergedSelectedCount}件の未マージブランチが含まれています。
                  削除すると変更内容が失われる可能性があります。
                </span>
              </div>
            )}
            <div className="max-h-40 overflow-y-auto mb-4 p-2 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
              <ul className="text-sm space-y-1">
                {Array.from(selectedBranches).map((name) => {
                  const branch = branches.find((b) => b.name === name);
                  return (
                    <li key={name} className="flex items-center gap-2 text-gray-700 dark:text-gray-300">
                      <GitBranch className="h-3 w-3" />
                      <span className="font-mono">{name}</span>
                      {branch && !branch.is_merged && (
                        <span className="text-xs text-yellow-600 dark:text-yellow-400">(未マージ)</span>
                      )}
                    </li>
                  );
                })}
              </ul>
            </div>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setShowDeleteConfirm(false)}
                disabled={isDeleting}
                className="px-4 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
              >
                キャンセル
              </button>
              <button
                onClick={handleDeleteBranches}
                disabled={isDeleting}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 transition-colors"
              >
                {isDeleting ? (
                  <RefreshCw className="h-4 w-4 animate-spin" />
                ) : (
                  <Trash2 className="h-4 w-4" />
                )}
                削除する
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Help text */}
      <div className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-xl border border-gray-200 dark:border-gray-700">
        <h3 className="font-medium text-gray-900 dark:text-gray-100 mb-2">
          デフォルトリポジトリについて
        </h3>
        <ul className="text-sm text-gray-600 dark:text-gray-400 space-y-1 list-disc list-inside">
          <li>新規Run作成時にリポジトリURLとディレクトリパスが自動入力されます</li>
          <li>Run作成時に個別に変更することも可能です</li>
          <li>GitHubトークンにリポジトリへの書き込み権限が必要です</li>
        </ul>
      </div>

      {/* Branch management help */}
      <div className="p-4 bg-purple-50 dark:bg-purple-900/20 rounded-xl border border-purple-200 dark:border-purple-800">
        <h3 className="font-medium text-gray-900 dark:text-gray-100 mb-2">
          ブランチ管理について
        </h3>
        <ul className="text-sm text-gray-600 dark:text-gray-400 space-y-1 list-disc list-inside">
          <li>保護ブランチ（main, master, develop, release/*）は削除できません</li>
          <li>デフォルトブランチも削除から保護されています</li>
          <li>未マージのブランチを削除すると、変更内容が失われる可能性があります</li>
        </ul>
      </div>
    </div>
  );
}
