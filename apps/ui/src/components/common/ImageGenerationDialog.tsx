"use client";

import { useState, useRef, useEffect } from "react";
import {
  X,
  ImageIcon,
  Loader2,
  SkipForward,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface ImageGenerationDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onGenerate: (config: ImageGenerationConfig) => void;
  onSkip: () => void;
  loading?: boolean;
}

export interface ImageGenerationConfig {
  enabled: true;
  imageCount: number;
  positionRequest: string;
}

export function ImageGenerationDialog({
  isOpen,
  onClose,
  onGenerate,
  onSkip,
  loading = false,
}: ImageGenerationDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [imageCount, setImageCount] = useState(3);
  const [positionRequest, setPositionRequest] = useState("");

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    if (isOpen) {
      dialog.showModal();
    } else {
      dialog.close();
    }
  }, [isOpen]);

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === dialogRef.current) {
      onClose();
    }
  };

  const handleGenerate = () => {
    onGenerate({
      enabled: true,
      imageCount,
      positionRequest,
    });
  };

  if (!isOpen) return null;

  return (
    <dialog
      ref={dialogRef}
      className="fixed inset-0 z-50 w-full max-w-lg p-0 bg-transparent backdrop:bg-black/50"
      onClick={handleBackdropClick}
    >
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl overflow-hidden">
        {/* ヘッダー */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">画像生成</h2>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              記事に画像を追加しますか？
            </p>
          </div>
          <button
            onClick={onClose}
            disabled={loading}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
          >
            <X className="h-5 w-5 text-gray-500 dark:text-gray-400" />
          </button>
        </div>

        {/* コンテンツ */}
        <div className="p-6 space-y-6">
          {/* 説明 */}
          <div className="p-4 bg-gray-50 dark:bg-gray-900/50 border border-gray-200 dark:border-gray-700 rounded-lg">
            <p className="text-sm text-gray-600 dark:text-gray-400">
              AIが記事内容を分析し、適切な位置に画像を自動生成して挿入します。
              画像の枚数や挿入位置の希望を指定できます。
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
                max={5}
                value={imageCount}
                onChange={(e) => setImageCount(Number(e.target.value))}
                className="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-primary-600"
                disabled={loading}
              />
              <span className="w-12 text-center text-lg font-semibold text-gray-900 dark:text-gray-100">
                {imageCount}枚
              </span>
            </div>
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
        </div>

        {/* フッター */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
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
            onClick={handleGenerate}
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
            ) : (
              <>
                <ImageIcon className="h-4 w-4" />
                画像を生成
              </>
            )}
          </button>
        </div>
      </div>
    </dialog>
  );
}
