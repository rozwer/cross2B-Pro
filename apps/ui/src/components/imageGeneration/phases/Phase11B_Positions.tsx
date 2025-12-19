"use client";

import { useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  RefreshCw,
  Loader2,
  Trash2,
  Plus,
  Edit2,
  Check,
  MapPin,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { ImagePosition, Section } from "@/lib/types";

interface Phase11B_PositionsProps {
  positions: ImagePosition[];
  sections: Section[];
  analysisSummary: string;
  onConfirm: (positions: ImagePosition[]) => void;
  onReanalyze: (request: string) => void;
  onBack: () => void;
  loading?: boolean;
}

export function Phase11B_Positions({
  positions: initialPositions,
  sections,
  analysisSummary,
  onConfirm,
  onReanalyze,
  onBack,
  loading = false,
}: Phase11B_PositionsProps) {
  const [positions, setPositions] = useState<ImagePosition[]>(initialPositions);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [showReanalyzeInput, setShowReanalyzeInput] = useState(false);
  const [reanalyzeRequest, setReanalyzeRequest] = useState("");
  const [showAddForm, setShowAddForm] = useState(false);
  const [newPosition, setNewPosition] = useState<Partial<ImagePosition>>({
    section_title: "",
    section_index: 0,
    position: "after",
    description: "",
  });

  const handleDelete = (index: number) => {
    setPositions((prev) => prev.filter((_, i) => i !== index));
  };

  const handleEdit = (index: number, field: keyof ImagePosition, value: string | number) => {
    setPositions((prev) =>
      prev.map((pos, i) =>
        i === index ? { ...pos, [field]: value } : pos
      )
    );
  };

  const handleAdd = () => {
    if (!newPosition.section_title) return;

    const position: ImagePosition = {
      section_title: newPosition.section_title!,
      section_index: newPosition.section_index!,
      position: newPosition.position as "before" | "after",
      source_text: "",  // 後方互換性のため空文字を設定
      description: newPosition.description || "",
    };
    setPositions((prev) => [...prev, position]);
    setShowAddForm(false);
    setNewPosition({
      section_title: "",
      section_index: 0,
      position: "after",
      description: "",
    });
  };

  const handleReanalyze = () => {
    onReanalyze(reanalyzeRequest);
    setShowReanalyzeInput(false);
    setReanalyzeRequest("");
  };

  return (
    <div className="space-y-6">
      {/* 分析結果サマリー */}
      <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
        <h4 className="text-sm font-medium text-blue-800 dark:text-blue-200 mb-2">
          分析結果
        </h4>
        <p className="text-sm text-blue-700 dark:text-blue-300">
          {analysisSummary}
        </p>
      </div>

      {/* 位置一覧 */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100">
            挿入位置 ({positions.length}件)
          </h4>
          <button
            onClick={() => setShowAddForm(true)}
            disabled={loading}
            className="inline-flex items-center gap-1 px-3 py-1 text-xs font-medium text-purple-600 dark:text-purple-400 hover:bg-purple-50 dark:hover:bg-purple-900/20 rounded-lg"
          >
            <Plus className="h-3 w-3" />
            追加
          </button>
        </div>

        {/* 位置カード */}
        <div className="space-y-2 max-h-64 overflow-y-auto">
          {positions.map((pos, index) => (
            <div
              key={index}
              className="p-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg"
            >
              {editingIndex === index ? (
                // 編集モード
                <div className="space-y-3">
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="text-xs text-gray-500 dark:text-gray-400">
                        セクション
                      </label>
                      <select
                        value={pos.section_title}
                        onChange={(e) => {
                          const section = sections.find(
                            (s) => s.title === e.target.value
                          );
                          if (section) {
                            handleEdit(index, "section_title", section.title);
                            handleEdit(index, "section_index", sections.indexOf(section));
                          }
                        }}
                        className="w-full px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                      >
                        {sections.map((section, i) => (
                          <option key={i} value={section.title}>
                            {section.title}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="text-xs text-gray-500 dark:text-gray-400">
                        位置
                      </label>
                      <select
                        value={pos.position}
                        onChange={(e) =>
                          handleEdit(index, "position", e.target.value)
                        }
                        className="w-full px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                      >
                        <option value="before">見出しの前</option>
                        <option value="after">見出しの後</option>
                      </select>
                    </div>
                  </div>
                  <div>
                    <label className="text-xs text-gray-500 dark:text-gray-400">
                      説明
                    </label>
                    <input
                      type="text"
                      value={pos.description}
                      onChange={(e) =>
                        handleEdit(index, "description", e.target.value)
                      }
                      className="w-full px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                    />
                  </div>
                  <div className="flex justify-end gap-2">
                    <button
                      onClick={() => setEditingIndex(null)}
                      className="p-1 text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20 rounded"
                    >
                      <Check className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              ) : (
                // 表示モード
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <MapPin className="h-4 w-4 text-purple-500 flex-shrink-0" />
                      <span className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                        {pos.section_title}
                      </span>
                      <span className="text-xs px-1.5 py-0.5 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded">
                        {pos.position === "before" ? "前" : "後"}
                      </span>
                    </div>
                    {pos.description && (
                      <p className="text-xs text-gray-500 dark:text-gray-400 line-clamp-2">
                        {pos.description}
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-1 flex-shrink-0 ml-2">
                    <button
                      onClick={() => setEditingIndex(index)}
                      disabled={loading}
                      className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                    >
                      <Edit2 className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => handleDelete(index)}
                      disabled={loading}
                      className="p-1 text-gray-400 hover:text-red-600 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>

        {/* 追加フォーム */}
        {showAddForm && (
          <div className="p-4 bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 rounded-lg space-y-3">
            <h5 className="text-sm font-medium text-gray-900 dark:text-gray-100">
              新しい挿入位置を追加
            </h5>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-xs text-gray-500 dark:text-gray-400">
                  セクション
                </label>
                <select
                  value={newPosition.section_title}
                  onChange={(e) => {
                    const section = sections.find((s) => s.title === e.target.value);
                    if (section) {
                      setNewPosition((prev) => ({
                        ...prev,
                        section_title: section.title,
                        section_index: sections.indexOf(section),
                      }));
                    }
                  }}
                  className="w-full px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                >
                  <option value="">選択してください</option>
                  {sections.map((section, i) => (
                    <option key={i} value={section.title}>
                      {section.title}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs text-gray-500 dark:text-gray-400">
                  位置
                </label>
                <select
                  value={newPosition.position}
                  onChange={(e) =>
                    setNewPosition((prev) => ({
                      ...prev,
                      position: e.target.value as "before" | "after",
                    }))
                  }
                  className="w-full px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                >
                  <option value="before">見出しの前</option>
                  <option value="after">見出しの後</option>
                </select>
              </div>
            </div>
            <div>
              <label className="text-xs text-gray-500 dark:text-gray-400">
                説明（任意）
              </label>
              <input
                type="text"
                value={newPosition.description}
                onChange={(e) =>
                  setNewPosition((prev) => ({ ...prev, description: e.target.value }))
                }
                placeholder="この位置に入れる画像の説明"
                className="w-full px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
              />
            </div>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setShowAddForm(false)}
                className="px-3 py-1 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
              >
                キャンセル
              </button>
              <button
                onClick={handleAdd}
                disabled={!newPosition.section_title}
                className="px-3 py-1 text-sm bg-purple-600 text-white rounded hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                追加
              </button>
            </div>
          </div>
        )}
      </div>

      {/* 再分析リクエスト */}
      {showReanalyzeInput && (
        <div className="p-4 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg space-y-3">
          <label className="text-sm font-medium text-yellow-800 dark:text-yellow-200">
            再分析のリクエスト
          </label>
          <textarea
            value={reanalyzeRequest}
            onChange={(e) => setReanalyzeRequest(e.target.value)}
            placeholder="例：「もっと導入部分に画像を配置してほしい」「技術的な説明の後に図解を入れてほしい」"
            rows={2}
            className="w-full px-3 py-2 text-sm border border-yellow-300 dark:border-yellow-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
          />
          <div className="flex justify-end gap-2">
            <button
              onClick={() => setShowReanalyzeInput(false)}
              className="px-3 py-1 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
            >
              キャンセル
            </button>
            <button
              onClick={handleReanalyze}
              disabled={loading}
              className="px-3 py-1 text-sm bg-yellow-600 text-white rounded hover:bg-yellow-700"
            >
              再分析
            </button>
          </div>
        </div>
      )}

      {/* アクションボタン */}
      <div className="flex items-center justify-between pt-4 border-t border-gray-200 dark:border-gray-700">
        <div className="flex gap-2">
          <button
            onClick={onBack}
            disabled={loading}
            className={cn(
              "inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg transition-colors",
              "text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700",
              loading && "opacity-50 cursor-not-allowed"
            )}
          >
            <ArrowLeft className="h-4 w-4" />
            戻る
          </button>
          <button
            onClick={() => setShowReanalyzeInput(true)}
            disabled={loading || showReanalyzeInput}
            className={cn(
              "inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg transition-colors",
              "text-yellow-600 dark:text-yellow-400 hover:bg-yellow-50 dark:hover:bg-yellow-900/20",
              (loading || showReanalyzeInput) && "opacity-50 cursor-not-allowed"
            )}
          >
            <RefreshCw className="h-4 w-4" />
            再分析
          </button>
        </div>

        <button
          onClick={() => onConfirm(positions)}
          disabled={loading || positions.length === 0}
          className={cn(
            "inline-flex items-center gap-2 px-6 py-2 text-sm font-medium rounded-lg transition-colors",
            "bg-gradient-to-r from-purple-600 to-pink-600 text-white hover:from-purple-700 hover:to-pink-700",
            (loading || positions.length === 0) && "opacity-50 cursor-not-allowed"
          )}
        >
          {loading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              処理中...
            </>
          ) : (
            <>
              <ArrowRight className="h-4 w-4" />
              次へ（画像指示）
            </>
          )}
        </button>
      </div>
    </div>
  );
}
