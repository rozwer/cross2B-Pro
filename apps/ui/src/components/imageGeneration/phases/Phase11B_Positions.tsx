"use client";

import { useState, useEffect, useCallback } from "react";
import {
  ArrowLeft,
  ArrowRight,
  RefreshCw,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { ImagePosition, Section } from "@/lib/types";
import { SortablePositionList } from "./SortablePositionList";
import { ArticlePreviewWithMarkers } from "./ArticlePreviewWithMarkers";

interface Phase11B_PositionsProps {
  positions: ImagePosition[];
  sections: Section[];
  analysisSummary: string;
  articleMarkdown?: string;
  onConfirm: (positions: ImagePosition[]) => void;
  onReanalyze: (request: string) => void;
  onBack: () => void;
  loading?: boolean;
}

export function Phase11B_Positions({
  positions: initialPositions,
  sections,
  analysisSummary,
  articleMarkdown = "",
  onConfirm,
  onReanalyze,
  onBack,
  loading = false,
}: Phase11B_PositionsProps) {
  const [positions, setPositions] = useState<ImagePosition[]>(initialPositions);
  const [showReanalyzeInput, setShowReanalyzeInput] = useState(false);
  const [reanalyzeRequest, setReanalyzeRequest] = useState("");
  const [showAddForm, setShowAddForm] = useState(false);
  const [newPosition, setNewPosition] = useState<Partial<ImagePosition>>({
    article_number: sections[0]?.article_number ?? 1,
    section_title: "",
    section_index: 0,
    position: "after",
    description: "",
  });

  // Sync positions state when initialPositions prop changes
  useEffect(() => {
    setPositions(initialPositions);
  }, [initialPositions]);

  // 位置追加（視覚的選択から）
  const handleAddFromPreview = useCallback(
    (section: Section, position: "before" | "after") => {
      const newPos: ImagePosition = {
        article_number: section.article_number ?? null,
        section_title: section.title,
        section_index: section.section_index ?? sections.indexOf(section),
        position,
        source_text: "",
        description: "",
      };
      setPositions((prev) => [...prev, newPos]);
    },
    [sections]
  );

  // 位置削除（視覚的選択から）
  const handleRemoveFromPreview = useCallback((index: number) => {
    setPositions((prev) => prev.filter((_, i) => i !== index));
  }, []);

  // 手動追加フォームから追加
  const handleAdd = () => {
    if (!newPosition.section_title) return;

    const position: ImagePosition = {
      article_number: newPosition.article_number ?? null,
      section_title: newPosition.section_title!,
      section_index: newPosition.section_index!,
      position: newPosition.position as "before" | "after",
      source_text: "",
      description: newPosition.description || "",
    };
    setPositions((prev) => [...prev, position]);
    setShowAddForm(false);
    setNewPosition({
      article_number: sections[0]?.article_number ?? 1,
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
    <div className="space-y-4">
      {/* 分析結果サマリー */}
      <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
        <h4 className="text-sm font-medium text-blue-800 dark:text-blue-200 mb-1">
          分析結果
        </h4>
        <p className="text-xs text-blue-700 dark:text-blue-300">
          {analysisSummary}
        </p>
      </div>

      {/* 2ペインレイアウト */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* 左ペイン: 記事プレビュー（視覚的位置選択） */}
        <div className="order-2 lg:order-1">
          <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
            記事プレビュー
          </h4>
          <ArticlePreviewWithMarkers
            markdown={articleMarkdown}
            sections={sections}
            positions={positions}
            onAddPosition={handleAddFromPreview}
            onRemovePosition={handleRemoveFromPreview}
          />
        </div>

        {/* 右ペイン: 位置リスト（ドラッグ&ドロップ） */}
        <div className="order-1 lg:order-2">
          <SortablePositionList
            positions={positions}
            sections={sections}
            disabled={loading}
            onPositionsChange={setPositions}
            onShowAddForm={() => setShowAddForm(true)}
          />

          {/* 追加フォーム */}
          {showAddForm && (
            <div className="mt-3 p-4 bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 rounded-lg space-y-3">
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
                          section_index: section.section_index ?? sections.indexOf(section),
                          article_number: section.article_number ?? prev.article_number,
                        }));
                      }
                    }}
                    className="w-full px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                  >
                    <option value="">選択してください</option>
                    {sections.map((section, i) => (
                      <option key={section.section_key ?? i} value={section.title}>
                        {section.article_number ? `記事${section.article_number}: ` : ""}{section.title}
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
                  className="px-3 py-1 text-sm bg-primary-600 text-white rounded hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  追加
                </button>
              </div>
            </div>
          )}
        </div>
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
            "bg-primary-600 text-white hover:bg-primary-700",
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
