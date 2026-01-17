"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { StrategyInput, ChildTopicSuggestion } from "@/lib/types";
import { HelpButton } from "@/components/common/HelpButton";

interface Step3StrategyProps {
  data: StrategyInput;
  onChange: (data: Partial<StrategyInput>) => void;
  mainKeyword: string;
  businessDescription: string;
  targetAudience: string;
  errors: string[];
}

export function Step3Strategy({
  data,
  onChange,
  mainKeyword,
  businessDescription,
  targetAudience,
  errors,
}: Step3StrategyProps) {
  const [newTopic, setNewTopic] = useState("");
  const [isLoadingSuggestions, setIsLoadingSuggestions] = useState(false);
  const [topicSuggestions, setTopicSuggestions] = useState<ChildTopicSuggestion[]>([]);
  const [suggestionError, setSuggestionError] = useState<string | null>(null);

  const canSuggestTopics =
    mainKeyword.length >= 2 &&
    businessDescription.length >= 10 &&
    targetAudience.length >= 10;

  const addChildTopic = () => {
    if (!newTopic.trim()) return;

    const currentTopics = data.child_topics || [];
    onChange({ child_topics: [...currentTopics, newTopic.trim()] });
    setNewTopic("");
  };

  const removeChildTopic = (index: number) => {
    const currentTopics = data.child_topics || [];
    onChange({
      child_topics: currentTopics.filter((_, i) => i !== index),
    });
  };

  const handleSuggestTopics = async () => {
    if (!canSuggestTopics) return;

    setIsLoadingSuggestions(true);
    setSuggestionError(null);
    setTopicSuggestions([]);

    try {
      const response = await api.suggestions.childTopics({
        main_keyword: mainKeyword,
        business_description: businessDescription,
        target_audience: targetAudience,
      });
      setTopicSuggestions(response.suggestions);
    } catch (error) {
      setSuggestionError("子記事トピックの提案に失敗しました。再度お試しください。");
      console.error("Failed to get child topic suggestions:", error);
    } finally {
      setIsLoadingSuggestions(false);
    }
  };

  const handleSelectTopic = (suggestion: ChildTopicSuggestion) => {
    const currentTopics = data.child_topics || [];
    // Avoid duplicates
    if (!currentTopics.includes(suggestion.topic)) {
      onChange({ child_topics: [...currentTopics, suggestion.topic] });
    }
  };

  return (
    <div className="space-y-6">
      {/* Validation Errors */}
      {errors.length > 0 && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-md">
          <ul className="list-disc list-inside text-sm text-red-600">
            {errors.map((error, idx) => (
              <li key={idx}>{error}</li>
            ))}
          </ul>
        </div>
      )}

      {/* 記事のスタイル */}
      <div>
        <label className="block text-sm font-medium text-gray-700">
          <span className="inline-flex items-center gap-1">
            記事のスタイル <span className="text-red-500">*</span>
            <HelpButton helpKey="wizard.step3.type" size="sm" />
          </span>
        </label>
        <p className="mt-1 text-xs text-gray-500">
          どちらの記事スタイルで作成しますか？
        </p>

        <div className="mt-4 space-y-4">
          {/* 標準記事 */}
          <label
            className={`
              relative flex cursor-pointer rounded-lg border p-4
              ${
                data.article_style === "standalone"
                  ? "border-primary-500 bg-primary-50"
                  : "border-gray-200 hover:border-gray-300"
              }
            `}
          >
            <input
              type="radio"
              name="article_style"
              value="standalone"
              checked={data.article_style === "standalone"}
              onChange={() => onChange({ article_style: "standalone", child_topics: undefined })}
              className="sr-only"
            />
            <div className="flex flex-1">
              <div className="flex flex-col">
                <span className="block text-sm font-medium text-gray-900">
                  ①標準記事（スタンドアロン型）
                </span>
                <span className="mt-1 text-sm text-gray-500">
                  1記事で完結する記事。文字数制限を厳守。幅広いトピックをバランスよくカバー。
                </span>
              </div>
            </div>
            {data.article_style === "standalone" && (
              <div className="flex-shrink-0 ml-4">
                <svg
                  className="h-5 w-5 text-primary-600"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                >
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                    clipRule="evenodd"
                  />
                </svg>
              </div>
            )}
          </label>

          {/* トピッククラスター */}
          <label
            className={`
              relative flex cursor-pointer rounded-lg border p-4
              ${
                data.article_style === "topic_cluster"
                  ? "border-primary-500 bg-primary-50"
                  : "border-gray-200 hover:border-gray-300"
              }
            `}
          >
            <input
              type="radio"
              name="article_style"
              value="topic_cluster"
              checked={data.article_style === "topic_cluster"}
              onChange={() => onChange({ article_style: "topic_cluster" })}
              className="sr-only"
            />
            <div className="flex flex-1">
              <div className="flex flex-col">
                <span className="block text-sm font-medium text-gray-900">
                  ②トピッククラスター戦略（親記事+子記事）
                </span>
                <span className="mt-1 text-sm text-gray-500">
                  本記事を「親記事（ピラー記事）」とし、詳細は「子記事」に分割。
                  親記事は概要と子記事へのリンク中心。
                </span>
              </div>
            </div>
            {data.article_style === "topic_cluster" && (
              <div className="flex-shrink-0 ml-4">
                <svg
                  className="h-5 w-5 text-primary-600"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                >
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                    clipRule="evenodd"
                  />
                </svg>
              </div>
            )}
          </label>
        </div>
      </div>

      {/* 子記事トピック（トピッククラスター選択時のみ） */}
      {data.article_style === "topic_cluster" && (
        <div>
          <div className="flex items-center justify-between">
            <label className="block text-sm font-medium text-gray-700">
              <span className="inline-flex items-center gap-1">
                子記事のトピック <span className="text-red-500">*</span>
                <HelpButton helpKey="wizard.step3.cta" size="sm" />
              </span>
            </label>
            <button
              type="button"
              onClick={handleSuggestTopics}
              disabled={!canSuggestTopics || isLoadingSuggestions}
              className={`
                inline-flex items-center gap-1 px-3 py-1 text-xs font-medium rounded-md
                ${
                  canSuggestTopics && !isLoadingSuggestions
                    ? "bg-primary-50 text-primary-700 hover:bg-primary-100 border border-primary-200"
                    : "bg-gray-100 text-gray-400 cursor-not-allowed border border-gray-200"
                }
              `}
              title={!canSuggestTopics ? "キーワード、事業内容、ターゲット読者が必要です" : ""}
            >
              {isLoadingSuggestions ? (
                <>
                  <svg className="animate-spin h-3 w-3" viewBox="0 0 24 24">
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                      fill="none"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    />
                  </svg>
                  生成中...
                </>
              ) : (
                <>
                  <svg className="h-3 w-3" viewBox="0 0 20 20" fill="currentColor">
                    <path
                      fillRule="evenodd"
                      d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z"
                      clipRule="evenodd"
                    />
                  </svg>
                  AIで提案
                </>
              )}
            </button>
          </div>
          <p className="mt-1 text-xs text-gray-500">
            子記事として作成する予定のトピックを追加してください（3〜5個推奨）
          </p>

          {/* 既存のトピック一覧 */}
          {data.child_topics && data.child_topics.length > 0 && (
            <ul className="mt-3 space-y-2">
              {data.child_topics.map((topic, idx) => (
                <li
                  key={idx}
                  className="flex items-center justify-between px-3 py-2 bg-gray-50 rounded-md"
                >
                  <span className="text-sm text-gray-700">{topic}</span>
                  <button
                    type="button"
                    onClick={() => removeChildTopic(idx)}
                    className="text-gray-400 hover:text-red-500"
                  >
                    <svg
                      className="h-4 w-4"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M6 18L18 6M6 6l12 12"
                      />
                    </svg>
                  </button>
                </li>
              ))}
            </ul>
          )}

          {/* AIサジェスト候補 */}
          {topicSuggestions.length > 0 && (
            <div className="mt-3 p-3 bg-primary-50 rounded-lg border border-primary-200">
              <p className="text-xs font-medium text-primary-700 mb-2">
                AI提案（クリックで追加）
              </p>
              <div className="space-y-2">
                {topicSuggestions.map((suggestion, idx) => {
                  const isAdded = data.child_topics?.includes(suggestion.topic);
                  return (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => handleSelectTopic(suggestion)}
                      disabled={isAdded}
                      className={`
                        w-full text-left p-2 rounded border transition-colors
                        ${
                          isAdded
                            ? "bg-gray-100 border-gray-200 text-gray-400 cursor-not-allowed"
                            : "bg-white border-primary-100 hover:border-primary-300 hover:bg-primary-50"
                        }
                      `}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-900">{suggestion.topic}</span>
                        {isAdded && (
                          <span className="text-xs text-green-600">追加済み</span>
                        )}
                      </div>
                      <p className="text-xs text-gray-500 mt-1">
                        KW: {suggestion.target_keyword}
                      </p>
                      <p className="text-xs text-gray-400 mt-0.5">
                        {suggestion.rationale}
                      </p>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* エラー表示 */}
          {suggestionError && (
            <p className="mt-2 text-xs text-red-600">{suggestionError}</p>
          )}

          {/* 新規トピック追加 */}
          <div className="mt-3 flex gap-2">
            <input
              type="text"
              value={newTopic}
              onChange={(e) => setNewTopic(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  addChildTopic();
                }
              }}
              placeholder="例: 派遣社員向けOJTの具体的手法"
              className="flex-1 rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
            />
            <button
              type="button"
              onClick={addChildTopic}
              disabled={!newTopic.trim()}
              className={`
                inline-flex items-center px-3 py-2 text-sm font-medium rounded-md
                ${
                  !newTopic.trim()
                    ? "bg-gray-100 text-gray-400 cursor-not-allowed"
                    : "bg-primary-600 text-white hover:bg-primary-700"
                }
              `}
            >
              <svg
                className="h-4 w-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 4v16m8-8H4"
                />
              </svg>
            </button>
          </div>

          {/* サンプルトピック */}
          <div className="mt-3">
            <p className="text-xs text-gray-500">例:</p>
            <ul className="mt-1 text-xs text-gray-400 list-disc list-inside">
              <li>派遣社員向けOJTの具体的手法</li>
              <li>派遣社員向けeラーニングツール比較</li>
              <li>派遣社員の定着率を高めるフォローアップ方法</li>
              <li>新人派遣社員向けオリエンテーションプログラム</li>
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
