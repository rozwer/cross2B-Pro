"use client";

import { useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  Loader2,
  ImageIcon,
  Lightbulb,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { ImagePosition } from "@/lib/types";

interface ImageInstruction {
  index: number;
  instruction: string;
}

interface Phase11C_InstructionsProps {
  positions: ImagePosition[];
  onSubmit: (instructions: ImageInstruction[]) => void;
  onBack: () => void;
  loading?: boolean;
}

export function Phase11C_Instructions({
  positions,
  onSubmit,
  onBack,
  loading = false,
}: Phase11C_InstructionsProps) {
  const [instructions, setInstructions] = useState<string[]>(
    positions.map(() => "")
  );

  const handleInstructionChange = (index: number, value: string) => {
    setInstructions((prev) => {
      const next = [...prev];
      next[index] = value;
      return next;
    });
  };

  const handleSubmit = () => {
    const data: ImageInstruction[] = instructions.map((instruction, index) => ({
      index,
      instruction,
    }));
    onSubmit(data);
  };

  const allFilled = instructions.every((inst) => inst.trim().length > 0);

  return (
    <div className="space-y-6">
      {/* 説明 */}
      <div className="p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
        <div className="flex items-start gap-3">
          <Lightbulb className="h-5 w-5 text-purple-600 dark:text-purple-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm text-purple-800 dark:text-purple-200">
              各挿入位置に対して、どのような画像を生成するか指示してください。
              具体的な説明があるほど、より適切な画像が生成されます。
            </p>
          </div>
        </div>
      </div>

      {/* 指示入力 */}
      <div className="space-y-4 max-h-80 overflow-y-auto pr-2">
        {positions.map((position, index) => (
          <div
            key={index}
            className="p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg space-y-3"
          >
            <div className="flex items-center gap-2">
              <div className="flex items-center justify-center w-6 h-6 bg-purple-100 dark:bg-purple-900/30 rounded-full">
                <span className="text-xs font-bold text-purple-600 dark:text-purple-400">
                  {index + 1}
                </span>
              </div>
              <div className="flex-1 min-w-0">
                <span className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate block">
                  {position.section_title}
                </span>
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  {position.position === "before" ? "見出し前" : "見出し後"}
                </span>
              </div>
            </div>

            {/* 位置の説明 */}
            {position.description && (
              <p className="text-xs text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-700/50 p-2 rounded">
                {position.description}
              </p>
            )}

            {/* 指示入力 */}
            <div>
              <label className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-1 block">
                画像の指示
              </label>
              <textarea
                value={instructions[index]}
                onChange={(e) => handleInstructionChange(index, e.target.value)}
                placeholder="例：「モダンなオフィスでパソコンを使って作業しているビジネスパーソン」「シンプルな図解で3つのステップを表現」"
                rows={2}
                disabled={loading}
                className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent resize-none"
              />
            </div>

            {/* サジェスト */}
            <div className="flex flex-wrap gap-1">
              {getSuggestions(position).map((suggestion, i) => (
                <button
                  key={i}
                  onClick={() => handleInstructionChange(index, suggestion)}
                  disabled={loading}
                  className="text-xs px-2 py-0.5 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                >
                  {suggestion.slice(0, 20)}...
                </button>
              ))}
            </div>
          </div>
        ))}
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
          disabled={loading || !allFilled}
          className={cn(
            "inline-flex items-center gap-2 px-6 py-2 text-sm font-medium rounded-lg transition-colors",
            "bg-gradient-to-r from-purple-600 to-pink-600 text-white hover:from-purple-700 hover:to-pink-700",
            (loading || !allFilled) && "opacity-50 cursor-not-allowed"
          )}
        >
          {loading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              生成中...
            </>
          ) : (
            <>
              <ImageIcon className="h-4 w-4" />
              画像を生成
            </>
          )}
        </button>
      </div>

      {!allFilled && (
        <p className="text-xs text-center text-amber-600 dark:text-amber-400">
          全ての位置に指示を入力してください
        </p>
      )}
    </div>
  );
}

// 位置情報に基づいてサジェストを生成
function getSuggestions(position: ImagePosition): string[] {
  const suggestions: string[] = [];
  const title = position.section_title.toLowerCase();
  const desc = position.description?.toLowerCase() || "";

  // 導入・はじめにセクション
  if (title.includes("はじめ") || title.includes("導入") || position.section_index === 0) {
    suggestions.push("記事のテーマを象徴するアイキャッチ画像");
    suggestions.push("読者の興味を引く印象的なビジュアル");
  }

  // まとめセクション
  if (title.includes("まとめ") || title.includes("結論") || title.includes("おわり")) {
    suggestions.push("記事の要点を視覚的にまとめた図解");
    suggestions.push("次のアクションを促すイメージ");
  }

  // 方法・手順系
  if (title.includes("方法") || title.includes("手順") || title.includes("ステップ")) {
    suggestions.push("手順をわかりやすく示したフローチャート風の図解");
    suggestions.push("作業工程を示すイラスト");
  }

  // 比較系
  if (title.includes("比較") || title.includes("違い") || title.includes("メリット")) {
    suggestions.push("比較対象を並べて表示した図解");
    suggestions.push("メリット・デメリットを視覚化した画像");
  }

  // デフォルトサジェスト
  if (suggestions.length === 0) {
    suggestions.push("このセクションの内容を象徴するイメージ");
    suggestions.push("読者の理解を助けるシンプルな図解");
  }

  return suggestions.slice(0, 2);
}
