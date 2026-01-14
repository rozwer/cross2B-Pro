"use client";

import { useState, useCallback } from "react";
import { api } from "@/lib/api";

type RepoMode = "existing" | "new";

interface RepoSelectorProps {
  value: string;
  onChange: (repoUrl: string) => void;
  defaultRepoUrl?: string;
  disabled?: boolean;
}

interface ValidationState {
  status: "idle" | "checking" | "success" | "error";
  message?: string;
  permissions?: string[];
}

export function RepoSelector({
  value,
  onChange,
  defaultRepoUrl,
  disabled = false,
}: RepoSelectorProps) {
  const [mode, setMode] = useState<RepoMode>(defaultRepoUrl ? "existing" : "existing");
  const [repoUrl, setRepoUrl] = useState(value || defaultRepoUrl || "");
  const [newRepoName, setNewRepoName] = useState("");
  const [newRepoDescription, setNewRepoDescription] = useState("");
  const [isPrivate, setIsPrivate] = useState(true);
  const [validation, setValidation] = useState<ValidationState>({ status: "idle" });
  const [isCreating, setIsCreating] = useState(false);

  const handleCheckAccess = useCallback(async () => {
    if (!repoUrl.trim()) {
      setValidation({ status: "error", message: "URLを入力してください" });
      return;
    }

    setValidation({ status: "checking" });

    try {
      const result = await api.github.checkAccess(repoUrl);

      if (result.accessible) {
        setValidation({
          status: "success",
          message: "アクセス確認OK",
          permissions: result.permissions,
        });
        onChange(repoUrl);
      } else {
        setValidation({
          status: "error",
          message: result.error || "アクセスできません",
        });
      }
    } catch (error) {
      setValidation({
        status: "error",
        message: error instanceof Error ? error.message : "確認に失敗しました",
      });
    }
  }, [repoUrl, onChange]);

  const handleCreateRepo = useCallback(async () => {
    if (!newRepoName.trim()) {
      setValidation({ status: "error", message: "リポジトリ名を入力してください" });
      return;
    }

    setIsCreating(true);
    setValidation({ status: "checking" });

    try {
      const result = await api.github.createRepo(
        newRepoName,
        newRepoDescription,
        isPrivate
      );

      setRepoUrl(result.repo_url);
      setValidation({
        status: "success",
        message: "リポジトリを作成しました",
        permissions: ["read", "write", "admin"],
      });
      onChange(result.repo_url);
      setMode("existing");
    } catch (error) {
      setValidation({
        status: "error",
        message: error instanceof Error ? error.message : "作成に失敗しました",
      });
    } finally {
      setIsCreating(false);
    }
  }, [newRepoName, newRepoDescription, isPrivate, onChange]);

  const handleUrlChange = (url: string) => {
    setRepoUrl(url);
    setValidation({ status: "idle" });
  };

  const handleSkip = () => {
    onChange("");
    setValidation({ status: "idle" });
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          GitHub リポジトリ設定
        </h3>
        <span className="text-sm text-gray-500">(オプション)</span>
      </div>

      <p className="text-sm text-gray-600 dark:text-gray-400">
        成果物を GitHub で管理すると、Claude Code による編集が可能になります。
      </p>

      {/* Mode Selection */}
      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => setMode("existing")}
          disabled={disabled}
          className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
            mode === "existing"
              ? "bg-blue-600 text-white"
              : "bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300"
          }`}
        >
          既存のリポジトリを使用
        </button>
        <button
          type="button"
          onClick={() => setMode("new")}
          disabled={disabled}
          className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
            mode === "new"
              ? "bg-blue-600 text-white"
              : "bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300"
          }`}
        >
          新しいリポジトリを作成
        </button>
      </div>

      {/* Existing Repo Mode */}
      {mode === "existing" && (
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              リポジトリ URL
            </label>
            <div className="flex gap-2">
              <input
                type="url"
                value={repoUrl}
                onChange={(e) => handleUrlChange(e.target.value)}
                placeholder="https://github.com/owner/repo"
                disabled={disabled}
                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:border-gray-600 dark:text-white"
              />
              <button
                type="button"
                onClick={handleCheckAccess}
                disabled={disabled || validation.status === "checking"}
                className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {validation.status === "checking" ? "確認中..." : "確認"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* New Repo Mode */}
      {mode === "new" && (
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              リポジトリ名 *
            </label>
            <input
              type="text"
              value={newRepoName}
              onChange={(e) => setNewRepoName(e.target.value)}
              placeholder="my-seo-articles"
              disabled={disabled || isCreating}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:border-gray-600 dark:text-white"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              説明
            </label>
            <input
              type="text"
              value={newRepoDescription}
              onChange={(e) => setNewRepoDescription(e.target.value)}
              placeholder="SEO記事生成の成果物"
              disabled={disabled || isCreating}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:border-gray-600 dark:text-white"
            />
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="private-repo"
              checked={isPrivate}
              onChange={(e) => setIsPrivate(e.target.checked)}
              disabled={disabled || isCreating}
              className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
            />
            <label htmlFor="private-repo" className="text-sm text-gray-700 dark:text-gray-300">
              プライベートリポジトリにする
            </label>
          </div>

          <button
            type="button"
            onClick={handleCreateRepo}
            disabled={disabled || isCreating || !newRepoName.trim()}
            className="w-full px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isCreating ? "作成中..." : "リポジトリを作成"}
          </button>
        </div>
      )}

      {/* Validation Status */}
      {validation.status !== "idle" && (
        <div
          className={`p-3 rounded-lg ${
            validation.status === "checking"
              ? "bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300"
              : validation.status === "success"
              ? "bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-300"
              : "bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-300"
          }`}
        >
          <div className="flex items-center gap-2">
            {validation.status === "checking" && (
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                  fill="none"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
            )}
            {validation.status === "success" && (
              <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fillRule="evenodd"
                  d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                  clipRule="evenodd"
                />
              </svg>
            )}
            {validation.status === "error" && (
              <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fillRule="evenodd"
                  d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
                  clipRule="evenodd"
                />
              </svg>
            )}
            <span className="text-sm">{validation.message}</span>
          </div>
          {validation.permissions && validation.permissions.length > 0 && (
            <div className="mt-2 text-xs">
              権限: {validation.permissions.join(", ")}
            </div>
          )}
        </div>
      )}

      {/* Skip Option */}
      <div className="pt-2 border-t border-gray-200 dark:border-gray-700">
        <button
          type="button"
          onClick={handleSkip}
          disabled={disabled}
          className="text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300"
        >
          GitHub 連携をスキップ
        </button>
      </div>
    </div>
  );
}

export default RepoSelector;
