"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Key,
  Check,
  X,
  RefreshCw,
  Eye,
  EyeOff,
  AlertCircle,
  CheckCircle2,
  Trash2,
  ExternalLink,
  Server,
  Zap,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { ProviderLogo } from "@/components/icons/ProviderLogos";
import api from "@/lib/api";
import type {
  ServiceType,
  ApiSettingResponse,
  ApiSettingUpdateRequest,
  ConnectionTestResponse,
} from "@/lib/types";

// Service definitions
const SERVICE_INFO: Record<
  ServiceType,
  {
    name: string;
    description: string;
    isLLM: boolean;
    docsUrl: string;
    color: string;
    bgColor: string;
    borderColor: string;
    icon: "gemini" | "openai" | "anthropic" | "server";
    warningMessage?: string;
  }
> = {
  gemini: {
    name: "Google Gemini",
    description: "Google AIのLLMサービス（Grounding、Code Execution対応）",
    isLLM: true,
    docsUrl: "https://ai.google.dev/",
    color: "text-blue-700 dark:text-blue-300",
    bgColor: "bg-blue-50 dark:bg-blue-900/30",
    borderColor: "border-blue-200 dark:border-blue-800",
    icon: "gemini",
  },
  openai: {
    name: "OpenAI",
    description: "GPT-4o、GPT-5系のLLMサービス",
    isLLM: true,
    docsUrl: "https://platform.openai.com/",
    color: "text-green-700 dark:text-green-300",
    bgColor: "bg-green-50 dark:bg-green-900/30",
    borderColor: "border-green-200 dark:border-green-800",
    icon: "openai",
  },
  anthropic: {
    name: "Anthropic Claude",
    description: "Claude 3.5/4系のLLMサービス（Extended Thinking対応）",
    isLLM: true,
    docsUrl: "https://console.anthropic.com/",
    color: "text-orange-700 dark:text-orange-300",
    bgColor: "bg-orange-50 dark:bg-orange-900/30",
    borderColor: "border-orange-200 dark:border-orange-800",
    icon: "anthropic",
  },
  serp: {
    name: "SERP API",
    description: "Google検索結果取得API",
    isLLM: false,
    docsUrl: "https://serpapi.com/",
    color: "text-purple-700 dark:text-purple-300",
    bgColor: "bg-purple-50 dark:bg-purple-900/30",
    borderColor: "border-purple-200 dark:border-purple-800",
    icon: "server",
  },
  google_ads: {
    name: "Google Ads",
    description: "Keyword Planner API（検索ボリューム・関連キーワード取得）",
    isLLM: false,
    docsUrl: "https://ads.google.com/",
    color: "text-yellow-700 dark:text-yellow-300",
    bgColor: "bg-yellow-50 dark:bg-yellow-900/30",
    borderColor: "border-yellow-200 dark:border-yellow-800",
    icon: "server",
  },
  github: {
    name: "GitHub",
    description: "記事管理・外部編集連携",
    isLLM: false,
    docsUrl: "https://github.com/settings/tokens",
    color: "text-gray-700 dark:text-gray-300",
    bgColor: "bg-gray-50 dark:bg-gray-800/50",
    borderColor: "border-gray-200 dark:border-gray-700",
    icon: "server",
    warningMessage: "GitHubトークンは露出すると自動で無効化されます。取り扱いに注意してください。",
  },
};

const SERVICE_ORDER: ServiceType[] = ["gemini", "openai", "anthropic", "serp", "google_ads", "github"];

interface ServiceCardProps {
  service: ServiceType;
  setting: ApiSettingResponse | null;
  onUpdate: (service: ServiceType, data: ApiSettingUpdateRequest) => Promise<void>;
  onDelete: (service: ServiceType) => Promise<void>;
  onTest: (service: ServiceType, apiKey?: string, model?: string) => Promise<ConnectionTestResponse>;
}

