"use client";

import { useState } from "react";
import {
  SkipForward,
  ArrowRight,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface Phase11A_SettingsProps {
  onSubmit: (settings: { imageCount: number; positionRequest: string }) => void;
  onSkip: () => void;
  loading?: boolean;
}

export function Phase11A_Settings({
  onSubmit,
  onSkip,
  loading = false,
}: Phase11A_SettingsProps) {
  const [imageCount, setImageCount] = useState(3);
  const [positionRequest, setPositionRequest] = useState("");

  const handleSubmit = () => {
    onSubmit({
      imageCount,
      positionRequest,
    });
  };

  return (
    <div className="space-y-6">
      {/* 説明 */}
      <div className="p-4 bg-gray-50 dark:bg-gray-900/50 border border-gray-200 dark:border-gray-700 rounded-lg">
        <p className="text-sm text-gray-600 dark:text-gray-400">
          AIが記事内容を分析し、画像挿入に適した位置を提案します。
          画像の枚数と挿入位置の希望を指定してください。
        </p>
      </div>

      {/* 画像枚数 */}
      <div className="space-y-2">
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
          生成する画像の枚数
        </label>
        <div className="flex items-center gap-4">
          <input
            type="range"
            min={1}
            max={10}
            value={imageCount}
            onChange={(e) => setImageCount(Number(e.target.value))}
            className="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-primary-600"
            disabled={loading}
          />
          <span className="w-12 text-center text-lg font-semibold text-gray-900 dark:text-gray-100">
            {imageCount}枚
          </span>
        </div>
        <p className="text-xs text-gray-500 dark:text-gray-400">
          最大10枚まで生成できます
        </p>
      </div>

      {/* 挿入位置のリクエスト */}
      <div className="space-y-2">
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
          挿入位置のリクエスト（任意）
        </label>
        <textarea
          value={positionRequest}
          onChange={(e) => setPositionRequest(e.target.value)}
          placeholder="例：「導入部分にアイキャッチ画像を入れてほしい」「各セクションの説明に図解を入れてほしい」"
          rows={3}
          className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none"
          disabled={loading}
        />
        <p className="text-xs text-gray-500 dark:text-gray-400">
          指定がない場合はAIが最適な位置を判断します
        </p>
      </div>

      {/* アクションボタン */}
      <div className="flex items-center justify-between pt-4 border-t border-gray-200 dark:border-gray-700">
        <button
          onClick={onSkip}
          disabled={loading}
          className={cn(
            "inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg transition-colors",
            "text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700",
            loading && "opacity-50 cursor-not-allowed"
          )}
        >
          <SkipForward className="h-4 w-4" />
          スキップ
        </button>

        <button
          onClick={handleSubmit}
          disabled={loading}
          aria-busy={loading}
          className={cn(
            "inline-flex items-center gap-2 px-6 py-2 text-sm font-medium rounded-lg transition-colors",
            "bg-primary-600 text-white hover:bg-primary-700",
            loading && "opacity-50 cursor-not-allowed"
          )}
        >
          {loading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              分析中...
            </>
          ) : (
            <>
              <ArrowRight className="h-4 w-4" />
              次へ（位置分析）
            </>
          )}
        </button>
      </div>
    </div>
  );
}
