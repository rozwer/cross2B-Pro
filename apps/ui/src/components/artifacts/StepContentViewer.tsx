"use client";

import { useMemo } from "react";
import {
  Target,
  Users,
  Lightbulb,
  Search,
  FileText,
  ListOrdered,
  CheckCircle2,
  AlertTriangle,
  Globe,
  ExternalLink,
  BookOpen,
  Sparkles,
  BarChart3,
  Hash,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { MarkdownViewer } from "./MarkdownViewer";

interface StepContentViewerProps {
  content: string;
  stepName: string;
}

interface ParsedContent {
  step?: string;
  keyword?: string;
  [key: string]: unknown;
}

export function StepContentViewer({ content, stepName }: StepContentViewerProps) {
  const parsed = useMemo(() => {
    try {
      return JSON.parse(content) as ParsedContent;
    } catch {
      return null;
    }
  }, [content]);

  if (!parsed) {
    return (
      <pre className="p-4 bg-gray-50 dark:bg-gray-900 rounded-lg text-xs overflow-auto whitespace-pre-wrap font-mono">
        {content}
      </pre>
    );
  }

  // 工程に応じたビューを選択
  const step = parsed.step || stepName;

  // デバッグ: ステップ判定ログ
  console.log("[StepContentViewer] stepName prop:", stepName);
  console.log("[StepContentViewer] parsed.step:", parsed.step);
  console.log("[StepContentViewer] final step:", step);
  console.log("[StepContentViewer] data keys:", Object.keys(parsed));

  switch (step) {
    case "step0":
      return <Step0Viewer data={parsed} />;
    case "step1":
      return <Step1Viewer data={parsed} />;
    case "step2":
      return <Step2Viewer data={parsed} />;
    case "step3a":
      return <Step3aViewer data={parsed} />;
    case "step3b":
      return <Step3bViewer data={parsed} />;
    case "step3c":
      return <Step3cViewer data={parsed} />;
    case "step4":
      return <Step4Viewer data={parsed} />;
    case "step5":
      return <Step5Viewer data={parsed} />;
    case "step6":
      return <Step6Viewer data={parsed} />;
    case "step6_5":
    case "step6.5":
      return <Step6_5Viewer data={parsed} />;
    case "step7a":
    case "step7b":
      return <Step7Viewer data={parsed} />;
    case "step11":
      return <Step11Viewer data={parsed} />;
    default:
      return <GenericViewer data={parsed} />;
  }
}

// 共通のセクションコンポーネント
function Section({
  icon: Icon,
  title,
  children,
  className,
}: {
  icon: React.ElementType;
  title: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800", className)}>
      <div className="flex items-center gap-2 px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
        <Icon className="h-4 w-4 text-primary-600 dark:text-primary-400" />
        <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">{title}</h3>
      </div>
      <div className="p-4">{children}</div>
    </div>
  );
}

// メタ情報バッジ
function MetaBadge({ icon: Icon, label, value }: { icon: React.ElementType; label: string; value: string | number }) {
  return (
    <div className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-gray-100 dark:bg-gray-700 rounded-md text-xs">
      <Icon className="h-3.5 w-3.5 text-gray-500 dark:text-gray-400" />
      <span className="text-gray-500 dark:text-gray-400">{label}:</span>
      <span className="font-medium text-gray-700 dark:text-gray-300">{value}</span>
    </div>
  );
}

// モデル・使用量バッジ（型安全）
function ModelUsageBadges({ model, usage }: { model: unknown; usage: unknown }) {
  const modelStr = typeof model === "string" ? model : null;
  const usageObj = usage && typeof usage === "object" ? (usage as { input_tokens?: number; output_tokens?: number }) : null;

  return (
    <div className="flex items-center gap-2">
      {modelStr && <MetaBadge icon={Sparkles} label="モデル" value={modelStr} />}
      {usageObj && (
        <MetaBadge icon={BarChart3} label="トークン" value={`${usageObj.input_tokens || 0} / ${usageObj.output_tokens || 0}`} />
      )}
    </div>
  );
}

// 残りのフィールドを表示する共通コンポーネント
function RemainingFields({ data, excludeKeys }: { data: ParsedContent; excludeKeys: string[] }) {
  // 常に除外するキー
  const alwaysExclude = ["step", "keyword", "model", "usage"];
  const allExcludeKeys = [...alwaysExclude, ...excludeKeys];

  const remainingEntries = Object.entries(data).filter(
    ([key]) => !allExcludeKeys.includes(key)
  );

  if (remainingEntries.length === 0) return null;

  return (
    <div className="mt-6 pt-4 border-t border-gray-200 dark:border-gray-700">
      <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-3">その他のデータ</h4>
      <div className="grid grid-cols-1 gap-3">
        {remainingEntries.map(([key, value]) => (
          <div
            key={key}
            className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800"
          >
            <div className="px-3 py-2 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
              <h5 className="text-xs font-medium text-gray-600 dark:text-gray-400">{key}</h5>
            </div>
            <div className="p-3">
              {typeof value === "string" ? (
                value.length > 500 ? (
                  <div className="prose prose-sm dark:prose-invert max-w-none">
                    <MarkdownViewer content={value} />
                  </div>
                ) : (
                  <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">{value}</p>
                )
              ) : Array.isArray(value) ? (
                <pre className="text-xs text-gray-600 dark:text-gray-400 overflow-auto max-h-48 whitespace-pre-wrap font-mono bg-gray-50 dark:bg-gray-900 p-2 rounded">
                  {JSON.stringify(value, null, 2)}
                </pre>
              ) : typeof value === "object" && value !== null ? (
                <pre className="text-xs text-gray-600 dark:text-gray-400 overflow-auto max-h-48 whitespace-pre-wrap font-mono bg-gray-50 dark:bg-gray-900 p-2 rounded">
                  {JSON.stringify(value, null, 2)}
                </pre>
              ) : (
                <span className="text-sm text-gray-700 dark:text-gray-300">{String(value)}</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// コードブロックからJSONを抽出
function extractJsonFromMarkdown(text: string): unknown | null {
  const match = text.match(/```json\n?([\s\S]*?)\n?```/);
  if (match) {
    try {
      return JSON.parse(match[1]);
    } catch {
      return null;
    }
  }
  return null;
}

// Step0: キーワード分析
function Step0Viewer({ data }: { data: ParsedContent }) {
  // 新形式: 直接フィールド (search_intent, difficulty_score, recommended_angles, target_audience)
  // 旧形式: analysis フィールド内のMarkdown/JSON
  const analysisRaw = typeof data.analysis === "string" ? data.analysis : null;
  const extractedAnalysis = analysisRaw ? extractJsonFromMarkdown(analysisRaw) : null;

  // 新形式のフィールドを優先、なければ旧形式から取得
  const searchIntent = typeof data.search_intent === "string" ? data.search_intent
    : (extractedAnalysis as Record<string, unknown>)?.search_intent as string | undefined;
  const difficulty = typeof data.difficulty_score === "number" ? (data.difficulty_score > 7 ? "high" : data.difficulty_score > 4 ? "medium" : "low")
    : (extractedAnalysis as Record<string, unknown>)?.difficulty as string | undefined;
  const targetAudience = typeof data.target_audience === "string" ? data.target_audience
    : (extractedAnalysis as Record<string, unknown>)?.target_audience as string | undefined;
  const recommendedAngles = Array.isArray(data.recommended_angles) ? data.recommended_angles as string[]
    : (extractedAnalysis as Record<string, unknown>)?.suggested_topics as string[] | undefined;
  const contentTypeSuggestion = typeof data.content_type_suggestion === "string" ? data.content_type_suggestion : null;

  const hasData = searchIntent || difficulty || targetAudience || (recommendedAngles && recommendedAngles.length > 0);

  return (
    <div className="space-y-4">
      {/* ヘッダー */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <Hash className="h-5 w-5 text-primary-600" />
          <span className="text-lg font-semibold text-gray-900 dark:text-gray-100">{String(data.keyword || "")}</span>
        </div>
        <ModelUsageBadges model={data.model} usage={data.usage} />
      </div>

      {hasData ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* 検索意図 */}
          {searchIntent && (
            <Section icon={Search} title="検索意図">
              <p className="text-sm text-gray-700 dark:text-gray-300">{searchIntent}</p>
            </Section>
          )}

          {/* 難易度 */}
          {difficulty && (
            <Section icon={Target} title="難易度">
              <div className="flex items-center gap-2">
                <span
                  className={cn(
                    "px-3 py-1 rounded-full text-sm font-medium",
                    difficulty === "high"
                      ? "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
                      : difficulty === "medium"
                        ? "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400"
                        : "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
                  )}
                >
                  {difficulty === "high" ? "高" : difficulty === "medium" ? "中" : "低"}
                </span>
                {typeof data.difficulty_score === "number" && (
                  <span className="text-xs text-gray-500">({data.difficulty_score}/10)</span>
                )}
              </div>
            </Section>
          )}

          {/* ターゲットオーディエンス */}
          {targetAudience && (
            <Section icon={Users} title="ターゲット" className="md:col-span-2">
              <p className="text-sm text-gray-700 dark:text-gray-300">{targetAudience}</p>
            </Section>
          )}

          {/* コンテンツタイプ提案 */}
          {contentTypeSuggestion && (
            <Section icon={FileText} title="推奨コンテンツタイプ" className="md:col-span-2">
              <p className="text-sm text-gray-700 dark:text-gray-300">{contentTypeSuggestion}</p>
            </Section>
          )}

          {/* 推奨トピック/アングル */}
          {recommendedAngles && recommendedAngles.length > 0 && (
            <Section icon={Lightbulb} title="推奨トピック・切り口" className="md:col-span-2">
              <ul className="space-y-2">
                {recommendedAngles.map((topic, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-gray-700 dark:text-gray-300">
                    <span className="flex-shrink-0 w-5 h-5 rounded-full bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400 flex items-center justify-center text-xs font-medium">
                      {i + 1}
                    </span>
                    {topic}
                  </li>
                ))}
              </ul>
            </Section>
          )}
        </div>
      ) : analysisRaw ? (
        // JSONが取り出せなかった場合はMarkdownとして表示
        <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6">
          <div className="prose prose-sm dark:prose-invert max-w-none">
            <MarkdownViewer content={analysisRaw} />
          </div>
        </div>
      ) : (
        <p className="text-sm text-gray-500 dark:text-gray-400">分析データがありません</p>
      )}

      {/* 残りのフィールド */}
      <RemainingFields
        data={data}
        excludeKeys={["analysis", "search_intent", "difficulty_score", "target_audience", "recommended_angles", "content_type_suggestion"]}
      />
    </div>
  );
}

// Step1: 競合情報収集
function Step1Viewer({ data }: { data: ParsedContent }) {
  // competitors または search_results フィールドをサポート
  const competitors = (data.competitors || data.search_results) as Array<{
    title?: string;
    url?: string;
    snippet?: string;
    content?: string;
    word_count?: number;
  }> | undefined;

  const keyword = typeof data.keyword === "string" ? data.keyword : null;
  const serpQuery = typeof data.serp_query === "string" ? data.serp_query : null;

  return (
    <div className="space-y-4">
      {/* ヘッダー情報 */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <Search className="h-5 w-5 text-primary-600" />
          <span className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            競合分析結果 ({competitors?.length || 0}件)
          </span>
        </div>
        <div className="flex items-center gap-2">
          {typeof data.model === "string" && <MetaBadge icon={Sparkles} label="モデル" value={data.model} />}
        </div>
      </div>

      {/* キーワード情報 */}
      {(keyword || serpQuery) && (
        <div className="flex flex-wrap gap-2 p-3 rounded-lg bg-gray-50 dark:bg-gray-800/50">
          {keyword && (
            <div className="flex items-center gap-1.5 text-sm">
              <Hash className="h-4 w-4 text-gray-500" />
              <span className="text-gray-600 dark:text-gray-400">キーワード:</span>
              <span className="font-medium text-gray-900 dark:text-gray-100">{keyword}</span>
            </div>
          )}
          {serpQuery && serpQuery !== keyword && (
            <div className="flex items-center gap-1.5 text-sm">
              <Search className="h-4 w-4 text-gray-500" />
              <span className="text-gray-600 dark:text-gray-400">検索クエリ:</span>
              <span className="font-medium text-gray-900 dark:text-gray-100">{serpQuery}</span>
            </div>
          )}
        </div>
      )}

      {competitors && competitors.length > 0 ? (
        <div className="space-y-3">
          {competitors.map((result, i) => (
            <div
              key={i}
              className="p-4 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:border-primary-300 dark:hover:border-primary-600 transition-colors"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                    {result.title || "タイトルなし"}
                  </h4>
                  {result.url && (
                    <a
                      href={result.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-primary-600 dark:text-primary-400 hover:underline flex items-center gap-1 mt-1"
                    >
                      <Globe className="h-3 w-3" />
                      {(() => {
                        try {
                          return new URL(result.url).hostname;
                        } catch {
                          return result.url;
                        }
                      })()}
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  )}
                </div>
                {result.word_count && (
                  <span className="flex-shrink-0 px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded text-xs text-gray-600 dark:text-gray-400">
                    {result.word_count.toLocaleString()} 文字
                  </span>
                )}
              </div>
              {(result.snippet || result.content) && (
                <p className="mt-2 text-xs text-gray-600 dark:text-gray-400 line-clamp-3">
                  {result.snippet || (typeof result.content === "string" ? result.content.substring(0, 300) : "")}
                </p>
              )}
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm text-gray-500 dark:text-gray-400">競合サイトが見つかりません</p>
      )}

      {/* 残りのフィールド */}
      <RemainingFields
        data={data}
        excludeKeys={["competitors", "search_results", "serp_query"]}
      />
    </div>
  );
}

// Step2: 情報検証・バリデーション
function Step2Viewer({ data }: { data: ParsedContent }) {
  // validated_data フィールドをサポート
  const validatedData = (data.validated_data) as Array<{
    title?: string;
    url?: string;
    content?: string;
    word_count?: number;
    headings?: string[];
    fetched_at?: string;
    content_hash?: string;
    quality_score?: number;
    auto_fixes_applied?: string[];
  }> | undefined;

  // validation_summary のパース
  const validationSummary = data.validation_summary as {
    total_records?: number;
    valid_records?: number;
    rejected_records?: number;
    auto_fixed_count?: number;
    error_rate?: number;
  } | undefined;

  const isValid = typeof data.is_valid === "boolean" ? data.is_valid : null;
  const keyword = typeof data.keyword === "string" ? data.keyword : null;

  return (
    <div className="space-y-4">
      {/* ヘッダー情報 */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <CheckCircle2 className="h-5 w-5 text-primary-600" />
          <span className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            情報検証結果 ({validatedData?.length || 0}件)
          </span>
        </div>
        <div className="flex items-center gap-2">
          {isValid !== null && (
            <span className={cn(
              "px-2.5 py-1 rounded-full text-xs font-medium",
              isValid
                ? "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300"
                : "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300"
            )}>
              {isValid ? "✓ 有効" : "✗ 無効"}
            </span>
          )}
          {typeof data.model === "string" && <MetaBadge icon={Sparkles} label="モデル" value={data.model} />}
        </div>
      </div>

      {/* キーワード情報 */}
      {keyword && (
        <div className="flex flex-wrap gap-2 p-3 rounded-lg bg-gray-50 dark:bg-gray-800/50">
          <div className="flex items-center gap-1.5 text-sm">
            <Hash className="h-4 w-4 text-gray-500" />
            <span className="text-gray-600 dark:text-gray-400">キーワード:</span>
            <span className="font-medium text-gray-900 dark:text-gray-100">{keyword}</span>
          </div>
        </div>
      )}

      {/* バリデーションサマリー */}
      {validationSummary && (
        <Section icon={BarChart3} title="検証サマリー">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg text-center">
              <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                {validationSummary.total_records ?? "-"}
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400">総件数</div>
            </div>
            <div className="p-3 bg-green-50 dark:bg-green-900/20 rounded-lg text-center">
              <div className="text-2xl font-bold text-green-700 dark:text-green-300">
                {validationSummary.valid_records ?? "-"}
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400">有効</div>
            </div>
            <div className="p-3 bg-red-50 dark:bg-red-900/20 rounded-lg text-center">
              <div className="text-2xl font-bold text-red-700 dark:text-red-300">
                {validationSummary.rejected_records ?? "-"}
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400">無効</div>
            </div>
            <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg text-center">
              <div className="text-2xl font-bold text-blue-700 dark:text-blue-300">
                {validationSummary.auto_fixed_count ?? "-"}
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400">自動修正</div>
            </div>
            <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg text-center">
              <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                {validationSummary.error_rate !== undefined ? `${(validationSummary.error_rate * 100).toFixed(1)}%` : "-"}
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400">エラー率</div>
            </div>
          </div>
        </Section>
      )}

      {/* 検証済みデータ一覧 */}
      {validatedData && validatedData.length > 0 ? (
        <Section icon={FileText} title={`検証済みデータ (${validatedData.length}件)`}>
          <div className="space-y-3 max-h-[500px] overflow-y-auto">
            {validatedData.map((item, i) => (
              <div
                key={i}
                className="p-4 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:border-primary-300 dark:hover:border-primary-600 transition-colors"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 line-clamp-2">
                      {item.title || "タイトルなし"}
                    </h4>
                    {item.url && (
                      <a
                        href={item.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs text-primary-600 dark:text-primary-400 hover:underline flex items-center gap-1 mt-1"
                      >
                        <Globe className="h-3 w-3" />
                        {(() => {
                          try {
                            return new URL(item.url).hostname;
                          } catch {
                            return item.url;
                          }
                        })()}
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    )}
                  </div>
                  <div className="flex flex-col items-end gap-1">
                    {item.word_count && (
                      <span className="px-2 py-0.5 bg-gray-100 dark:bg-gray-700 rounded text-xs text-gray-600 dark:text-gray-400">
                        {item.word_count.toLocaleString()} 文字
                      </span>
                    )}
                    {item.quality_score !== undefined && (
                      <span className={cn(
                        "px-2 py-0.5 rounded text-xs",
                        item.quality_score >= 0.8
                          ? "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300"
                          : item.quality_score >= 0.5
                            ? "bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300"
                            : "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300"
                      )}>
                        品質: {(item.quality_score * 100).toFixed(0)}%
                      </span>
                    )}
                  </div>
                </div>

                {/* 自動修正情報 */}
                {item.auto_fixes_applied && item.auto_fixes_applied.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {item.auto_fixes_applied.map((fix, j) => (
                      <span
                        key={j}
                        className="px-1.5 py-0.5 bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 rounded text-xs"
                      >
                        🔧 {fix}
                      </span>
                    ))}
                  </div>
                )}

                {/* コンテンツプレビュー */}
                {item.content && (
                  <p className="mt-2 text-xs text-gray-600 dark:text-gray-400 line-clamp-3">
                    {typeof item.content === "string" ? item.content.substring(0, 300) : ""}...
                  </p>
                )}

                {/* 取得日時 */}
                {item.fetched_at && (
                  <div className="mt-2 text-xs text-gray-400 dark:text-gray-500">
                    取得: {new Date(item.fetched_at).toLocaleString("ja-JP")}
                  </div>
                )}
              </div>
            ))}
          </div>
        </Section>
      ) : (
        <p className="text-sm text-gray-500 dark:text-gray-400">検証済みデータがありません</p>
      )}

      {/* 残りのフィールド */}
      <RemainingFields
        data={data}
        excludeKeys={["validated_data", "validation_summary", "is_valid"]}
      />
    </div>
  );
}

// Step3a: クエリ分析
function Step3aViewer({ data }: { data: ParsedContent }) {
  const queryAnalysisRaw = typeof data.query_analysis === "string" ? data.query_analysis : null;
  const analysis = queryAnalysisRaw ? extractJsonFromMarkdown(queryAnalysisRaw) : data.query_analysis;
  const analysisData = analysis as {
    query_type?: string;
    user_intent?: string;
    related_queries?: string[];
    content_format_suggestion?: string;
  } | null;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <Search className="h-5 w-5 text-primary-600" />
          <span className="text-lg font-semibold text-gray-900 dark:text-gray-100">クエリ分析</span>
        </div>
        <ModelUsageBadges model={data.model} usage={data.usage} />
      </div>

      {analysisData && (analysisData.query_type || analysisData.user_intent || analysisData.related_queries || analysisData.content_format_suggestion) ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {analysisData.query_type && (
            <Section icon={Target} title="クエリタイプ">
              <span className="px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
                {analysisData.query_type}
              </span>
            </Section>
          )}

          {analysisData.user_intent && (
            <Section icon={Users} title="ユーザー意図">
              <p className="text-sm text-gray-700 dark:text-gray-300">{analysisData.user_intent}</p>
            </Section>
          )}

          {analysisData.related_queries && analysisData.related_queries.length > 0 && (
            <Section icon={Search} title="関連クエリ" className="md:col-span-2">
              <div className="flex flex-wrap gap-2">
                {analysisData.related_queries.map((query, i) => (
                  <span
                    key={i}
                    className="px-3 py-1.5 rounded-full text-xs bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300"
                  >
                    {query}
                  </span>
                ))}
              </div>
            </Section>
          )}

          {analysisData.content_format_suggestion && (
            <Section icon={FileText} title="推奨コンテンツ形式" className="md:col-span-2">
              <p className="text-sm text-gray-700 dark:text-gray-300">{analysisData.content_format_suggestion}</p>
            </Section>
          )}
        </div>
      ) : queryAnalysisRaw ? (
        // JSONが取り出せなかった場合はMarkdownとして表示
        <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6">
          <div className="prose prose-sm dark:prose-invert max-w-none">
            <MarkdownViewer content={queryAnalysisRaw} />
          </div>
        </div>
      ) : (
        <p className="text-sm text-gray-500 dark:text-gray-400">クエリ分析データがありません</p>
      )}

      {/* 残りのフィールド */}
      <RemainingFields
        data={data}
        excludeKeys={["query_analysis"]}
      />
    </div>
  );
}

// Step3b メトリクス・品質セクション
function Step3bMetricsSection({ metrics, quality }: { metrics: unknown; quality: unknown }) {
  const metricsObj = metrics && typeof metrics === "object" ? metrics as { char_count?: number; word_count?: number } : null;
  const qualityObj = quality && typeof quality === "object" ? quality as { attempts?: number; warnings?: string[]; issues?: string[] } : null;

  if (!metricsObj && !qualityObj) return null;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {metricsObj && (
        <Section icon={BarChart3} title="メトリクス">
          <div className="grid grid-cols-2 gap-2">
            {metricsObj.char_count !== undefined && (
              <div className="p-2 bg-gray-50 dark:bg-gray-800/50 rounded text-center">
                <div className="text-lg font-bold text-gray-900 dark:text-gray-100">
                  {metricsObj.char_count.toLocaleString()}
                </div>
                <div className="text-xs text-gray-500">文字数</div>
              </div>
            )}
            {metricsObj.word_count !== undefined && (
              <div className="p-2 bg-gray-50 dark:bg-gray-800/50 rounded text-center">
                <div className="text-lg font-bold text-gray-900 dark:text-gray-100">
                  {metricsObj.word_count.toLocaleString()}
                </div>
                <div className="text-xs text-gray-500">単語数</div>
              </div>
            )}
          </div>
        </Section>
      )}
      {qualityObj && (
        <Section icon={CheckCircle2} title="品質情報">
          <div className="space-y-2">
            {qualityObj.attempts !== undefined && (
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-600 dark:text-gray-400">試行回数</span>
                <span className="font-medium text-gray-900 dark:text-gray-100">
                  {qualityObj.attempts}
                </span>
              </div>
            )}
            {Array.isArray(qualityObj.warnings) && qualityObj.warnings.length > 0 && (
              <div>
                <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">警告</div>
                <div className="space-y-1">
                  {qualityObj.warnings.map((w, i) => (
                    <div key={i} className="text-xs text-amber-600 dark:text-amber-400 flex items-center gap-1">
                      <AlertTriangle className="h-3 w-3" />
                      {w}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </Section>
      )}
    </div>
  );
}

// Step3b: 共起語分析
function Step3bViewer({ data }: { data: ParsedContent }) {
  // デバッグ: 入力データの確認
  console.log("[Step3bViewer] === START ===");
  console.log("[Step3bViewer] data keys:", Object.keys(data));
  console.log("[Step3bViewer] data.parsed_data:", data.parsed_data);
  console.log("[Step3bViewer] data.cooccurrence_analysis type:", typeof data.cooccurrence_analysis);

  const cooccurrenceAnalysis = typeof data.cooccurrence_analysis === "string" ? data.cooccurrence_analysis : null;
  const competitorCount = typeof data.competitor_count === "number" ? data.competitor_count : null;

  // 新形式: parsed_data に構造化データ
  // cooccurrence_keywords は string[] またはカテゴリ別オブジェクト
  const rawParsedData = data.parsed_data as {
    cooccurrence_keywords?: string[] | Record<string, string[]>;
    semantic_clusters?: Array<{ cluster: string; keywords: string[] }>;
    content_gaps?: string[];
  } | undefined;

  console.log("[Step3bViewer] rawParsedData:", rawParsedData);

  // cooccurrence_keywords をフラットな配列に変換
  const normalizeKeywords = (keywords: string[] | Record<string, string[]> | undefined): string[] => {
    if (!keywords) return [];
    if (Array.isArray(keywords)) return keywords;
    // オブジェクト形式の場合、全てのカテゴリからキーワードを集約
    const allKeywords: string[] = [];
    for (const category of Object.values(keywords)) {
      if (Array.isArray(category)) {
        for (const kw of category) {
          // "- " プレフィックスを除去
          const cleaned = typeof kw === "string" ? kw.replace(/^-\s*/, "") : kw;
          allKeywords.push(cleaned);
        }
      }
    }
    return allKeywords;
  };

  // カテゴリ別のキーワードを取得（表示用）
  const getKeywordCategories = (keywords: string[] | Record<string, string[]> | undefined): Array<{ category: string; keywords: string[] }> => {
    if (!keywords || Array.isArray(keywords)) return [];
    return Object.entries(keywords).map(([category, kws]) => ({
      category,
      keywords: Array.isArray(kws) ? kws.map(kw => typeof kw === "string" ? kw.replace(/^-\s*/, "") : kw) : [],
    }));
  };

  const parsedData = rawParsedData ? {
    cooccurrence_keywords: normalizeKeywords(rawParsedData.cooccurrence_keywords),
    keyword_categories: getKeywordCategories(rawParsedData.cooccurrence_keywords),
    semantic_clusters: rawParsedData.semantic_clusters,
    content_gaps: rawParsedData.content_gaps,
  } : undefined;

  // デバッグ: 処理後のデータ確認
  console.log("[Step3bViewer] parsedData:", parsedData);
  console.log("[Step3bViewer] cooccurrence_keywords length:", parsedData?.cooccurrence_keywords?.length);
  console.log("[Step3bViewer] keyword_categories length:", parsedData?.keyword_categories?.length);
  console.log("[Step3bViewer] semantic_clusters length:", parsedData?.semantic_clusters?.length);
  console.log("[Step3bViewer] content_gaps length:", parsedData?.content_gaps?.length);

  const hasStructuredData = parsedData && (
    (parsedData.cooccurrence_keywords && parsedData.cooccurrence_keywords.length > 0) ||
    (parsedData.keyword_categories && parsedData.keyword_categories.length > 0) ||
    (parsedData.semantic_clusters && parsedData.semantic_clusters.length > 0) ||
    (parsedData.content_gaps && parsedData.content_gaps.length > 0)
  );

  console.log("[Step3bViewer] hasStructuredData:", hasStructuredData);
  console.log("[Step3bViewer] cooccurrenceAnalysis:", cooccurrenceAnalysis ? "exists" : "null");
  console.log("[Step3bViewer] === END ===");

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <Search className="h-5 w-5 text-primary-600" />
          <span className="text-lg font-semibold text-gray-900 dark:text-gray-100">共起語分析</span>
        </div>
        <div className="flex items-center gap-2">
          {competitorCount !== null && <MetaBadge icon={Users} label="競合数" value={competitorCount} />}
          <ModelUsageBadges model={data.model} usage={data.usage} />
        </div>
      </div>

      {hasStructuredData ? (
        <div className="space-y-4">
          {/* カテゴリ別キーワード（オブジェクト形式の場合） */}
          {parsedData.keyword_categories && parsedData.keyword_categories.length > 0 ? (
            <Section icon={Hash} title="共起・関連キーワード">
              <div className="space-y-4">
                {parsedData.keyword_categories.map((cat, i) => (
                  <div key={i} className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                    <h5 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">{cat.category}</h5>
                    <div className="flex flex-wrap gap-2">
                      {cat.keywords.map((kw, j) => (
                        <span key={j} className="px-2.5 py-1 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 rounded-full text-xs">
                          {kw}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </Section>
          ) : parsedData.cooccurrence_keywords && parsedData.cooccurrence_keywords.length > 0 ? (
            /* フラット配列形式の場合 */
            <Section icon={Hash} title="共起キーワード">
              <div className="flex flex-wrap gap-2">
                {parsedData.cooccurrence_keywords.map((kw, i) => (
                  <span key={i} className="px-2.5 py-1 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 rounded-full text-xs">
                    {kw}
                  </span>
                ))}
              </div>
            </Section>
          ) : null}

          {/* セマンティッククラスター */}
          {parsedData.semantic_clusters && parsedData.semantic_clusters.length > 0 && (
            <Section icon={Target} title="セマンティッククラスター">
              <div className="space-y-3">
                {parsedData.semantic_clusters.map((cluster, i) => (
                  <div key={i} className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                    <h5 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">{cluster.cluster}</h5>
                    <div className="flex flex-wrap gap-1.5">
                      {cluster.keywords.map((kw, j) => (
                        <span key={j} className="px-2 py-0.5 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded text-xs">
                          {kw}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </Section>
          )}

          {/* コンテンツギャップ */}
          {parsedData.content_gaps && parsedData.content_gaps.length > 0 && (
            <Section icon={Lightbulb} title="コンテンツギャップ">
              <ul className="space-y-2">
                {parsedData.content_gaps.map((gap, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-gray-700 dark:text-gray-300">
                    <CheckCircle2 className="h-4 w-4 text-green-500 flex-shrink-0 mt-0.5" />
                    {gap}
                  </li>
                ))}
              </ul>
            </Section>
          )}
        </div>
      ) : cooccurrenceAnalysis ? (
        <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6">
          <div className="prose prose-sm dark:prose-invert max-w-none">
            <MarkdownViewer content={cooccurrenceAnalysis} />
          </div>
        </div>
      ) : (
        <p className="text-sm text-gray-500 dark:text-gray-400">共起語分析データがありません</p>
      )}

      {/* メトリクスと品質情報 */}
      <Step3bMetricsSection metrics={data.metrics} quality={data.quality} />

      {/* 残りのフィールド */}
      <RemainingFields
        data={data}
        excludeKeys={["cooccurrence_analysis", "parsed_data", "competitor_count", "format_detected", "metrics", "quality"]}
      />
    </div>
  );
}

// Step3c: 競合分析（構造分析）
function Step3cViewer({ data }: { data: ParsedContent }) {
  const competitorAnalysisRaw = typeof data.competitor_analysis === "string" ? data.competitor_analysis : null;
  const competitorCount = typeof data.competitor_count === "number" ? data.competitor_count : null;
  const qualityCompetitorCount = typeof data.quality_competitor_count === "number" ? data.quality_competitor_count : null;
  const formatDetected = typeof data.format_detected === "string" ? data.format_detected : null;

  // 品質情報
  const quality = data.quality as {
    attempts?: number;
    issues?: string[];
    details?: {
      output_size?: number;
      output_tokens?: number;
      finish_reason?: string;
    };
  } | undefined;

  // メトリクス情報（出力サイズ確認用）
  const metrics = data.metrics as {
    output_size?: number;
    output_tokens?: number;
    input_tokens?: number;
  } | undefined;

  // 競合データの型定義
  type CompetitorData = {
    url?: string;
    strengths?: string[];
    weaknesses?: string[];
    recommendations?: string[];
  };

  // parsed_data から構造化データを取得（存在する場合）
  const parsedDataRaw = data.parsed_data;
  const parsedData: { competitor_analysis?: CompetitorData[] } | null =
    parsedDataRaw && typeof parsedDataRaw === "object" && !Array.isArray(parsedDataRaw)
      ? (parsedDataRaw as { competitor_analysis?: CompetitorData[] })
      : null;

  // competitor_analysis からJSONを抽出して解析
  const extractedAnalysisRaw = competitorAnalysisRaw ? extractJsonFromMarkdown(competitorAnalysisRaw) : null;
  const analysisFromExtracted: { competitor_analysis?: CompetitorData[] } | null =
    extractedAnalysisRaw && typeof extractedAnalysisRaw === "object" && !Array.isArray(extractedAnalysisRaw)
      ? (extractedAnalysisRaw as { competitor_analysis?: CompetitorData[] })
      : null;

  // 構造化された競合分析データ（parsed_data優先、次にextracted）
  const getStructuredAnalysis = (): CompetitorData[] | null => {
    if (parsedData?.competitor_analysis && Array.isArray(parsedData.competitor_analysis)) {
      return parsedData.competitor_analysis;
    }
    if (analysisFromExtracted?.competitor_analysis && Array.isArray(analysisFromExtracted.competitor_analysis)) {
      return analysisFromExtracted.competitor_analysis;
    }
    return null;
  };
  const structuredAnalysis = getStructuredAnalysis();
  const hasStructuredAnalysis = structuredAnalysis !== null && structuredAnalysis.length > 0;

  // 品質問題のラベルマッピング
  const issueLabels: Record<string, string> = {
    no_recommendations: "推奨事項なし",
    incomplete_json: "JSONが不完全",
    parse_error: "パースエラー",
    truncated: "出力が切れている",
    output_too_small: "出力サイズ不足",
    appears_truncated: "出力が途中で切れている可能性",
  };

  // 出力切れ関連のissueかどうか
  const hasTruncationIssue = quality?.issues?.some(
    issue => ["truncated", "output_too_small", "appears_truncated", "incomplete_json"].includes(issue)
  );

  // 出力サイズ情報を取得（quality.details または metrics から）
  const outputSize = quality?.details?.output_size ?? metrics?.output_size;
  const outputTokens = quality?.details?.output_tokens ?? metrics?.output_tokens ??
    (data.usage as { output_tokens?: number } | undefined)?.output_tokens;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <Target className="h-5 w-5 text-primary-600" />
          <span className="text-lg font-semibold text-gray-900 dark:text-gray-100">構造分析</span>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          {competitorCount !== null && <MetaBadge icon={Users} label="競合数" value={competitorCount} />}
          {qualityCompetitorCount !== null && qualityCompetitorCount !== competitorCount && (
            <MetaBadge icon={CheckCircle2} label="品質競合" value={qualityCompetitorCount} />
          )}
          <ModelUsageBadges model={data.model} usage={data.usage} />
        </div>
      </div>

      {/* 品質警告 */}
      {quality?.issues && Array.isArray(quality.issues) && quality.issues.length > 0 && (
        <div className="p-3 rounded-lg bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800">
          <div className="flex items-start gap-2">
            <AlertTriangle className="h-4 w-4 text-yellow-600 dark:text-yellow-400 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="text-sm font-medium text-yellow-800 dark:text-yellow-200">品質に関する注意</p>
              <div className="flex flex-wrap gap-1.5 mt-1">
                {(quality.issues as string[]).map((issue: string, i: number) => {
                  const label: string = issueLabels[issue] ?? issue;
                  return (
                    <span
                      key={i}
                      className="px-2 py-0.5 bg-yellow-100 dark:bg-yellow-900/40 text-yellow-700 dark:text-yellow-300 rounded text-xs"
                    >
                      {label}
                    </span>
                  );
                })}
              </div>
              {/* 出力切れ関連の詳細情報 */}
              {hasTruncationIssue && (
                <div className="mt-2 p-2 bg-yellow-100/50 dark:bg-yellow-900/30 rounded text-xs space-y-1">
                  {outputSize !== undefined && (
                    <div className="flex items-center gap-2">
                      <span className="text-yellow-700 dark:text-yellow-300">出力サイズ:</span>
                      <span className="font-mono text-yellow-800 dark:text-yellow-200">
                        {outputSize.toLocaleString()} バイト
                        {outputSize < 3000 && (
                          <span className="ml-1 text-red-600 dark:text-red-400">(期待値: 3,000+ バイト)</span>
                        )}
                      </span>
                    </div>
                  )}
                  {outputTokens !== undefined && (
                    <div className="flex items-center gap-2">
                      <span className="text-yellow-700 dark:text-yellow-300">出力トークン:</span>
                      <span className="font-mono text-yellow-800 dark:text-yellow-200">
                        {outputTokens.toLocaleString()} トークン
                        {outputTokens < 500 && (
                          <span className="ml-1 text-red-600 dark:text-red-400">(期待値: 500+ トークン)</span>
                        )}
                      </span>
                    </div>
                  )}
                  <p className="text-yellow-600 dark:text-yellow-400 mt-1">
                    この工程の再実行をお勧めします。
                  </p>
                </div>
              )}
              {formatDetected === "unknown" && !hasTruncationIssue && (
                <p className="text-xs text-yellow-600 dark:text-yellow-400 mt-1">
                  出力形式が認識できませんでした。LLMの出力が途中で切れている可能性があります。
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* 構造化された競合分析 */}
      {hasStructuredAnalysis && structuredAnalysis && (
        <div className="space-y-3">
          {structuredAnalysis.map((competitor, i) => (
            <div
              key={i}
              className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 overflow-hidden"
            >
              {/* URL ヘッダー */}
              {competitor.url && (
                <div className="px-4 py-2 bg-gray-50 dark:bg-gray-800/50 border-b border-gray-200 dark:border-gray-700">
                  <a
                    href={competitor.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-primary-600 dark:text-primary-400 hover:underline flex items-center gap-1"
                  >
                    <Globe className="h-3.5 w-3.5" />
                    {(() => {
                      try {
                        return new URL(competitor.url).hostname;
                      } catch {
                        return competitor.url;
                      }
                    })()}
                    <ExternalLink className="h-3 w-3" />
                  </a>
                </div>
              )}

              <div className="p-4 grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* 強み */}
                {competitor.strengths && competitor.strengths.length > 0 && (
                  <div>
                    <h5 className="text-xs font-medium text-green-700 dark:text-green-400 mb-2 flex items-center gap-1">
                      <CheckCircle2 className="h-3.5 w-3.5" />
                      強み
                    </h5>
                    <ul className="space-y-1">
                      {competitor.strengths.map((s, j) => (
                        <li key={j} className="text-xs text-gray-600 dark:text-gray-400 flex items-start gap-1.5">
                          <span className="text-green-500 mt-0.5">•</span>
                          {s}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* 弱み */}
                {competitor.weaknesses && competitor.weaknesses.length > 0 && (
                  <div>
                    <h5 className="text-xs font-medium text-red-700 dark:text-red-400 mb-2 flex items-center gap-1">
                      <AlertTriangle className="h-3.5 w-3.5" />
                      弱み
                    </h5>
                    <ul className="space-y-1">
                      {competitor.weaknesses.map((w, j) => (
                        <li key={j} className="text-xs text-gray-600 dark:text-gray-400 flex items-start gap-1.5">
                          <span className="text-red-500 mt-0.5">•</span>
                          {w}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* 推奨事項 */}
                {competitor.recommendations && competitor.recommendations.length > 0 && (
                  <div>
                    <h5 className="text-xs font-medium text-blue-700 dark:text-blue-400 mb-2 flex items-center gap-1">
                      <Lightbulb className="h-3.5 w-3.5" />
                      推奨
                    </h5>
                    <ul className="space-y-1">
                      {competitor.recommendations.map((r, j) => (
                        <li key={j} className="text-xs text-gray-600 dark:text-gray-400 flex items-start gap-1.5">
                          <span className="text-blue-500 mt-0.5">•</span>
                          {r}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 構造化できない場合は生データを表示 */}
      {!hasStructuredAnalysis && competitorAnalysisRaw && (
        <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6">
          <div className="prose prose-sm dark:prose-invert max-w-none">
            <MarkdownViewer content={competitorAnalysisRaw} />
          </div>
        </div>
      )}

      {/* データがない場合 */}
      {!hasStructuredAnalysis && !competitorAnalysisRaw && (
        <p className="text-sm text-gray-500 dark:text-gray-400">競合分析データがありません</p>
      )}

      {/* メトリクス情報 */}
      {data.metrics != null && typeof data.metrics === "object" && (
        <div className="flex items-center gap-3 p-3 rounded-lg bg-gray-50 dark:bg-gray-800/50">
          <span className="text-xs text-gray-500 dark:text-gray-400">メトリクス:</span>
          {(data.metrics as { char_count?: number }).char_count !== undefined && (
            <MetaBadge icon={Hash} label="文字数" value={(data.metrics as { char_count: number }).char_count} />
          )}
          {(data.metrics as { word_count?: number }).word_count !== undefined && (
            <MetaBadge icon={FileText} label="単語数" value={(data.metrics as { word_count: number }).word_count} />
          )}
        </div>
      )}

      {/* 残りのフィールド */}
      <RemainingFields
        data={data}
        excludeKeys={["competitor_analysis", "competitor_count", "quality_competitor_count", "parsed_data", "format_detected", "quality", "metrics"]}
      />
    </div>
  );
}

// JSON文字列またはPythonリスト形式の文字列をパース
function parseOutlineString(str: string): unknown | null {
  // まず通常のJSONパースを試行
  try {
    return JSON.parse(str);
  } catch {
    // Python形式のシングルクォートをダブルクォートに変換
    try {
      // Python repr形式からJSON形式への変換
      // 構造を認識しながらシングルクォートをダブルクォートに変換
      const converted = convertPythonToJson(str);
      return JSON.parse(converted);
    } catch {
      // より単純な変換を試行（シングルクォートを全てダブルクォートに）
      try {
        const jsonStr = str.replace(/'/g, '"');
        return JSON.parse(jsonStr);
      } catch {
        return null;
      }
    }
  }
}

// Pythonリテラル形式をJSON形式に変換
function convertPythonToJson(str: string): string {
  let result = "";
  let i = 0;

  while (i < str.length) {
    const char = str[i];

    if (char === "'") {
      // シングルクォートで始まる文字列を処理
      result += '"';
      i++;

      // 文字列の終わりまで読み進める
      while (i < str.length) {
        const c = str[i];

        if (c === "\\") {
          // エスケープシーケンス
          if (i + 1 < str.length) {
            const next = str[i + 1];
            if (next === "'") {
              // \' は ' に変換
              result += "'";
              i += 2;
            } else if (next === '"') {
              // \" はそのまま
              result += '\\"';
              i += 2;
            } else {
              // その他のエスケープはそのまま
              result += c + next;
              i += 2;
            }
          } else {
            result += c;
            i++;
          }
        } else if (c === "'") {
          // 文字列の終わり
          result += '"';
          i++;
          break;
        } else if (c === '"') {
          // ダブルクォートはエスケープ
          result += '\\"';
          i++;
        } else {
          result += c;
          i++;
        }
      }
    } else {
      result += char;
      i++;
    }
  }

  return result;
}

// Step4: アウトライン生成
function Step4Viewer({ data }: { data: ParsedContent }) {
  const outlineRaw = typeof data.outline === "string" ? data.outline : null;

  // 新形式: article_title と sections が直接フィールドにある
  // 旧形式: outline 内にMarkdown+JSONまたはPythonリスト形式の文字列
  const articleTitle = typeof data.article_title === "string" && data.article_title.length > 0 ? data.article_title : null;
  // sections が空配列でないことを確認
  const sectionsFromData = Array.isArray(data.sections) && data.sections.length > 0 ? data.sections as Array<{
    heading?: string;
    subheadings?: string[];
    key_points?: string[];
  }> : null;

  // 旧形式のパース
  let parsedOutline: Array<{
    heading?: string;
    subheadings?: string[];
    key_points?: string[];
  }> | null = null;

  if (!sectionsFromData && outlineRaw) {
    // Markdownからの抽出を試行
    const extracted = extractJsonFromMarkdown(outlineRaw);
    if (extracted && typeof extracted === "object") {
      if (Array.isArray(extracted)) {
        parsedOutline = extracted;
      } else if ("outline" in (extracted as Record<string, unknown>)) {
        parsedOutline = (extracted as Record<string, unknown>).outline as typeof parsedOutline;
      }
    }
    // 直接パースを試行
    if (!parsedOutline) {
      const direct = parseOutlineString(outlineRaw);
      if (Array.isArray(direct)) {
        parsedOutline = direct;
      }
    }
  }

  const outlineSections = sectionsFromData || parsedOutline;
  const title = articleTitle;

  // 構造化データがあるかどうかを判定
  const hasStructuredData = title || (outlineSections && outlineSections.length > 0);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <ListOrdered className="h-5 w-5 text-primary-600" />
          <span className="text-lg font-semibold text-gray-900 dark:text-gray-100">記事アウトライン</span>
        </div>
        <ModelUsageBadges model={data.model} usage={data.usage} />
      </div>

      {hasStructuredData ? (
        <div className="space-y-4">
          {title && (
            <div className="p-4 rounded-lg bg-primary-50 dark:bg-primary-900/20 border border-primary-200 dark:border-primary-800">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">{title}</h3>
            </div>
          )}

          {outlineSections && outlineSections.length > 0 && (
            <div className="space-y-4">
              {outlineSections.map((section, i) => (
                <div
                  key={i}
                  className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 overflow-hidden"
                >
                  <div className="flex items-center gap-3 px-4 py-3 bg-gray-50 dark:bg-gray-800/50 border-b border-gray-200 dark:border-gray-700">
                    <span className="flex-shrink-0 w-6 h-6 rounded-full bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400 flex items-center justify-center text-sm font-bold">
                      {i + 1}
                    </span>
                    <h4 className="font-medium text-gray-900 dark:text-gray-100">{section.heading}</h4>
                  </div>
                  <div className="p-4 space-y-3">
                    {section.subheadings && section.subheadings.length > 0 && (
                      <div>
                        <h5 className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">小見出し</h5>
                        <ul className="space-y-1">
                          {section.subheadings.map((sub, j) => (
                            <li key={j} className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
                              <span className="w-1.5 h-1.5 rounded-full bg-gray-400" />
                              {sub}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {section.key_points && section.key_points.length > 0 && (
                      <div>
                        <h5 className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">キーポイント</h5>
                        <ul className="space-y-1">
                          {section.key_points.map((point, k) => (
                            <li key={k} className="flex items-start gap-2 text-sm text-gray-600 dark:text-gray-400">
                              <CheckCircle2 className="h-4 w-4 text-green-500 flex-shrink-0 mt-0.5" />
                              {point}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {Array.isArray(data.key_differentiators) && data.key_differentiators.length > 0 && (
            <Section icon={Lightbulb} title="差別化ポイント">
              <ul className="space-y-2">
                {(data.key_differentiators as string[]).map((point, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-gray-700 dark:text-gray-300">
                    <CheckCircle2 className="h-4 w-4 text-amber-500 flex-shrink-0 mt-0.5" />
                    {point}
                  </li>
                ))}
              </ul>
            </Section>
          )}
        </div>
      ) : outlineRaw ? (
        // JSONが取り出せなかった場合はMarkdownとして表示
        <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6">
          <div className="prose prose-sm dark:prose-invert max-w-none">
            <MarkdownViewer content={outlineRaw} />
          </div>
        </div>
      ) : (
        <p className="text-sm text-gray-500 dark:text-gray-400">アウトラインデータがありません</p>
      )}

      {/* 残りのフィールド */}
      <RemainingFields
        data={data}
        excludeKeys={["outline", "article_title", "sections", "meta_description", "key_differentiators"]}
      />
    </div>
  );
}

// Step5: ソース収集
function Step5Viewer({ data }: { data: ParsedContent }) {
  const sources = data.sources as Array<{
    url?: string;
    title?: string;
    verified?: boolean;
    source_type?: string;
    credibility_score?: number;
    excerpt?: string;
  }> | undefined;

  const invalidSources = data.invalid_sources as Array<{
    url?: string;
    title?: string;
    verified?: boolean;
    source_type?: string;
    credibility_score?: number;
    excerpt?: string;
  }> | undefined;

  const searchQueries = Array.isArray(data.search_queries) ? data.search_queries as string[] : null;
  const failedQueries = Array.isArray(data.failed_queries) ? data.failed_queries as string[] : null;
  const collectionStats = data.collection_stats as {
    total_collected?: number;
    total_verified?: number;
    failed_queries?: number;
  } | undefined;

  const hasAnyData = (sources && sources.length > 0) || (invalidSources && invalidSources.length > 0) || searchQueries;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <Globe className="h-5 w-5 text-primary-600" />
          <span className="text-lg font-semibold text-gray-900 dark:text-gray-100">ソース収集</span>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          {collectionStats?.total_collected !== undefined && (
            <MetaBadge icon={Globe} label="収集" value={collectionStats.total_collected} />
          )}
          {collectionStats?.total_verified !== undefined && (
            <MetaBadge icon={CheckCircle2} label="検証済み" value={collectionStats.total_verified} />
          )}
          {collectionStats?.failed_queries !== undefined && collectionStats.failed_queries > 0 && (
            <MetaBadge icon={AlertTriangle} label="失敗クエリ" value={collectionStats.failed_queries} />
          )}
        </div>
      </div>

      {/* 収集サマリー */}
      {collectionStats && (
        <div className="grid grid-cols-3 gap-3 p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
          <div className="text-center">
            <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
              {collectionStats.total_collected ?? 0}
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400">総収集数</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600 dark:text-green-400">
              {collectionStats.total_verified ?? 0}
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400">検証済み</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-yellow-600 dark:text-yellow-400">
              {(collectionStats.total_collected ?? 0) - (collectionStats.total_verified ?? 0)}
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400">未検証</div>
          </div>
        </div>
      )}

      {hasAnyData ? (
        <div className="space-y-4">
          {/* 検索クエリ */}
          {searchQueries && searchQueries.length > 0 && (
            <Section icon={Search} title={`検索クエリ (${searchQueries.length}件)`}>
              <div className="flex flex-wrap gap-2">
                {searchQueries.map((query, i) => (
                  <span key={i} className="px-2.5 py-1.5 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 rounded-lg text-xs font-medium">
                    {query}
                  </span>
                ))}
              </div>
            </Section>
          )}

          {/* 失敗したクエリ */}
          {failedQueries && failedQueries.length > 0 && (
            <Section icon={AlertTriangle} title={`失敗したクエリ (${failedQueries.length}件)`}>
              <div className="flex flex-wrap gap-2">
                {failedQueries.map((query, i) => (
                  <span key={i} className="px-2.5 py-1.5 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 rounded-lg text-xs">
                    {query}
                  </span>
                ))}
              </div>
            </Section>
          )}

          {/* 有効なソース */}
          {sources && sources.length > 0 && (
            <Section icon={CheckCircle2} title={`有効なソース (${sources.length}件)`}>
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {sources.map((source, i) => (
                  <div key={i} className="p-3 bg-green-50 dark:bg-green-900/10 rounded-lg border border-green-200 dark:border-green-800">
                    <div className="flex items-start gap-2">
                      <CheckCircle2 className="h-4 w-4 text-green-500 flex-shrink-0 mt-0.5" />
                      <div className="flex-1 min-w-0">
                        <a
                          href={source.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-primary-600 dark:text-primary-400 hover:underline text-sm font-medium block"
                        >
                          {source.title || "タイトルなし"}
                        </a>
                        {source.url && (
                          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5 truncate flex items-center gap-1">
                            <ExternalLink className="h-3 w-3" />
                            {source.url}
                          </p>
                        )}
                        {source.excerpt && (
                          <p className="text-xs text-gray-600 dark:text-gray-300 mt-1.5 line-clamp-2">{source.excerpt}</p>
                        )}
                        <div className="flex items-center gap-2 mt-1.5">
                          {source.source_type && (
                            <span className="px-1.5 py-0.5 bg-green-100 dark:bg-green-800/50 rounded text-xs text-green-700 dark:text-green-300">
                              {source.source_type}
                            </span>
                          )}
                          {source.credibility_score !== undefined && (
                            <span className="text-xs text-gray-500 dark:text-gray-400">
                              信頼度: {(source.credibility_score * 100).toFixed(0)}%
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </Section>
          )}

          {/* 未検証ソース */}
          {invalidSources && invalidSources.length > 0 && (
            <Section icon={AlertTriangle} title={`未検証ソース (${invalidSources.length}件)`}>
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
                これらのソースは収集されましたが、まだ検証されていません。
              </p>
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {invalidSources.map((source, i) => (
                  <div key={i} className="p-3 bg-yellow-50 dark:bg-yellow-900/10 rounded-lg border border-yellow-200 dark:border-yellow-800">
                    <div className="flex items-start gap-2">
                      <AlertTriangle className="h-4 w-4 text-yellow-500 flex-shrink-0 mt-0.5" />
                      <div className="flex-1 min-w-0">
                        <a
                          href={source.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-gray-700 dark:text-gray-300 hover:text-primary-600 dark:hover:text-primary-400 hover:underline text-sm font-medium block"
                        >
                          {source.title || "タイトルなし"}
                        </a>
                        {source.url && (
                          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5 truncate flex items-center gap-1">
                            <ExternalLink className="h-3 w-3" />
                            {source.url}
                          </p>
                        )}
                        {source.excerpt && (
                          <p className="text-xs text-gray-600 dark:text-gray-300 mt-1.5 line-clamp-2">{source.excerpt}</p>
                        )}
                        <div className="flex items-center gap-2 mt-1.5">
                          {source.source_type && (
                            <span className="px-1.5 py-0.5 bg-yellow-100 dark:bg-yellow-800/50 rounded text-xs text-yellow-700 dark:text-yellow-300">
                              {source.source_type}
                            </span>
                          )}
                          {source.credibility_score !== undefined && (
                            <span className="text-xs text-gray-500 dark:text-gray-400">
                              信頼度: {(source.credibility_score * 100).toFixed(0)}%
                            </span>
                          )}
                          {source.verified === false && (
                            <span className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-700 rounded text-xs text-gray-500 dark:text-gray-400">
                              未検証
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </Section>
          )}
        </div>
      ) : (
        <p className="text-sm text-gray-500 dark:text-gray-400">ソースデータがありません</p>
      )}

      {/* 残りのフィールド */}
      <RemainingFields
        data={data}
        excludeKeys={["sources", "invalid_sources", "search_queries", "failed_queries", "collection_stats"]}
      />
    </div>
  );
}

// Step6: アウトライン強化
function Step6Viewer({ data }: { data: ParsedContent }) {
  const enhancedOutlineRaw = typeof data.enhanced_outline === "string" ? data.enhanced_outline : null;
  const sourcesUsed = typeof data.sources_used === "number" ? data.sources_used : null;

  // 新形式: sections が直接フィールドにある（空配列は null として扱う）
  const sections = Array.isArray(data.sections) && data.sections.length > 0 ? data.sections as Array<{
    heading?: string;
    subheadings?: string[];
    key_points?: string[];
    sources?: string[] | Array<{ title?: string; url?: string }>;
    content_notes?: string;
  }> : null;

  // 新形式: enhancement_summary（文字列またはオブジェクト形式をサポート）, source_citations
  const enhancementSummaryStr = typeof data.enhancement_summary === "string" ? data.enhancement_summary : null;
  const enhancementSummaryObj = data.enhancement_summary && typeof data.enhancement_summary === "object" && !Array.isArray(data.enhancement_summary)
    ? data.enhancement_summary as {
        sections_enhanced?: number;
        sections_added?: number;
        sources_integrated?: number;
        total_word_increase?: number;
      }
    : null;

  const sourceCitations = Array.isArray(data.source_citations) ? data.source_citations as Array<{
    url?: string;
    title?: string;
    used_in_sections?: string[];
  }> : null;

  // source_citations がオブジェクト形式（URLをキーとした辞書）の場合もサポート
  const sourceCitationsObj = data.source_citations && typeof data.source_citations === "object" && !Array.isArray(data.source_citations)
    ? data.source_citations as Record<string, unknown>
    : null;

  // セクション型定義
  type OutlineSection = {
    heading?: string;
    subheadings?: string[];
    key_points?: string[];
    sources?: string[] | Array<{ title?: string; url?: string }>;
    content_notes?: string;
  };

  // 旧形式のパース - Python形式のリスト文字列をパース
  let parsedOutline: OutlineSection[] | null = null;

  // sections が空または null の場合、enhanced_outline をパース
  if (!sections && enhancedOutlineRaw) {
    // Markdownからの抽出を試行
    const extracted = extractJsonFromMarkdown(enhancedOutlineRaw);
    if (extracted && Array.isArray(extracted)) {
      parsedOutline = extracted as OutlineSection[];
    } else {
      // 直接パースを試行
      const direct = parseOutlineString(enhancedOutlineRaw);
      if (direct && Array.isArray(direct)) {
        parsedOutline = direct as OutlineSection[];
      }
    }
  }

  const outlineSections = sections || parsedOutline;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-primary-600" />
          <span className="text-lg font-semibold text-gray-900 dark:text-gray-100">強化されたアウトライン</span>
        </div>
        <div className="flex items-center gap-2">
          {sourcesUsed !== null && <MetaBadge icon={Globe} label="使用ソース" value={sourcesUsed} />}
          {outlineSections && <MetaBadge icon={ListOrdered} label="セクション" value={outlineSections.length} />}
          <ModelUsageBadges model={data.model} usage={data.usage} />
        </div>
      </div>

      {/* 強化サマリー（文字列形式） */}
      {enhancementSummaryStr && (
        <Section icon={Lightbulb} title="強化サマリー">
          <p className="text-sm text-gray-700 dark:text-gray-300">{enhancementSummaryStr}</p>
        </Section>
      )}

      {/* 強化サマリー（オブジェクト形式） */}
      {enhancementSummaryObj && (
        <Section icon={BarChart3} title="強化統計">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {enhancementSummaryObj.sections_enhanced !== undefined && (
              <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg text-center">
                <div className="text-xl font-bold text-gray-900 dark:text-gray-100">
                  {enhancementSummaryObj.sections_enhanced}
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400">強化セクション</div>
              </div>
            )}
            {enhancementSummaryObj.sections_added !== undefined && (
              <div className="p-3 bg-green-50 dark:bg-green-900/20 rounded-lg text-center">
                <div className="text-xl font-bold text-green-700 dark:text-green-300">
                  +{enhancementSummaryObj.sections_added}
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400">追加セクション</div>
              </div>
            )}
            {enhancementSummaryObj.sources_integrated !== undefined && (
              <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg text-center">
                <div className="text-xl font-bold text-blue-700 dark:text-blue-300">
                  {enhancementSummaryObj.sources_integrated}
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400">統合ソース</div>
              </div>
            )}
            {enhancementSummaryObj.total_word_increase !== undefined && (
              <div className="p-3 bg-purple-50 dark:bg-purple-900/20 rounded-lg text-center">
                <div className="text-xl font-bold text-purple-700 dark:text-purple-300">
                  +{enhancementSummaryObj.total_word_increase.toLocaleString()}
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400">文字増加</div>
              </div>
            )}
          </div>
        </Section>
      )}

      {/* 構造化されたセクション */}
      {outlineSections && outlineSections.length > 0 ? (
        <div className="space-y-3">
          {outlineSections.map((section, index) => (
            <div key={index} className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 overflow-hidden">
              <div className="px-4 py-3 bg-gradient-to-r from-primary-50 to-transparent dark:from-primary-900/20">
                <div className="flex items-center gap-2">
                  <span className="flex items-center justify-center w-6 h-6 rounded-full bg-primary-100 dark:bg-primary-800 text-primary-700 dark:text-primary-300 text-xs font-bold">
                    {index + 1}
                  </span>
                  <h4 className="text-base font-semibold text-gray-900 dark:text-gray-100">{section.heading || `セクション ${index + 1}`}</h4>
                </div>
              </div>
              <div className="p-4 space-y-3">
                {/* サブ見出し */}
                {section.subheadings && section.subheadings.length > 0 && (
                  <div>
                    <h5 className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1.5">サブ見出し</h5>
                    <ul className="space-y-1">
                      {section.subheadings.map((sub, subIndex) => (
                        <li key={subIndex} className="flex items-start gap-2 text-sm text-gray-700 dark:text-gray-300">
                          <span className="text-primary-500 mt-1">•</span>
                          {sub}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* キーポイント */}
                {section.key_points && section.key_points.length > 0 && (
                  <div>
                    <h5 className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1.5">キーポイント</h5>
                    <ul className="space-y-1">
                      {section.key_points.map((point, pointIndex) => (
                        <li key={pointIndex} className="flex items-start gap-2 text-sm text-gray-700 dark:text-gray-300">
                          <CheckCircle2 className="h-4 w-4 text-green-500 flex-shrink-0 mt-0.5" />
                          {point}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* ソース参照（文字列配列またはオブジェクト配列） */}
                {section.sources && section.sources.length > 0 && (
                  <div>
                    <h5 className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1.5">参照ソース</h5>
                    <ul className="space-y-1">
                      {section.sources.map((source, sourceIndex) => {
                        // 文字列形式の場合
                        if (typeof source === "string") {
                          return (
                            <li key={sourceIndex} className="flex items-center gap-2 text-sm">
                              <ExternalLink className="h-3.5 w-3.5 text-gray-400 flex-shrink-0" />
                              <span className="text-gray-600 dark:text-gray-400">{source}</span>
                            </li>
                          );
                        }
                        // オブジェクト形式の場合
                        return (
                          <li key={sourceIndex} className="flex items-center gap-2 text-sm">
                            <ExternalLink className="h-3.5 w-3.5 text-gray-400 flex-shrink-0" />
                            {source.url ? (
                              <a
                                href={source.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-primary-600 hover:text-primary-700 dark:text-primary-400 hover:underline truncate"
                              >
                                {source.title || source.url}
                              </a>
                            ) : (
                              <span className="text-gray-600 dark:text-gray-400">{source.title}</span>
                            )}
                          </li>
                        );
                      })}
                    </ul>
                  </div>
                )}

                {/* コンテンツノート */}
                {section.content_notes && (
                  <div className="pt-2 border-t border-gray-100 dark:border-gray-700">
                    <p className="text-xs text-gray-500 dark:text-gray-400 italic">{section.content_notes}</p>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      ) : enhancedOutlineRaw ? (
        // 構造化できない場合はMarkdownとして表示
        <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6">
          <div className="prose prose-sm dark:prose-invert max-w-none">
            <MarkdownViewer content={enhancedOutlineRaw} />
          </div>
        </div>
      ) : (
        <p className="text-sm text-gray-500 dark:text-gray-400">アウトラインデータがありません</p>
      )}

      {/* ソース引用一覧（配列形式） */}
      {sourceCitations && sourceCitations.length > 0 && (
        <Section icon={Globe} title="引用ソース一覧">
          <ul className="space-y-2">
            {sourceCitations.map((citation, index) => (
              <li key={index} className="flex items-start gap-2 text-sm">
                <span className="text-gray-400 flex-shrink-0">{index + 1}.</span>
                <div>
                  {citation.url ? (
                    <a
                      href={citation.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary-600 hover:text-primary-700 dark:text-primary-400 hover:underline"
                    >
                      {citation.title || citation.url}
                    </a>
                  ) : (
                    <span className="text-gray-700 dark:text-gray-300">{citation.title}</span>
                  )}
                  {citation.used_in_sections && citation.used_in_sections.length > 0 && (
                    <span className="ml-2 text-xs text-gray-500">
                      使用: {citation.used_in_sections.join(", ")}
                    </span>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </Section>
      )}

      {/* ソース引用一覧（オブジェクト形式） */}
      {sourceCitationsObj && Object.keys(sourceCitationsObj).length > 0 && (
        <Section icon={Globe} title="引用ソース">
          <ul className="space-y-2">
            {Object.entries(sourceCitationsObj).map(([url, data], index) => (
              <li key={index} className="flex items-start gap-2 text-sm">
                <span className="text-gray-400 flex-shrink-0">{index + 1}.</span>
                <div>
                  <a
                    href={url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary-600 hover:text-primary-700 dark:text-primary-400 hover:underline"
                  >
                    {url}
                  </a>
                  {typeof data === "object" && data !== null && (
                    <span className="ml-2 text-xs text-gray-500">
                      {JSON.stringify(data)}
                    </span>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </Section>
      )}

      {/* 残りのフィールド */}
      <RemainingFields
        data={data}
        excludeKeys={["enhanced_outline", "sources_used", "sections", "enhancement_summary", "source_citations"]}
      />
    </div>
  );
}

// Step6_5: 統合パッケージ
function Step6_5Viewer({ data }: { data: ParsedContent }) {
  const integrationPackage = typeof data.integration_package === "string" ? data.integration_package : null;
  const sectionCount = typeof data.section_count === "number" ? data.section_count : null;
  const totalSources = typeof data.total_sources === "number" ? data.total_sources : null;

  // inputs_summary: 文字列形式またはオブジェクト形式をサポート
  const inputsSummaryStr = typeof data.inputs_summary === "string" ? data.inputs_summary : null;
  const inputsSummaryObj = data.inputs_summary && typeof data.inputs_summary === "object" && !Array.isArray(data.inputs_summary)
    ? data.inputs_summary as Record<string, boolean>
    : null;

  const outlineSummary = typeof data.outline_summary === "string" ? data.outline_summary : null;

  // 入力サマリーをバッジ形式で表示するためのラベルマッピング
  const inputSummaryLabels: Record<string, string> = {
    has_keyword_analysis: "キーワード分析",
    has_query_analysis: "クエリ分析",
    has_cooccurrence: "共起語分析",
    has_competitor_analysis: "競合分析",
    has_strategic_outline: "戦略的アウトライン",
    has_sources: "ソース収集",
    has_enhanced_outline: "強化アウトライン",
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <BookOpen className="h-5 w-5 text-primary-600" />
          <span className="text-lg font-semibold text-gray-900 dark:text-gray-100">統合パッケージ</span>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          {sectionCount !== null && <MetaBadge icon={ListOrdered} label="セクション" value={sectionCount} />}
          {totalSources !== null && <MetaBadge icon={Globe} label="ソース" value={totalSources} />}
          <ModelUsageBadges model={data.model} usage={data.usage} />
        </div>
      </div>

      {/* サマリー情報 */}
      {(inputsSummaryStr || inputsSummaryObj || outlineSummary) && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {inputsSummaryStr ? (
            <Section icon={FileText} title="入力サマリー">
              <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">{inputsSummaryStr}</p>
            </Section>
          ) : inputsSummaryObj ? (
            <Section icon={FileText} title="入力データ状況">
              <div className="flex flex-wrap gap-2">
                {Object.entries(inputsSummaryObj).map(([key, value]) => (
                  <span
                    key={key}
                    className={cn(
                      "px-2.5 py-1 rounded-full text-xs font-medium",
                      value
                        ? "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300"
                        : "bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400"
                    )}
                  >
                    {value ? "✓ " : "✗ "}
                    {inputSummaryLabels[key] || key}
                  </span>
                ))}
              </div>
            </Section>
          ) : null}
          {outlineSummary && (
            <Section icon={ListOrdered} title="アウトラインサマリー">
              <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">{outlineSummary}</p>
            </Section>
          )}
        </div>
      )}

      {/* 統合パッケージ本文 */}
      {integrationPackage ? (
        <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6">
          <div className="prose prose-sm dark:prose-invert max-w-none">
            <MarkdownViewer content={integrationPackage} />
          </div>
        </div>
      ) : (
        <p className="text-sm text-gray-500 dark:text-gray-400">統合パッケージデータがありません</p>
      )}

      {/* 残りのフィールド */}
      <RemainingFields
        data={data}
        excludeKeys={["integration_package", "section_count", "total_sources", "inputs_summary", "outline_summary"]}
      />
    </div>
  );
}

// Step7: 記事ドラフト生成
function Step7Viewer({ data }: { data: ParsedContent }) {
  const draft = typeof data.draft === "string" ? data.draft : null;
  const sectionCount = typeof data.section_count === "number" ? data.section_count : null;
  const ctaPositions = Array.isArray(data.cta_positions) ? data.cta_positions as string[] : null;
  const stats = data.stats as { word_count?: number; char_count?: number } | undefined;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <FileText className="h-5 w-5 text-primary-600" />
          <span className="text-lg font-semibold text-gray-900 dark:text-gray-100">記事ドラフト</span>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          {sectionCount !== null && <MetaBadge icon={ListOrdered} label="セクション" value={sectionCount} />}
          {stats?.word_count && <MetaBadge icon={FileText} label="単語数" value={stats.word_count.toLocaleString()} />}
          {stats?.char_count && <MetaBadge icon={Hash} label="文字数" value={stats.char_count.toLocaleString()} />}
          <ModelUsageBadges model={data.model} usage={data.usage} />
        </div>
      </div>

      {/* CTA配置情報 */}
      {ctaPositions && ctaPositions.length > 0 && (
        <Section icon={Target} title="CTA配置位置">
          <div className="flex flex-wrap gap-2">
            {ctaPositions.map((pos, i) => (
              <span
                key={i}
                className="px-3 py-1.5 rounded-full text-xs bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400"
              >
                {pos}
              </span>
            ))}
          </div>
        </Section>
      )}

      {/* ドラフト本文 */}
      {draft ? (
        <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6">
          <div className="prose prose-sm dark:prose-invert max-w-none">
            <MarkdownViewer content={draft} />
          </div>
        </div>
      ) : (
        <p className="text-sm text-gray-500 dark:text-gray-400">ドラフトデータがありません</p>
      )}

      {/* 残りのフィールド */}
      <RemainingFields
        data={data}
        excludeKeys={["draft", "section_count", "cta_positions", "stats"]}
      />
    </div>
  );
}

// 汎用ビューア（構造化されていないJSON向け）
function GenericViewer({ data }: { data: ParsedContent }) {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <FileText className="h-5 w-5 text-primary-600" />
        <span className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          {data.step || "出力データ"}
        </span>
      </div>

      {typeof data.keyword === "string" && data.keyword && (
        <div className="flex items-center gap-2 p-3 rounded-lg bg-gray-50 dark:bg-gray-800/50">
          <Hash className="h-4 w-4 text-gray-500" />
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{data.keyword}</span>
        </div>
      )}

      <div className="grid grid-cols-1 gap-4">
        {Object.entries(data)
          .filter(([key]) => !["step", "keyword", "model", "usage"].includes(key))
          .map(([key, value]) => (
            <div
              key={key}
              className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800"
            >
              <div className="px-4 py-2 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
                <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">{key}</h4>
              </div>
              <div className="p-4">
                {typeof value === "string" ? (
                  value.length > 500 ? (
                    <div className="prose prose-sm dark:prose-invert max-w-none">
                      <MarkdownViewer content={value} />
                    </div>
                  ) : (
                    <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">{value}</p>
                  )
                ) : (
                  <pre className="text-xs text-gray-600 dark:text-gray-400 overflow-auto max-h-64 whitespace-pre-wrap font-mono">
                    {JSON.stringify(value, null, 2)}
                  </pre>
                )}
              </div>
            </div>
          ))}
      </div>

      <ModelUsageBadges model={data.model} usage={data.usage} />
    </div>
  );
}

// Step11: 画像生成ビューア
interface Step11Data extends ParsedContent {
  enabled?: boolean;
  image_count?: number;
  images?: Array<{
    request?: {
      position?: {
        section_title?: string;
        section_index?: number;
        position?: string;
        source_text?: string;
        description?: string;
      };
      user_instruction?: string;
      generated_prompt?: string;
      alt_text?: string;
    };
    image_path?: string;
    image_base64?: string;
    mime_type?: string;
    width?: number;
    height?: number;
    file_size?: number;
    accepted?: boolean;
  }>;
  markdown_with_images?: string;
  html_with_images?: string;
  warnings?: string[];
}

function Step11Viewer({ data }: { data: Step11Data }) {
  const enabled = data.enabled !== false;
  const images = data.images || [];
  const imageCount = data.image_count || images.length;
  const hasMarkdown = !!data.markdown_with_images;
  const hasHtml = !!data.html_with_images;
  const warnings = data.warnings || [];

  if (!enabled) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-gray-400" />
          <span className="text-lg font-semibold text-gray-700 dark:text-gray-300">
            画像生成 (スキップ)
          </span>
        </div>
        <div className="p-4 rounded-lg bg-gray-50 dark:bg-gray-800/50 text-sm text-gray-600 dark:text-gray-400">
          画像生成はスキップされました
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* ヘッダー */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-purple-600 dark:text-purple-400" />
          <span className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            画像生成
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="px-2 py-1 text-xs font-medium bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 rounded">
            {imageCount} 画像生成
          </span>
        </div>
      </div>

      {/* 警告 */}
      {warnings.length > 0 && (
        <div className="p-3 rounded-lg bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800">
          <div className="flex items-start gap-2">
            <AlertTriangle className="h-4 w-4 text-yellow-600 dark:text-yellow-500 mt-0.5" />
            <div className="space-y-1">
              {warnings.map((warning, i) => (
                <p key={i} className="text-sm text-yellow-700 dark:text-yellow-400">
                  {warning}
                </p>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* 生成画像一覧 */}
      {images.length > 0 && (
        <Section icon={Sparkles} title="生成画像">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {images.map((img, idx) => (
              <div
                key={idx}
                className="rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden"
              >
                {/* 画像プレビュー */}
                {img.image_base64 && (
                  <div className="relative aspect-video bg-gray-100 dark:bg-gray-800">
                    <img
                      src={`data:${img.mime_type || "image/png"};base64,${img.image_base64}`}
                      alt={img.request?.alt_text || `Generated image ${idx + 1}`}
                      className="w-full h-full object-contain"
                    />
                    {img.accepted && (
                      <div className="absolute top-2 right-2">
                        <CheckCircle2 className="h-5 w-5 text-green-500" />
                      </div>
                    )}
                  </div>
                )}

                {/* 画像情報 */}
                <div className="p-3 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                      画像 #{idx + 1}
                    </span>
                    {img.width && img.height && (
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        {img.width} × {img.height}
                      </span>
                    )}
                  </div>

                  {img.request?.position?.section_title && (
                    <div className="text-xs text-gray-600 dark:text-gray-400">
                      <span className="font-medium">挿入先:</span> {img.request.position.section_title}
                    </div>
                  )}

                  {img.request?.alt_text && (
                    <div className="text-xs text-gray-600 dark:text-gray-400">
                      <span className="font-medium">Alt:</span> {img.request.alt_text}
                    </div>
                  )}

                  {img.request?.generated_prompt && (
                    <details className="text-xs">
                      <summary className="cursor-pointer text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300">
                        生成プロンプトを表示
                      </summary>
                      <p className="mt-1 p-2 bg-gray-50 dark:bg-gray-800 rounded text-gray-600 dark:text-gray-400 whitespace-pre-wrap">
                        {img.request.generated_prompt}
                      </p>
                    </details>
                  )}

                  {img.file_size && img.file_size > 0 && (
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      サイズ: {(img.file_size / 1024).toFixed(1)} KB
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Markdownプレビュー */}
      {hasMarkdown && (
        <Section icon={FileText} title="画像挿入済みMarkdown">
          <div className="max-h-96 overflow-auto">
            <MarkdownViewer content={data.markdown_with_images || ""} />
          </div>
        </Section>
      )}

      {/* HTMLプレビュー */}
      {hasHtml && (
        <Section icon={Globe} title="画像挿入済みHTML">
          <details>
            <summary className="cursor-pointer text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100">
              HTMLコードを表示
            </summary>
            <pre className="mt-2 p-3 bg-gray-50 dark:bg-gray-900 rounded text-xs text-gray-700 dark:text-gray-300 overflow-auto max-h-64 whitespace-pre-wrap font-mono">
              {data.html_with_images}
            </pre>
          </details>
        </Section>
      )}

      {/* モデル使用情報 */}
      <ModelUsageBadges model={data.model} usage={data.usage} />
    </div>
  );
}
