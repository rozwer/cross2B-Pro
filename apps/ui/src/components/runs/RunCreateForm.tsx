"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Plus, X, AlertCircle, ExternalLink, Search, Globe, Shield, FileText } from "lucide-react";
import Link from "next/link";
import type { CreateRunInput } from "@/lib/types";
import { WORKFLOW_STEPS, type StepConfig } from "@/components/workflow";
import { ProviderLogo } from "@/components/icons/ProviderLogos";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

const createRunSchema = z.object({
  keyword: z.string().min(1, "キーワードは必須です"),
  target_audience: z.string().optional(),
  additional_requirements: z.string().optional(),
  retry_limit: z.number().min(1).max(10),
  repair_enabled: z.boolean(),
  serp_fetch: z.boolean(),
  page_fetch: z.boolean(),
  url_verify: z.boolean(),
  pdf_extract: z.boolean(),
});

type FormData = z.infer<typeof createRunSchema>;

export function RunCreateForm() {
  const router = useRouter();
  const [competitorUrls, setCompetitorUrls] = useState<string[]>([""]);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [stepConfigs, setStepConfigs] = useState<StepConfig[]>(WORKFLOW_STEPS);

  useEffect(() => {
    const savedConfig = localStorage.getItem("workflow-config");
    if (savedConfig) {
      try {
        setStepConfigs(JSON.parse(savedConfig));
      } catch (e) {
        console.error("Failed to parse saved config:", e);
      }
    }
  }, []);

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<FormData>({
    resolver: zodResolver(createRunSchema),
    defaultValues: {
      keyword: "",
      target_audience: "",
      additional_requirements: "",
      retry_limit: 3,
      repair_enabled: true,
      serp_fetch: true,
      page_fetch: true,
      url_verify: true,
      pdf_extract: false,
    },
  });

  const retryLimit = watch("retry_limit");

  const addCompetitorUrl = () => setCompetitorUrls([...competitorUrls, ""]);
  const removeCompetitorUrl = (index: number) =>
    setCompetitorUrls(competitorUrls.filter((_, i) => i !== index));
  const updateCompetitorUrl = (index: number, value: string) => {
    const updated = [...competitorUrls];
    updated[index] = value;
    setCompetitorUrls(updated);
  };

  const onSubmit = async (data: FormData) => {
    setSubmitting(true);
    setSubmitError(null);

    const configurableSteps = stepConfigs.filter(
      (s) => s.isConfigurable && s.stepId !== "approval",
    );
    // step_configs: 空配列の場合は undefined にする（バックエンドの None と一致させる）
    // Normalize step_ids: convert dots to underscores (step6.5 -> step6_5)
    const stepConfigsPayload = configurableSteps.length > 0
      ? configurableSteps.map((step) => ({
          step_id: step.stepId.replace(/\./g, "_"),
          platform: step.aiModel,
          model: step.modelName,
          temperature: step.temperature,
          grounding: step.grounding,
          retry_limit: step.retryLimit,
          repair_enabled: step.repairEnabled,
        }))
      : undefined;

    const firstStep = configurableSteps[0] || stepConfigs[0];

    const input: CreateRunInput = {
      input: {
        format_type: "legacy",  // Required for discriminated union
        keyword: data.keyword,
        target_audience: data.target_audience || undefined,
        competitor_urls: competitorUrls.filter((url) => url.trim() !== ""),
        additional_requirements: data.additional_requirements || undefined,
      },
      model_config: {
        platform: firstStep.aiModel,
        model: firstStep.modelName,
        options: {
          grounding: firstStep.grounding,
          temperature: firstStep.temperature,
        },
      },
      step_configs: stepConfigsPayload,
      tool_config: {
        serp_fetch: data.serp_fetch,
        page_fetch: data.page_fetch,
        url_verify: data.url_verify,
        pdf_extract: data.pdf_extract,
      },
      options: {
        retry_limit: data.retry_limit,
        repair_enabled: data.repair_enabled,
      },
    };

    try {
      const run = await api.runs.create(input);
      router.push(`/runs/${run.id}`);
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : "Failed to create run");
    } finally {
      setSubmitting(false);
    }
  };

  const inputClass =
    "w-full px-3 py-2.5 text-sm border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all";
  const labelClass = "block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5";

  const TOOLS = [
    {
      name: "serp_fetch",
      label: "SERP取得",
      desc: "Google検索結果を取得",
      icon: Search,
      recommended: true,
    },
    {
      name: "page_fetch",
      label: "ページ取得",
      desc: "競合ページの本文を取得",
      icon: Globe,
      recommended: true,
    },
    {
      name: "url_verify",
      label: "URL検証",
      desc: "参照URLの有効性確認",
      icon: Shield,
      recommended: true,
    },
    {
      name: "pdf_extract",
      label: "PDF抽出",
      desc: "PDFからテキストを抽出",
      icon: FileText,
      recommended: false,
    },
  ];

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-8">
      {submitError && (
        <div className="flex items-start gap-3 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
          <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-red-700 dark:text-red-300">{submitError}</p>
        </div>
      )}

      {/* 入力情報 */}
      <section className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100 dark:border-gray-700">
          <h2 className="font-medium text-gray-900 dark:text-gray-100">入力情報</h2>
        </div>
        <div className="p-5 space-y-5">
          <div>
            <label className={labelClass}>
              キーワード <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              {...register("keyword")}
              className={cn(
                inputClass,
                errors.keyword && "border-red-300 dark:border-red-600 focus:border-red-500",
              )}
              placeholder="SEO対策 初心者"
            />
            {errors.keyword ? (
              <p className="mt-1.5 text-sm text-red-600 dark:text-red-400">
                {errors.keyword.message}
              </p>
            ) : (
              <p className="mt-1.5 text-xs text-gray-500 dark:text-gray-400">
                上位表示を狙うキーワードを入力
              </p>
            )}
          </div>

          <div>
            <label className={labelClass}>ターゲット</label>
            <input
              type="text"
              {...register("target_audience")}
              className={inputClass}
              placeholder="Webマーケティング初心者"
            />
            <p className="mt-1.5 text-xs text-gray-500 dark:text-gray-400">記事の想定読者を記述</p>
          </div>

          <div>
            <label className={labelClass}>
              競合URL
              {competitorUrls.filter((u) => u.trim()).length > 0 && (
                <span className="ml-2 text-xs font-normal text-gray-400">
                  {competitorUrls.filter((u) => u.trim()).length}件
                </span>
              )}
            </label>
            <div className="space-y-2">
              {competitorUrls.map((url, index) => (
                <div key={index} className="flex gap-2">
                  <input
                    type="url"
                    value={url}
                    onChange={(e) => updateCompetitorUrl(index, e.target.value)}
                    className={cn(inputClass, "flex-1")}
                    placeholder="https://example.com/article"
                  />
                  {competitorUrls.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeCompetitorUrl(index)}
                      className="px-2 text-gray-400 hover:text-red-500 transition-colors"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  )}
                </div>
              ))}
            </div>
            <button
              type="button"
              onClick={addCompetitorUrl}
              className="mt-2 text-sm text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 inline-flex items-center gap-1"
            >
              <Plus className="w-3.5 h-3.5" />
              追加
            </button>
          </div>

          <div>
            <label className={labelClass}>追加要件</label>
            <textarea
              {...register("additional_requirements")}
              rows={3}
              className={cn(inputClass, "resize-none")}
              placeholder="専門用語は避けてください、具体的な事例を含めてください"
            />
          </div>
        </div>
      </section>

      {/* モデル設定 */}
      <section className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100 dark:border-gray-700 flex items-center justify-between">
          <h2 className="font-medium text-gray-900 dark:text-gray-100">モデル設定</h2>
          <Link
            href="/"
            className="text-sm text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 inline-flex items-center gap-1"
          >
            変更
            <ExternalLink className="w-3.5 h-3.5" />
          </Link>
        </div>
        <div className="p-5">
          <div className="flex flex-wrap gap-4">
            {(() => {
              const counts = stepConfigs
                .filter((s) => s.isConfigurable && s.stepId !== "approval")
                .reduce(
                  (acc, step) => {
                    acc[step.aiModel] = (acc[step.aiModel] || 0) + 1;
                    return acc;
                  },
                  {} as Record<string, number>,
                );

              return (
                <>
                  {counts.gemini > 0 && (
                    <div className="flex items-center gap-2.5 px-4 py-2.5 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                      <ProviderLogo platform="gemini" size={22} />
                      <div>
                        <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                          Gemini
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          {counts.gemini}工程
                        </p>
                      </div>
                    </div>
                  )}
                  {counts.anthropic > 0 && (
                    <div className="flex items-center gap-2.5 px-4 py-2.5 bg-orange-50 dark:bg-orange-900/20 rounded-lg">
                      <ProviderLogo platform="anthropic" size={22} />
                      <div>
                        <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                          Claude
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          {counts.anthropic}工程
                        </p>
                      </div>
                    </div>
                  )}
                  {counts.openai > 0 && (
                    <div className="flex items-center gap-2.5 px-4 py-2.5 bg-green-50 dark:bg-green-900/20 rounded-lg">
                      <ProviderLogo platform="openai" size={22} />
                      <div>
                        <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                          OpenAI
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          {counts.openai}工程
                        </p>
                      </div>
                    </div>
                  )}
                </>
              );
            })()}
          </div>
          <p className="mt-3 text-xs text-gray-500 dark:text-gray-400">
            ホーム画面で設定した工程別モデルが使用されます
          </p>
        </div>
      </section>

      {/* ツール設定 */}
      <section className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100 dark:border-gray-700">
          <h2 className="font-medium text-gray-900 dark:text-gray-100">ツール設定</h2>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
            記事生成に使用する外部ツール
          </p>
        </div>
        <div className="p-5">
          <div className="grid sm:grid-cols-2 gap-3">
            {TOOLS.map((tool) => {
              const Icon = tool.icon;
              const isChecked = watch(tool.name as keyof FormData);
              return (
                <label
                  key={tool.name}
                  className={cn(
                    "flex items-start gap-3 p-3.5 rounded-lg border cursor-pointer transition-all",
                    isChecked
                      ? "border-blue-200 dark:border-blue-800 bg-blue-50/50 dark:bg-blue-900/10"
                      : "border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600",
                  )}
                >
                  <input
                    type="checkbox"
                    {...register(tool.name as keyof FormData)}
                    className="sr-only"
                  />
                  <div
                    className={cn(
                      "w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0",
                      isChecked
                        ? "bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400"
                        : "bg-gray-100 dark:bg-gray-800 text-gray-400",
                    )}
                  >
                    <Icon className="w-4.5 h-4.5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                        {tool.label}
                      </span>
                      {tool.recommended && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400 font-medium">
                          推奨
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{tool.desc}</p>
                  </div>
                  <div
                    className={cn(
                      "w-5 h-5 rounded border-2 flex items-center justify-center flex-shrink-0 mt-0.5 transition-all",
                      isChecked
                        ? "bg-blue-600 border-blue-600"
                        : "border-gray-300 dark:border-gray-600",
                    )}
                  >
                    {isChecked && (
                      <svg className="w-3 h-3 text-white" viewBox="0 0 12 12" fill="none">
                        <path
                          d="M2 6L5 9L10 3"
                          stroke="currentColor"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      </svg>
                    )}
                  </div>
                </label>
              );
            })}
          </div>
        </div>
      </section>

      {/* 実行オプション */}
      <section className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100 dark:border-gray-700">
          <h2 className="font-medium text-gray-900 dark:text-gray-100">実行オプション</h2>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
            エラー時の挙動と品質管理
          </p>
        </div>
        <div className="p-5 space-y-5">
          <div>
            <label className={labelClass}>リトライ上限</label>
            <div className="flex items-center gap-4">
              <input
                type="number"
                min="1"
                max="10"
                {...register("retry_limit", { valueAsNumber: true })}
                className={cn(inputClass, "w-20 text-center")}
              />
              <span className="text-sm text-gray-500 dark:text-gray-400">回</span>
              <div className="flex gap-1.5 ml-auto">
                {[1, 3, 5].map((n) => (
                  <button
                    key={n}
                    type="button"
                    onClick={() => setValue("retry_limit", n)}
                    className={cn(
                      "px-3 py-1.5 text-xs font-medium rounded-md transition-all",
                      retryLimit === n
                        ? "bg-gray-900 dark:bg-white text-white dark:text-gray-900"
                        : "bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600",
                    )}
                  >
                    {n === 3 ? "3 (推奨)" : n}
                  </button>
                ))}
              </div>
            </div>
            <p className="mt-1.5 text-xs text-gray-500 dark:text-gray-400">
              多すぎるとAPI費用が増加します
            </p>
          </div>

          <div className="border-t border-gray-100 dark:border-gray-700 pt-5">
            <label
              className={cn(
                "flex items-start gap-3 p-3.5 rounded-lg border cursor-pointer transition-all",
                watch("repair_enabled")
                  ? "border-blue-200 dark:border-blue-800 bg-blue-50/50 dark:bg-blue-900/10"
                  : "border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600",
              )}
            >
              <input type="checkbox" {...register("repair_enabled")} className="sr-only" />
              <div
                className={cn(
                  "w-5 h-5 rounded border-2 flex items-center justify-center flex-shrink-0 mt-0.5 transition-all",
                  watch("repair_enabled")
                    ? "bg-blue-600 border-blue-600"
                    : "border-gray-300 dark:border-gray-600",
                )}
              >
                {watch("repair_enabled") && (
                  <svg className="w-3 h-3 text-white" viewBox="0 0 12 12" fill="none">
                    <path
                      d="M2 6L5 9L10 3"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                )}
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                    自動修正を有効化
                  </span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400 font-medium">
                    推奨
                  </span>
                </div>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                  JSON形式などの軽微なエラーを自動修正し、リトライ回数を節約
                </p>
              </div>
            </label>
          </div>
        </div>
      </section>

      {/* Submit */}
      <div className="flex items-center justify-end gap-3 pt-2">
        <Link
          href="/"
          className="px-4 py-2.5 text-sm font-medium text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 transition-colors"
        >
          キャンセル
        </Link>
        <button
          type="submit"
          disabled={submitting}
          className="px-6 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-sm"
        >
          {submitting ? "作成中..." : "Runを作成"}
        </button>
      </div>
    </form>
  );
}
