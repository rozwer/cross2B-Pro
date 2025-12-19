"use client";

import { useState } from "react";
import {
  ArrowLeft,
  Check,
  Loader2,
  RotateCcw,
  ExternalLink,
  Code,
  Eye,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface Phase11E_PreviewProps {
  previewHtml: string;
  previewAvailable: boolean;
  onComplete: () => void;
  onRestartFrom: (phase: string) => void;
  loading?: boolean;
}

export function Phase11E_Preview({
  previewHtml,
  previewAvailable,
  onComplete,
  onRestartFrom,
  loading = false,
}: Phase11E_PreviewProps) {
  const [viewMode, setViewMode] = useState<"preview" | "html">("preview");
  const [showRestartOptions, setShowRestartOptions] = useState(false);

  return (
    <div className="space-y-6">
      {/* 説明 */}
      <div className="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg">
        <p className="text-sm text-green-800 dark:text-green-200">
          画像が挿入された記事のプレビューです。問題がなければ完了してください。
          修正が必要な場合は「画像指示に戻る」から再調整できます。
        </p>
      </div>

      {/* ビューモード切り替え */}
      <div className="flex items-center gap-2">
        <button
          onClick={() => setViewMode("preview")}
          className={cn(
            "inline-flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg transition-colors",
            viewMode === "preview"
              ? "bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300"
              : "text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700"
          )}
        >
          <Eye className="h-4 w-4" />
          プレビュー
        </button>
        <button
          onClick={() => setViewMode("html")}
          className={cn(
            "inline-flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg transition-colors",
            viewMode === "html"
              ? "bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300"
              : "text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700"
          )}
        >
          <Code className="h-4 w-4" />
          HTMLソース
        </button>
      </div>

      {/* プレビュー表示 */}
      <div className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden bg-white dark:bg-gray-900">
        {!previewAvailable ? (
          <div className="flex items-center justify-center h-64 text-gray-500 dark:text-gray-400">
            プレビューを読み込み中...
          </div>
        ) : viewMode === "preview" ? (
          <iframe
            srcDoc={previewHtml}
            title="Article Preview"
            className="w-full h-96 border-0"
            sandbox="allow-same-origin"
          />
        ) : (
          <pre className="p-4 h-96 overflow-auto text-xs text-gray-800 dark:text-gray-200 whitespace-pre-wrap">
            {previewHtml}
          </pre>
        )}
      </div>

      {/* 再開オプション */}
      {showRestartOptions && (
        <div className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg space-y-3">
          <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
            どこからやり直しますか？
          </p>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => onRestartFrom("11C")}
              disabled={loading}
              className="px-3 py-1.5 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300"
            >
              画像指示から（11C）
            </button>
          </div>
          <button
            onClick={() => setShowRestartOptions(false)}
            className="text-xs text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300"
          >
            キャンセル
          </button>
        </div>
      )}

      {/* アクションボタン */}
      <div className="flex items-center justify-between pt-4 border-t border-gray-200 dark:border-gray-700">
        <button
          onClick={() => setShowRestartOptions(true)}
          disabled={loading || showRestartOptions}
          className={cn(
            "inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg transition-colors",
            "text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700",
            (loading || showRestartOptions) && "opacity-50 cursor-not-allowed"
          )}
        >
          <RotateCcw className="h-4 w-4" />
          やり直す
        </button>

        <button
          onClick={onComplete}
          disabled={loading || !previewAvailable}
          className={cn(
            "inline-flex items-center gap-2 px-6 py-2 text-sm font-medium rounded-lg transition-colors",
            "bg-gradient-to-r from-green-600 to-emerald-600 text-white hover:from-green-700 hover:to-emerald-700",
            (loading || !previewAvailable) && "opacity-50 cursor-not-allowed"
          )}
        >
          {loading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              完了処理中...
            </>
          ) : (
            <>
              <Check className="h-4 w-4" />
              完了
            </>
          )}
        </button>
      </div>
    </div>
  );
}
