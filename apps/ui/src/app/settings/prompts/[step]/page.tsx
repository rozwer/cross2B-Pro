"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter, useParams } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Save,
  Plus,
  Trash2,
  Info,
  Eye,
  EyeOff,
} from "lucide-react";
import api from "@/lib/api";
import type { Prompt, PromptVariableInfo } from "@/lib/types";
import { STEP_LABELS } from "@/lib/types";
import { Loading } from "@/components/common";

interface VariableEntry {
  name: string;
  info: PromptVariableInfo;
}

export default function EditPromptPage() {
  const router = useRouter();
  const params = useParams();
  const step = decodeURIComponent(params.step as string);

  const [prompt, setPrompt] = useState<Prompt | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Form state
  const [content, setContent] = useState("");
  const [variables, setVariables] = useState<VariableEntry[]>([]);
  const [showPreview, setShowPreview] = useState(false);

  const loadPrompt = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.prompts.getByStep(step);
      setPrompt(data);
      setContent(data.content);

      // Convert variables object to array
      if (data.variables) {
        setVariables(
          Object.entries(data.variables).map(([name, info]) => ({
            name,
            info: info as PromptVariableInfo,
          }))
        );
      } else {
        setVariables([]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load prompt");
    } finally {
      setLoading(false);
    }
  }, [step]);

  useEffect(() => {
    loadPrompt();
  }, [loadPrompt]);

  const handleAddVariable = () => {
    setVariables([
      ...variables,
      {
        name: "",
        info: {
          required: true,
          type: "string",
          description: "",
        },
      },
    ]);
  };

  const handleRemoveVariable = (index: number) => {
    setVariables(variables.filter((_, i) => i !== index));
  };

  const handleVariableChange = (
    index: number,
    field: "name" | keyof PromptVariableInfo,
    value: string | boolean
  ) => {
    setVariables(
      variables.map((v, i) => {
        if (i !== index) return v;
        if (field === "name") {
          return { ...v, name: value as string };
        }
        return {
          ...v,
          info: { ...v.info, [field]: value },
        };
      })
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!content.trim()) {
      setError("プロンプト内容を入力してください");
      return;
    }

    // Validate variable names
    const variableNames = variables.map((v) => v.name).filter((n) => n.trim());
    const uniqueNames = new Set(variableNames);
    if (variableNames.length !== uniqueNames.size) {
      setError("変数名が重複しています");
      return;
    }

    // Build variables object
    const variablesObj: Record<string, PromptVariableInfo> = {};
    for (const v of variables) {
      if (v.name.trim()) {
        variablesObj[v.name.trim()] = v.info;
      }
    }

    setSaving(true);
    setError(null);
    setSuccess(null);

    try {
      const updated = await api.prompts.updateByStep(step, {
        content,
        variables: Object.keys(variablesObj).length > 0 ? variablesObj : undefined,
      });
      setPrompt(updated);
      setSuccess(`保存しました（バージョン ${updated.version}）`);
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update prompt");
    } finally {
      setSaving(false);
    }
  };

  // Extract variables from content
  const extractedVariables = content.match(/\{\{(\w+)\}\}/g) || [];
  const suggestedVariables = Array.from(new Set(extractedVariables.map((v) => v.slice(2, -2))));
  const definedVariables = variables.map((v) => v.name);
  const undefinedVariables = suggestedVariables.filter(
    (v) => !definedVariables.includes(v)
  );

  // Generate preview with sample values
  const generatePreview = () => {
    let preview = content;
    for (const v of variables) {
      if (v.name) {
        const placeholder = `{{${v.name}}}`;
        const sampleValue = v.info.default !== undefined ? String(v.info.default) : `[${v.name}]`;
        preview = preview.split(placeholder).join(sampleValue);
      }
    }
    return preview;
  };

  if (loading) {
    return <Loading text="プロンプトを読み込み中..." />;
  }

  if (!prompt) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500 dark:text-gray-400">
          プロンプトが見つかりません: {step}
        </p>
        <Link href="/settings?tab=prompts" className="mt-4 btn btn-primary inline-flex">
          <ArrowLeft className="h-4 w-4" />
          一覧に戻る
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-4">
          <Link
            href="/settings?tab=prompts"
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
          >
            <ArrowLeft className="h-5 w-5 text-gray-500" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
              {STEP_LABELS[prompt.step] || prompt.step}
              <span className="ml-2 text-base font-normal text-gray-500 dark:text-gray-400">
                v{prompt.version}
              </span>
            </h1>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              {prompt.step}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowPreview(!showPreview)}
            className={`inline-flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg border transition-colors ${
              showPreview
                ? "bg-primary-50 dark:bg-primary-900/20 border-primary-200 dark:border-primary-800 text-primary-700 dark:text-primary-300"
                : "bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
            }`}
          >
            {showPreview ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            プレビュー
          </button>
        </div>
      </div>

      {/* Messages */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <p className="text-sm text-red-700 dark:text-red-400">{error}</p>
        </div>
      )}

      {success && (
        <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
          <p className="text-sm text-green-700 dark:text-green-400">{success}</p>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Content Editor */}
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            プロンプト内容 <span className="text-red-500">*</span>
          </label>
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">
            変数は <code className="bg-gray-100 dark:bg-gray-700 px-1 rounded">{"{{変数名}}"}</code>{" "}
            形式で記述してください
          </p>

          {showPreview ? (
            <div className="p-4 border border-gray-200 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-900">
              <pre className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap font-mono">
                {generatePreview()}
              </pre>
            </div>
          ) : (
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              rows={20}
              className="w-full px-3 py-2.5 text-sm font-mono border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-y"
              placeholder="プロンプト内容を入力..."
            />
          )}

          {/* Suggested Variables */}
          {!showPreview && undefinedVariables.length > 0 && (
            <div className="mt-3 p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
              <div className="flex items-start gap-2">
                <Info className="h-4 w-4 text-yellow-600 dark:text-yellow-400 mt-0.5 flex-shrink-0" />
                <div>
                  <p className="text-sm text-yellow-700 dark:text-yellow-400">
                    以下の変数が定義されていません：
                  </p>
                  <div className="mt-1 flex flex-wrap gap-1">
                    {undefinedVariables.map((v) => (
                      <button
                        key={v}
                        type="button"
                        onClick={() =>
                          setVariables([
                            ...variables,
                            {
                              name: v,
                              info: { required: true, type: "string", description: "" },
                            },
                          ])
                        }
                        className="inline-flex items-center px-2 py-0.5 text-xs font-mono bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400 rounded hover:bg-yellow-200 dark:hover:bg-yellow-900/50 transition-colors"
                      >
                        + {`{{${v}}}`}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Variables */}
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300">
                変数定義
              </h3>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                プロンプトで使用する変数を定義します
              </p>
            </div>
            <button
              type="button"
              onClick={handleAddVariable}
              className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-primary-600 dark:text-primary-400 bg-primary-50 dark:bg-primary-900/20 rounded-lg hover:bg-primary-100 dark:hover:bg-primary-900/30 transition-colors"
            >
              <Plus className="h-3 w-3" />
              変数を追加
            </button>
          </div>

          {variables.length === 0 ? (
            <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-4">
              変数が定義されていません
            </p>
          ) : (
            <div className="space-y-4">
              {variables.map((variable, index) => (
                <div
                  key={index}
                  className="p-4 border border-gray-200 dark:border-gray-700 rounded-lg"
                >
                  <div className="flex items-start justify-between gap-4 mb-3">
                    <input
                      type="text"
                      value={variable.name}
                      onChange={(e) =>
                        handleVariableChange(index, "name", e.target.value)
                      }
                      placeholder="変数名"
                      className="flex-1 px-3 py-2 text-sm font-mono border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    />
                    <button
                      type="button"
                      onClick={() => handleRemoveVariable(index)}
                      className="p-2 text-gray-400 hover:text-red-600 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div>
                      <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">
                        型
                      </label>
                      <select
                        value={variable.info.type}
                        onChange={(e) =>
                          handleVariableChange(index, "type", e.target.value)
                        }
                        className="w-full px-3 py-1.5 text-sm border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-500"
                      >
                        <option value="string">string</option>
                        <option value="number">number</option>
                        <option value="boolean">boolean</option>
                        <option value="array">array</option>
                        <option value="object">object</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">
                        必須
                      </label>
                      <select
                        value={variable.info.required.toString()}
                        onChange={(e) =>
                          handleVariableChange(index, "required", e.target.value === "true")
                        }
                        className="w-full px-3 py-1.5 text-sm border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-500"
                      >
                        <option value="true">必須</option>
                        <option value="false">任意</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">
                        デフォルト値
                      </label>
                      <input
                        type="text"
                        value={variable.info.default !== undefined ? String(variable.info.default) : ""}
                        onChange={(e) =>
                          handleVariableChange(index, "default", e.target.value)
                        }
                        placeholder="（任意）"
                        className="w-full px-3 py-1.5 text-sm border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-500"
                      />
                    </div>
                  </div>

                  <div className="mt-3">
                    <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">
                      説明
                    </label>
                    <input
                      type="text"
                      value={variable.info.description || ""}
                      onChange={(e) =>
                        handleVariableChange(index, "description", e.target.value)
                      }
                      placeholder="変数の説明"
                      className="w-full px-3 py-1.5 text-sm border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-500"
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Submit */}
        <div className="flex justify-end gap-3">
          <Link
            href="/settings?tab=prompts"
            className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
          >
            キャンセル
          </Link>
          <button type="submit" disabled={saving} className="btn btn-primary">
            {saving ? (
              <>
                <span className="h-4 w-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                保存中...
              </>
            ) : (
              <>
                <Save className="h-4 w-4" />
                保存
              </>
            )}
          </button>
        </div>
      </form>

      {/* Info */}
      <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
        <div className="flex items-start gap-2">
          <Info className="h-4 w-4 text-blue-600 dark:text-blue-400 mt-0.5 flex-shrink-0" />
          <div className="text-sm text-blue-700 dark:text-blue-400">
            <p className="font-medium">JSON ファイル編集</p>
            <p className="mt-1">
              保存すると JSON ファイル（default.json）が直接更新され、バージョンが自動的にインクリメントされます。
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
