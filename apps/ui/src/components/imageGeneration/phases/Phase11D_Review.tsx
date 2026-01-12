"use client";

import { useState, useEffect } from "react";
import {
  ArrowLeft,
  ArrowRight,
  Loader2,
  Check,
  RefreshCw,
  AlertTriangle,
  Image as ImageIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { GeneratedImage } from "@/lib/types";

interface ImageReview {
  index: number;
  accepted: boolean;
  retry?: boolean;
  retryInstruction?: string;
}

interface Phase11D_ReviewProps {
  images: GeneratedImage[];
  warnings: string[];
  maxRetries?: number;
  onSubmit: (reviews: ImageReview[]) => void;
  onBack: () => void;
  loading?: boolean;
}

export function Phase11D_Review({
  images,
  warnings,
  maxRetries = 3,
  onSubmit,
  onBack,
  loading = false,
}: Phase11D_ReviewProps) {
  const [reviews, setReviews] = useState<Map<number, ImageReview>>(
    () =>
      new Map(
        images.map((img) => [
          img.index,
          { index: img.index, accepted: true },
        ])
      )
  );
  const [retryInputs, setRetryInputs] = useState<Map<number, string>>(
    () => new Map()
  );
  const [showRetryInput, setShowRetryInput] = useState<number | null>(null);

  // Reset state when images change (e.g., after retry)
  // This includes reviews, retryInputs, and showRetryInput to prevent stale data
  useEffect(() => {
    // Re-initialize reviews map with new images
    setReviews(
      new Map(
        images.map((img) => [
          img.index,
          { index: img.index, accepted: true },
        ])
      )
    );
    setRetryInputs(new Map());
    setShowRetryInput(null);
  }, [images]);

  const handleAccept = (index: number) => {
    setReviews((prev) => {
      const next = new Map(prev);
      next.set(index, { index, accepted: true });
      return next;
    });
    setShowRetryInput(null);
  };

  const handleReject = (index: number) => {
    setShowRetryInput(index);
  };

  const handleRetrySubmit = (index: number) => {
    const instruction = retryInputs.get(index) || "";
    setReviews((prev) => {
      const next = new Map(prev);
      next.set(index, {
        index,
        accepted: false,
        retry: true,
        retryInstruction: instruction,
      });
      return next;
    });
    setShowRetryInput(null);
  };

  const handleSubmit = () => {
    const reviewArray = Array.from(reviews.values());
    onSubmit(reviewArray);
  };

  const acceptedCount = Array.from(reviews.values()).filter((r) => r.accepted).length;
  const retryCount = Array.from(reviews.values()).filter((r) => r.retry).length;

  return (
    <div className="space-y-6">
      {/* 警告 */}
      {warnings.length > 0 && (
        <div className="p-4 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg">
          <div className="flex items-start gap-2">
            <AlertTriangle className="h-5 w-5 text-yellow-600 dark:text-yellow-400 flex-shrink-0" />
            <div>
              <p className="text-sm font-medium text-yellow-800 dark:text-yellow-200">
                注意
              </p>
              <ul className="mt-1 text-xs text-yellow-700 dark:text-yellow-300 list-disc list-inside">
                {warnings.map((warning, i) => (
                  <li key={i}>{warning}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* ステータス */}
      <div className="flex items-center justify-between text-sm">
        <span className="text-gray-600 dark:text-gray-400">
          {images.length}枚の画像を確認してください
        </span>
        <div className="flex items-center gap-4">
          <span className="text-green-600 dark:text-green-400">
            承認: {acceptedCount}枚
          </span>
          {retryCount > 0 && (
            <span className="text-yellow-600 dark:text-yellow-400">
              リトライ: {retryCount}枚
            </span>
          )}
        </div>
      </div>

      {/* 画像グリッド */}
      <div className="grid grid-cols-2 gap-4 max-h-96 overflow-y-auto">
        {images.map((image) => {
          const review = reviews.get(image.index);
          const canRetry = image.retry_count < maxRetries;

          return (
            <div
              key={image.index}
              className={cn(
                "relative border rounded-lg overflow-hidden transition-all",
                review?.accepted
                  ? "border-green-300 dark:border-green-600 ring-2 ring-green-200 dark:ring-green-800"
                  : review?.retry
                    ? "border-yellow-300 dark:border-yellow-600 ring-2 ring-yellow-200 dark:ring-yellow-800"
                    : "border-gray-200 dark:border-gray-700"
              )}
            >
              {/* 画像 */}
              <div className="aspect-video bg-gray-100 dark:bg-gray-800 relative">
                {image.image_base64 ? (
                  <img
                    src={`data:${image.mime_type};base64,${image.image_base64}`}
                    alt={image.alt_text}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="flex items-center justify-center h-full">
                    <ImageIcon className="h-12 w-12 text-gray-400" />
                  </div>
                )}

                {/* リトライ回数バッジ */}
                {image.retry_count > 0 && (
                  <div className="absolute top-2 left-2 px-2 py-0.5 bg-gray-900/70 text-white text-xs rounded">
                    リトライ {image.retry_count}/{maxRetries}
                  </div>
                )}

                {/* 承認/リトライバッジ */}
                {review?.accepted && (
                  <div className="absolute top-2 right-2 p-1 bg-green-500 rounded-full">
                    <Check className="h-4 w-4 text-white" />
                  </div>
                )}
                {review?.retry && (
                  <div className="absolute top-2 right-2 p-1 bg-yellow-500 rounded-full">
                    <RefreshCw className="h-4 w-4 text-white" />
                  </div>
                )}
              </div>

              {/* 情報とアクション */}
              <div className="p-3 space-y-2">
                <div className="text-xs text-gray-600 dark:text-gray-400 line-clamp-2 flex flex-wrap gap-1">
                  <span>{image.position.section_title}</span>
                  {image.article_number && (
                    <span className="px-1.5 py-0.5 bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-200 rounded">
                      記事{image.article_number}
                    </span>
                  )}
                  <span>- {image.user_instruction}</span>
                </div>

                {showRetryInput === image.index ? (
                  // リトライ指示入力
                  <div className="space-y-2">
                    <textarea
                      value={retryInputs.get(image.index) || ""}
                      onChange={(e) =>
                        setRetryInputs((prev) => {
                          const next = new Map(prev);
                          next.set(image.index, e.target.value);
                          return next;
                        })
                      }
                      placeholder="再生成の指示（例：もっと明るい雰囲気で）"
                      rows={2}
                      className="w-full px-2 py-1 text-xs border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                    />
                    <div className="flex gap-2">
                      <button
                        onClick={() => setShowRetryInput(null)}
                        className="flex-1 px-2 py-1 text-xs text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                      >
                        キャンセル
                      </button>
                      <button
                        onClick={() => handleRetrySubmit(image.index)}
                        className="flex-1 px-2 py-1 text-xs bg-yellow-500 text-white rounded hover:bg-yellow-600"
                      >
                        リトライ
                      </button>
                    </div>
                  </div>
                ) : (
                  // 通常のアクションボタン
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleAccept(image.index)}
                      disabled={loading}
                      className={cn(
                        "flex-1 inline-flex items-center justify-center gap-1 px-2 py-1 text-xs rounded transition-colors",
                        review?.accepted
                          ? "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300"
                          : "hover:bg-green-50 dark:hover:bg-green-900/20 text-gray-600 dark:text-gray-400"
                      )}
                    >
                      <Check className="h-3 w-3" />
                      承認
                    </button>
                    <button
                      onClick={() => handleReject(image.index)}
                      disabled={loading || !canRetry}
                      className={cn(
                        "flex-1 inline-flex items-center justify-center gap-1 px-2 py-1 text-xs rounded transition-colors",
                        review?.retry
                          ? "bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300"
                          : "hover:bg-yellow-50 dark:hover:bg-yellow-900/20 text-gray-600 dark:text-gray-400",
                        (!canRetry) && "opacity-50 cursor-not-allowed"
                      )}
                      title={!canRetry ? `リトライ上限（${maxRetries}回）に達しました` : undefined}
                    >
                      <RefreshCw className="h-3 w-3" />
                      リトライ
                    </button>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* アクションボタン */}
      <div className="flex items-center justify-between pt-4 border-t border-gray-200 dark:border-gray-700">
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
          onClick={handleSubmit}
          disabled={loading}
          className={cn(
            "inline-flex items-center gap-2 px-6 py-2 text-sm font-medium rounded-lg transition-colors",
            "bg-primary-600 text-white hover:bg-primary-700",
            loading && "opacity-50 cursor-not-allowed"
          )}
        >
          {loading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              処理中...
            </>
          ) : retryCount > 0 ? (
            <>
              <RefreshCw className="h-4 w-4" />
              リトライを実行
            </>
          ) : (
            <>
              <ArrowRight className="h-4 w-4" />
              次へ（プレビュー）
            </>
          )}
        </button>
      </div>
    </div>
  );
}
