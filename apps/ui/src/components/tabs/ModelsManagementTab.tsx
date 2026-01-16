"use client";

import { useState, useEffect, useCallback } from "react";
import {
  RefreshCw,
  Plus,
  Trash2,
  ChevronDown,
  ChevronRight,
  Check,
  X,
  AlertCircle,
} from "lucide-react";
import api from "@/lib/api";
import type { LLMProviderWithModels, LLMModel } from "@/lib/types";

interface AddModelFormData {
  provider_id: string;
  model_name: string;
  model_class: string;
}

export function ModelsManagementTab() {
  const [providers, setProviders] = useState<LLMProviderWithModels[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedProviders, setExpandedProviders] = useState<Set<string>>(new Set(["gemini", "openai", "anthropic"]));

  // Add model state
  const [showAddForm, setShowAddForm] = useState(false);
  const [addFormData, setAddFormData] = useState<AddModelFormData>({
    provider_id: "gemini",
    model_name: "",
    model_class: "standard",
  });
  const [addLoading, setAddLoading] = useState(false);
  const [addError, setAddError] = useState<string | null>(null);

  // Delete confirmation
  const [deleteConfirm, setDeleteConfirm] = useState<number | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);

  const loadProviders = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.models.list();
      setProviders(response.providers);
    } catch (err) {
      setError(err instanceof Error ? err.message : "モデルの読み込みに失敗しました");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadProviders();
  }, [loadProviders]);

  const toggleProvider = (providerId: string) => {
    setExpandedProviders((prev) => {
      const next = new Set(prev);
      if (next.has(providerId)) {
        next.delete(providerId);
      } else {
        next.add(providerId);
      }
      return next;
    });
  };

  const handleAddModel = async () => {
    if (!addFormData.model_name.trim()) {
      setAddError("モデル名を入力してください");
      return;
    }

    setAddLoading(true);
    setAddError(null);
    try {
      await api.models.create({
        provider_id: addFormData.provider_id,
        model_name: addFormData.model_name.trim(),
        model_class: addFormData.model_class,
      });
      setShowAddForm(false);
      setAddFormData({ provider_id: "gemini", model_name: "", model_class: "standard" });
      await loadProviders();
    } catch (err) {
      setAddError(err instanceof Error ? err.message : "モデルの追加に失敗しました");
    } finally {
      setAddLoading(false);
    }
  };

  const handleDeleteModel = async (modelId: number) => {
    setDeleteLoading(true);
    try {
      await api.models.delete(modelId);
      setDeleteConfirm(null);
      await loadProviders();
    } catch (err) {
      setError(err instanceof Error ? err.message : "モデルの削除に失敗しました");
    } finally {
      setDeleteLoading(false);
    }
  };

  const handleToggleActive = async (model: LLMModel) => {
    try {
      await api.models.update(model.id, { is_active: !model.is_active });
      await loadProviders();
    } catch (err) {
      setError(err instanceof Error ? err.message : "状態の更新に失敗しました");
    }
  };

  const getProviderColor = (providerId: string): string => {
    switch (providerId) {
      case "gemini":
        return "text-blue-600 dark:text-blue-400";
      case "openai":
        return "text-green-600 dark:text-green-400";
      case "anthropic":
        return "text-orange-600 dark:text-orange-400";
      default:
        return "text-gray-600 dark:text-gray-400";
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <RefreshCw className="h-6 w-6 animate-spin text-primary-500" />
        <span className="ml-2 text-gray-500 dark:text-gray-400">読み込み中...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            LLMモデル管理
          </h2>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            利用可能なLLMモデルの追加・削除を行います
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={loadProviders}
            className="inline-flex items-center gap-2 px-3 py-2 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
          >
            <RefreshCw className="h-4 w-4" />
            更新
          </button>
          <button
            onClick={() => setShowAddForm(true)}
            className="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 rounded-lg transition-colors"
          >
            <Plus className="h-4 w-4" />
            モデル追加
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
          <AlertCircle className="h-5 w-5 text-red-500" />
          <p className="text-sm text-red-700 dark:text-red-400">{error}</p>
        </div>
      )}

      {/* Add Model Form */}
      {showAddForm && (
        <div className="p-4 bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 rounded-lg">
          <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-4">
            新しいモデルを追加
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                プロバイダー
              </label>
              <select
                value={addFormData.provider_id}
                onChange={(e) => setAddFormData((prev) => ({ ...prev, provider_id: e.target.value }))}
                className="w-full px-3 py-2 text-sm border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                <option value="gemini">Google Gemini</option>
                <option value="openai">OpenAI</option>
                <option value="anthropic">Anthropic Claude</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                モデル名
              </label>
              <input
                type="text"
                value={addFormData.model_name}
                onChange={(e) => setAddFormData((prev) => ({ ...prev, model_name: e.target.value }))}
                placeholder="例: gemini-3.0-flash"
                className="w-full px-3 py-2 text-sm border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                モデルクラス
              </label>
              <select
                value={addFormData.model_class}
                onChange={(e) => setAddFormData((prev) => ({ ...prev, model_class: e.target.value }))}
                className="w-full px-3 py-2 text-sm border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                <option value="standard">Standard</option>
                <option value="pro">Pro</option>
              </select>
            </div>
          </div>
          {addError && (
            <p className="mt-2 text-sm text-red-600 dark:text-red-400">{addError}</p>
          )}
          <div className="mt-4 flex items-center justify-end gap-2">
            <button
              onClick={() => {
                setShowAddForm(false);
                setAddError(null);
              }}
              className="px-3 py-2 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition-colors"
            >
              キャンセル
            </button>
            <button
              onClick={handleAddModel}
              disabled={addLoading}
              className="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 rounded-lg transition-colors disabled:opacity-50"
            >
              {addLoading ? (
                <RefreshCw className="h-4 w-4 animate-spin" />
              ) : (
                <Plus className="h-4 w-4" />
              )}
              追加
            </button>
          </div>
        </div>
      )}

      {/* Providers List */}
      <div className="space-y-4">
        {providers.map((provider) => (
          <div
            key={provider.id}
            className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden"
          >
            {/* Provider Header */}
            <button
              onClick={() => toggleProvider(provider.id)}
              className="w-full flex items-center justify-between px-4 py-3 bg-gray-50 dark:bg-gray-800/50 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            >
              <div className="flex items-center gap-3">
                {expandedProviders.has(provider.id) ? (
                  <ChevronDown className="h-4 w-4 text-gray-400" />
                ) : (
                  <ChevronRight className="h-4 w-4 text-gray-400" />
                )}
                <span className={`font-medium ${getProviderColor(provider.id)}`}>
                  {provider.display_name}
                </span>
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  ({provider.models.length} モデル)
                </span>
              </div>
              {!provider.is_active && (
                <span className="px-2 py-0.5 text-xs bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded">
                  無効
                </span>
              )}
            </button>

            {/* Models List */}
            {expandedProviders.has(provider.id) && (
              <div className="divide-y divide-gray-200 dark:divide-gray-700">
                {provider.models.length === 0 ? (
                  <div className="px-4 py-6 text-center text-sm text-gray-500 dark:text-gray-400">
                    モデルがありません
                  </div>
                ) : (
                  provider.models.map((model) => (
                    <div
                      key={model.id}
                      className={`px-4 py-3 flex items-center justify-between ${
                        !model.is_active ? "bg-gray-50 dark:bg-gray-900/50 opacity-60" : ""
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <code className="text-sm font-mono text-gray-900 dark:text-gray-100">
                          {model.model_name}
                        </code>
                        <span
                          className={`px-2 py-0.5 text-xs rounded ${
                            model.model_class === "pro"
                              ? "bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400"
                              : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400"
                          }`}
                        >
                          {model.model_class}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        {/* Toggle Active */}
                        <button
                          onClick={() => handleToggleActive(model)}
                          className={`p-1.5 rounded-lg transition-colors ${
                            model.is_active
                              ? "text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20"
                              : "text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800"
                          }`}
                          title={model.is_active ? "無効にする" : "有効にする"}
                        >
                          {model.is_active ? (
                            <Check className="h-4 w-4" />
                          ) : (
                            <X className="h-4 w-4" />
                          )}
                        </button>

                        {/* Delete */}
                        {deleteConfirm === model.id ? (
                          <div className="flex items-center gap-1">
                            <button
                              onClick={() => handleDeleteModel(model.id)}
                              disabled={deleteLoading}
                              className="px-2 py-1 text-xs font-medium text-white bg-red-600 hover:bg-red-700 rounded transition-colors disabled:opacity-50"
                            >
                              {deleteLoading ? "..." : "削除"}
                            </button>
                            <button
                              onClick={() => setDeleteConfirm(null)}
                              className="px-2 py-1 text-xs text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 rounded transition-colors"
                            >
                              キャンセル
                            </button>
                          </div>
                        ) : (
                          <button
                            onClick={() => setDeleteConfirm(model.id)}
                            className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                            title="削除"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Info */}
      <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
        <p className="text-sm text-blue-700 dark:text-blue-400">
          ここで追加したモデルは、ワークフロー設定のモデル選択で利用できるようになります。
          新しいモデルがリリースされた場合は、ここから追加してください。
        </p>
      </div>
    </div>
  );
}
