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
} from "lucide-react";
import api from "@/lib/api";
import type { ApiSettingResponse, ServiceConfig } from "@/lib/types";

interface GitHubConfig {
  default_repo_url: string;
  default_dir_path: string;
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
    } catch (err) {
      // 404 is expected if no settings exist yet
      if (err instanceof Error && err.message.includes("404")) {
        setSetting(null);
        setRepoUrl("");
        setDirPath("");
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
    </div>
  );
}