function ServiceCard({ service, setting, onUpdate, onDelete, onTest }: ServiceCardProps) {
  const info = SERVICE_INFO[service];
  const [isExpanded, setIsExpanded] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [apiKey, setApiKey] = useState("");
  const [defaultModel, setDefaultModel] = useState(setting?.default_model || "");
  const [showApiKey, setShowApiKey] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [testResult, setTestResult] = useState<ConnectionTestResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Google Ads multi-field state
  const [gadsClientId, setGadsClientId] = useState(setting?.config?.client_id || "");
  const [gadsClientSecret, setGadsClientSecret] = useState(setting?.config?.client_secret || "");
  const [gadsRefreshToken, setGadsRefreshToken] = useState(setting?.config?.refresh_token || "");
  const [gadsCustomerId, setGadsCustomerId] = useState(setting?.config?.customer_id || "");
  const [showGadsSecrets, setShowGadsSecrets] = useState(false);
  const [isOAuthInProgress, setIsOAuthInProgress] = useState(false);

  const hasKey = setting?.api_key_masked && setting.api_key_masked !== "";
  const isEnvFallback = setting?.env_fallback;
  const isVerified = setting?.verified_at !== null;

  // Listen for OAuth callback postMessage (Google Ads refresh token)
  useEffect(() => {
    if (!isOAuthInProgress) return;
    const handleMessage = (event: MessageEvent) => {
      if (event.data?.type === "google-ads-oauth-callback" && event.data?.refresh_token) {
        setGadsRefreshToken(event.data.refresh_token);
        setIsOAuthInProgress(false);
      }
    };
    window.addEventListener("message", handleMessage);
    return () => window.removeEventListener("message", handleMessage);
  }, [isOAuthInProgress]);

  const handleOAuthRefreshToken = async () => {
    if (!gadsClientId || !gadsClientSecret) {
      setError("Refresh Token の取得には Client ID と Client Secret が必要です");
      return;
    }
    setIsOAuthInProgress(true);
    setError(null);
    try {
      const res = await fetch("/api/settings/google-ads/oauth-start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ client_id: gadsClientId, client_secret: gadsClientSecret }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({ detail: "OAuth開始に失敗しました" }));
        throw new Error(data.detail || "OAuth開始に失敗しました");
      }
      const data = await res.json();
      const popup = window.open(data.auth_url, "google_ads_oauth", "width=600,height=700,left=200,top=100");
      // Monitor popup close to reset state
      const checkClosed = setInterval(() => {
        if (popup?.closed) {
          clearInterval(checkClosed);
          setIsOAuthInProgress(false);
        }
      }, 1000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "OAuth開始に失敗しました");
      setIsOAuthInProgress(false);
    }
  };

  const handleTest = async () => {
    setIsTesting(true);
    setTestResult(null);
    setError(null);
    try {
      // Test with new key if editing, otherwise use stored key
      const result = await onTest(service, isEditing && apiKey ? apiKey : undefined, defaultModel || undefined);
      setTestResult(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "テスト失敗");
    } finally {
      setIsTesting(false);
    }
  };

  const handleSave = async () => {
    setIsSaving(true);
    setError(null);
    try {
      const updateData: ApiSettingUpdateRequest = {
        api_key: apiKey || undefined,
        default_model: info.isLLM ? defaultModel || undefined : undefined,
        is_active: true,
      };
      // Google Ads: save additional credentials in config
      if (service === "google_ads") {
        updateData.config = {
          client_id: gadsClientId || undefined,
          client_secret: gadsClientSecret || undefined,
          refresh_token: gadsRefreshToken || undefined,
          customer_id: gadsCustomerId || undefined,
        };
      }
      await onUpdate(service, updateData);
      setApiKey("");
      setIsEditing(false);
      // Auto-test after save
      await handleTest();
    } catch (err) {
      setError(err instanceof Error ? err.message : "保存失敗");
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm(`${info.name}の設定を削除しますか？\n環境変数にフォールバックします。`)) {
      return;
    }
    setError(null);
    try {
      await onDelete(service);
      setApiKey("");
      setDefaultModel("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "削除失敗");
    }
  };

  const renderIcon = () => {
    if (info.icon === "server") {
      return <Server className="w-6 h-6" />;
    }
    return <ProviderLogo platform={info.icon} size={24} />;
  };

  return (
    <div
      className={cn(
        "rounded-xl border-2 transition-all",
        isExpanded ? info.borderColor : "border-gray-200 dark:border-gray-700",
        isExpanded ? info.bgColor : "bg-white dark:bg-gray-800"
      )}
    >
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full p-4 flex items-center gap-4 text-left"
      >
        <div className={cn("p-2 rounded-lg", info.bgColor)}>
          {renderIcon()}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h3 className={cn("font-semibold", info.color)}>{info.name}</h3>
            {info.isLLM && (
              <span className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-primary-100 dark:bg-primary-900/40 text-primary-700 dark:text-primary-300 text-xs rounded">
                <Zap className="h-3 w-3" />
                LLM
              </span>
            )}
          </div>
          <p className="text-sm text-gray-500 dark:text-gray-400 truncate">
            {info.description}
          </p>
        </div>
        {/* Status indicators */}
        <div className="flex items-center gap-2">
          {hasKey ? (
            <div className="flex items-center gap-1.5">
              {isVerified ? (
                <CheckCircle2 className="h-5 w-5 text-green-500" />
              ) : (
                <AlertCircle className="h-5 w-5 text-yellow-500" />
              )}
              <span className="text-sm text-gray-600 dark:text-gray-400">
                {setting?.api_key_masked}
              </span>
              {isEnvFallback && (
                <span className="text-xs text-gray-400 dark:text-gray-500">(env)</span>
              )}
            </div>
          ) : (
            <span className="text-sm text-gray-400 dark:text-gray-500">未設定</span>
          )}
        </div>
      </button>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="px-4 pb-4 pt-2 border-t border-gray-200 dark:border-gray-700 space-y-4">
          {/* Warning message for GitHub */}
          {info.warningMessage && (
            <div className="flex items-start gap-2 p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
              <AlertCircle className="h-5 w-5 text-yellow-600 dark:text-yellow-400 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-yellow-700 dark:text-yellow-300">{info.warningMessage}</p>
            </div>
          )}

          {/* Current status */}
          <div className="flex items-center justify-between">
            <div className="text-sm text-gray-600 dark:text-gray-400">
              {isEnvFallback ? (
                <span>環境変数から読み込み中</span>
              ) : hasKey ? (
                <span>
                  最終検証: {setting?.verified_at ? new Date(setting.verified_at).toLocaleString() : "未検証"}
                </span>
              ) : (
                <span>APIキーが設定されていません</span>
              )}
            </div>
            <a
              href={info.docsUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-primary-600 dark:text-primary-400 hover:underline inline-flex items-center gap-1"
            >
              ドキュメント
              <ExternalLink className="h-3 w-3" />
            </a>
          </div>

          {/* Edit form */}
          {isEditing ? (
            <div className="space-y-4">
              {/* Google Ads: 5-field form */}
              {service === "google_ads" ? (
                <>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Developer Token
                    </label>
                    <div className="relative">
                      <input
                        type={showGadsSecrets ? "text" : "password"}
                        value={apiKey}
                        onChange={(e) => setApiKey(e.target.value)}
                        placeholder={hasKey ? "新しいトークンを入力（空欄で既存を保持）" : "Developer Token を入力"}
                        className="w-full px-3 py-2 pr-10 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-500"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      OAuth Client ID
                    </label>
                    <input
                      type="text"
                      value={gadsClientId}
                      onChange={(e) => setGadsClientId(e.target.value)}
                      placeholder="例: 123456789-xxxxx.apps.googleusercontent.com"
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      OAuth Client Secret
                    </label>
                    <div className="relative">
                      <input
                        type={showGadsSecrets ? "text" : "password"}
                        value={gadsClientSecret}
                        onChange={(e) => setGadsClientSecret(e.target.value)}
                        placeholder="GOCSPX-..."
                        className="w-full px-3 py-2 pr-10 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-500"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Refresh Token
                    </label>
                    <div className="relative">
                      <input
                        type={showGadsSecrets ? "text" : "password"}
                        value={gadsRefreshToken}
                        onChange={(e) => setGadsRefreshToken(e.target.value)}
                        placeholder="1//0e..."
                        className="w-full px-3 py-2 pr-10 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-500"
                      />
                    </div>
                    <button
                      type="button"
                      onClick={handleOAuthRefreshToken}
                      disabled={isOAuthInProgress}
                      className="mt-2 inline-flex items-center gap-1.5 px-3 py-1.5 text-sm bg-yellow-50 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300 border border-yellow-300 dark:border-yellow-700 rounded-lg hover:bg-yellow-100 dark:hover:bg-yellow-900/50 disabled:opacity-50 transition-colors"
                    >
                      {isOAuthInProgress ? (
                        <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <ExternalLink className="h-3.5 w-3.5" />
                      )}
                      {isOAuthInProgress ? "認証中..." : "Google アカウントから取得"}
                    </button>
                    <p className="mt-1 text-xs text-gray-400 dark:text-gray-500">
                      OAuth認証でRefresh Tokenを自動取得します（要: Google Cloud Consoleでリダイレクト URI を登録）
                    </p>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Customer ID
                    </label>
                    <input
                      type="text"
                      value={gadsCustomerId}
                      onChange={(e) => setGadsCustomerId(e.target.value)}
                      placeholder="例: 123-456-7890"
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-500"
                    />
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => setShowGadsSecrets(!showGadsSecrets)}
                      className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
                    >
                      {showGadsSecrets ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      {showGadsSecrets ? "シークレットを隠す" : "シークレットを表示"}
                    </button>
                  </div>
                </>
              ) : (
                <>
                  {/* Default: single API key field */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      APIキー
                    </label>
                    <div className="relative">
                      <input
                        type={showApiKey ? "text" : "password"}
                        value={apiKey}
                        onChange={(e) => setApiKey(e.target.value)}
                        placeholder={hasKey ? "新しいキーを入力（空欄で既存キーを保持）" : "APIキーを入力"}
                        className="w-full px-3 py-2 pr-10 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-500"
                      />
                      <button
                        type="button"
                        onClick={() => setShowApiKey(!showApiKey)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
                      >
                        {showApiKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </button>
                    </div>
                  </div>

                  {info.isLLM && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        デフォルトモデル（任意）
                      </label>
                      <input
                        type="text"
                        value={defaultModel}
                        onChange={(e) => setDefaultModel(e.target.value)}
                        placeholder={`例: ${service === "gemini" ? "gemini-2.5-flash" : service === "openai" ? "gpt-4o" : "claude-3-5-sonnet"}`}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-500"
                      />
                    </div>
                  )}
                </>
              )}

              <div className="flex items-center gap-2">
                <button
                  onClick={handleSave}
                  disabled={isSaving}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 transition-colors"
                >
                  {isSaving ? (
                    <RefreshCw className="h-4 w-4 animate-spin" />
                  ) : (
                    <Check className="h-4 w-4" />
                  )}
                  保存
                </button>
                <button
                  onClick={() => {
                    setIsEditing(false);
                    setApiKey("");
                    setError(null);
                  }}
                  className="inline-flex items-center gap-2 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                >
                  <X className="h-4 w-4" />
                  キャンセル
                </button>
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <button
                onClick={() => setIsEditing(true)}
                className="inline-flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
              >
                <Key className="h-4 w-4" />
                {hasKey ? "キーを変更" : "キーを設定"}
              </button>
              <button
                onClick={handleTest}
                disabled={isTesting || !hasKey}
                className="inline-flex items-center gap-2 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 transition-colors"
              >
                {isTesting ? (
                  <RefreshCw className="h-4 w-4 animate-spin" />
                ) : (
                  <RefreshCw className="h-4 w-4" />
                )}
                接続テスト
              </button>
              {hasKey && !isEnvFallback && (
                <button
                  onClick={handleDelete}
                  className="inline-flex items-center gap-2 px-4 py-2 text-red-600 dark:text-red-400 border border-red-300 dark:border-red-700 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                >
                  <Trash2 className="h-4 w-4" />
                  削除
                </button>
              )}
            </div>
          )}

          {/* Test result */}
          {testResult && (
            <div
              className={cn(
                "p-3 rounded-lg border",
                testResult.success
                  ? "bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800"
                  : "bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800"
              )}
            >
              <div className="flex items-center gap-2">
                {testResult.success ? (
                  <CheckCircle2 className="h-5 w-5 text-green-600 dark:text-green-400" />
                ) : (
                  <AlertCircle className="h-5 w-5 text-red-600 dark:text-red-400" />
                )}
                <span
                  className={cn(
                    "font-medium",
                    testResult.success
                      ? "text-green-700 dark:text-green-300"
                      : "text-red-700 dark:text-red-300"
                  )}
                >
                  {testResult.success ? "接続成功" : "接続失敗"}
                </span>
                {testResult.latency_ms && (
                  <span className="text-sm text-gray-500 dark:text-gray-400">
                    ({testResult.latency_ms}ms)
                  </span>
                )}
              </div>
              {testResult.error_message && (
                <p className="mt-1 text-sm text-red-600 dark:text-red-400">
                  {testResult.error_message}
                </p>
              )}
              {/* GitHub scope warning */}
              {service === "github" && testResult.scope_warning && (
                <div className="mt-2 p-2 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded">
                  <div className="flex items-start gap-2">
                    <AlertCircle className="h-4 w-4 text-yellow-600 dark:text-yellow-400 flex-shrink-0 mt-0.5" />
                    <div className="text-sm text-yellow-700 dark:text-yellow-300">
                      <p className="font-medium">権限の警告</p>
                      <p>{testResult.scope_warning}</p>
                    </div>
                  </div>
                </div>
              )}
              {/* GitHub scopes display */}
              {service === "github" && testResult.scopes && testResult.scopes.length > 0 && (
                <div className="mt-2">
                  <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">付与されたスコープ:</p>
                  <div className="flex flex-wrap gap-1">
                    {testResult.scopes.map((scope) => (
                      <span
                        key={scope}
                        className={cn(
                          "px-1.5 py-0.5 text-xs rounded",
                          testResult.missing_scopes?.includes(scope)
                            ? "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300"
                            : "bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300"
                        )}
                      >
                        {scope}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {/* GitHub fine-grained PAT notice */}
              {service === "github" && testResult.success && testResult.details?.token_type === "fine-grained" && (
                <div className="mt-2 p-2 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded">
                  <p className="text-xs text-blue-700 dark:text-blue-300">
                    Fine-grained Personal Access Token を使用しています。スコープの詳細確認はGitHub設定画面で行ってください。
                  </p>
                </div>
              )}
              {/* GitHub missing scopes */}
              {service === "github" && testResult.missing_scopes && testResult.missing_scopes.length > 0 && (
                <div className="mt-2">
                  <p className="text-xs text-red-500 dark:text-red-400 mb-1">不足しているスコープ:</p>
                  <div className="flex flex-wrap gap-1">
                    {testResult.missing_scopes.map((scope) => (
                      <span
                        key={scope}
                        className="px-1.5 py-0.5 text-xs bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 rounded"
                      >
                        {scope}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {testResult.details && Object.keys(testResult.details).length > 0 && (
                <pre className="mt-2 text-xs text-gray-600 dark:text-gray-400 overflow-x-auto">
                  {JSON.stringify(testResult.details, null, 2)}
                </pre>
              )}
            </div>
          )}

          {/* Error message */}
          {error && (
            <div className="p-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
              <div className="flex items-center gap-2">
                <AlertCircle className="h-5 w-5 text-red-600 dark:text-red-400" />
                <span className="text-red-700 dark:text-red-300">{error}</span>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function ApiKeysTab() {
  const [settings, setSettings] = useState<ApiSettingResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadSettings = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await api.settings.list();
      setSettings(response.settings);
    } catch (err) {
      setError(err instanceof Error ? err.message : "設定の読み込みに失敗しました");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSettings();
  }, [loadSettings]);

  const handleUpdate = async (service: ServiceType, data: ApiSettingUpdateRequest) => {
    await api.settings.update(service, data);
    await loadSettings();  // Refresh list
  };

  const handleDelete = async (service: ServiceType) => {
    await api.settings.delete(service);
    await loadSettings();  // Refresh list
  };

  const handleTest = async (service: ServiceType, apiKey?: string, model?: string) => {
    return await api.settings.test(service, apiKey, model);
  };

  const getSettingForService = (service: ServiceType): ApiSettingResponse | null => {
    return settings.find((s) => s.service === service) || null;
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <RefreshCw className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl">
        <div className="flex items-center gap-2 mb-2">
          <AlertCircle className="h-5 w-5 text-red-600 dark:text-red-400" />
          <span className="font-medium text-red-700 dark:text-red-300">エラー</span>
        </div>
        <p className="text-red-600 dark:text-red-400">{error}</p>
        <button
          onClick={loadSettings}
          className="mt-4 inline-flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
        >
          <RefreshCw className="h-4 w-4" />
          再読み込み
        </button>
      </div>
    );
  }

  // Group services
  const llmServices = SERVICE_ORDER.filter((s) => SERVICE_INFO[s].isLLM);
  const externalServices = SERVICE_ORDER.filter((s) => !SERVICE_INFO[s].isLLM);

  return (
    <div className="space-y-8">
      {/* LLM Services */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4 flex items-center gap-2">
          <Zap className="h-5 w-5 text-primary-600 dark:text-primary-400" />
          LLMサービス
        </h2>
        <div className="space-y-4">
          {llmServices.map((service) => (
            <ServiceCard
              key={service}
              service={service}
              setting={getSettingForService(service)}
              onUpdate={handleUpdate}
              onDelete={handleDelete}
              onTest={handleTest}
            />
          ))}
        </div>
      </div>

      {/* External Services */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4 flex items-center gap-2">
          <Server className="h-5 w-5 text-primary-600 dark:text-primary-400" />
          外部サービス
        </h2>
        <div className="space-y-4">
          {externalServices.map((service) => (
            <ServiceCard
              key={service}
              service={service}
              setting={getSettingForService(service)}
              onUpdate={handleUpdate}
              onDelete={handleDelete}
              onTest={handleTest}
            />
          ))}
        </div>
      </div>

      {/* Help text */}
      <div className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-xl border border-gray-200 dark:border-gray-700">
        <h3 className="font-medium text-gray-900 dark:text-gray-100 mb-2">環境変数について</h3>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          APIキーをここで設定しない場合、システムは環境変数から読み込みます。
          DBに保存されたキーは暗号化（AES-256-GCM）され、環境変数より優先されます。
        </p>
        <div className="mt-3 text-xs text-gray-500 dark:text-gray-500 font-mono">
          <div>GEMINI_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY</div>
          <div>SERP_API_KEY, GOOGLE_ADS_DEVELOPER_TOKEN, GITHUB_TOKEN</div>
        </div>
      </div>
    </div>
  );
}
