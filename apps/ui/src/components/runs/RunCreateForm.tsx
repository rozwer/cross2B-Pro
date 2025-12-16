'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Plus, X, AlertCircle } from 'lucide-react';
import type { CreateRunInput, LLMPlatform } from '@/lib/types';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';

const createRunSchema = z.object({
  keyword: z.string().min(1, 'キーワードは必須です'),
  target_audience: z.string().optional(),
  additional_requirements: z.string().optional(),
  platform: z.enum(['gemini', 'openai', 'anthropic']),
  model: z.string().min(1, 'モデルは必須です'),
  grounding: z.boolean(),
  temperature: z.number().min(0).max(2),
  retry_limit: z.number().min(1).max(10),
  repair_enabled: z.boolean(),
  serp_fetch: z.boolean(),
  page_fetch: z.boolean(),
  url_verify: z.boolean(),
  pdf_extract: z.boolean(),
});

type FormData = z.infer<typeof createRunSchema>;

const PLATFORM_MODELS: Record<LLMPlatform, string[]> = {
  gemini: ['gemini-2.0-flash', 'gemini-2.5-pro', 'gemini-1.5-pro'],
  openai: ['gpt-4o', 'gpt-4-turbo', 'o3'],
  anthropic: ['claude-sonnet-4', 'claude-opus-4'],
};

export function RunCreateForm() {
  const router = useRouter();
  const [competitorUrls, setCompetitorUrls] = useState<string[]>(['']);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors },
  } = useForm<FormData>({
    resolver: zodResolver(createRunSchema),
    defaultValues: {
      keyword: '',
      target_audience: '',
      additional_requirements: '',
      platform: 'gemini',
      model: 'gemini-2.0-flash',
      grounding: true,
      temperature: 0.7,
      retry_limit: 3,
      repair_enabled: true,
      serp_fetch: true,
      page_fetch: true,
      url_verify: true,
      pdf_extract: false,
    },
  });

  const platform = watch('platform');

  const handlePlatformChange = (newPlatform: LLMPlatform) => {
    setValue('platform', newPlatform);
    setValue('model', PLATFORM_MODELS[newPlatform][0]);
  };

  const addCompetitorUrl = () => {
    setCompetitorUrls([...competitorUrls, '']);
  };

  const removeCompetitorUrl = (index: number) => {
    setCompetitorUrls(competitorUrls.filter((_, i) => i !== index));
  };

  const updateCompetitorUrl = (index: number, value: string) => {
    const updated = [...competitorUrls];
    updated[index] = value;
    setCompetitorUrls(updated);
  };

  const onSubmit = async (data: FormData) => {
    setSubmitting(true);
    setSubmitError(null);

    const input: CreateRunInput = {
      input: {
        keyword: data.keyword,
        target_audience: data.target_audience || undefined,
        competitor_urls: competitorUrls.filter((url) => url.trim() !== ''),
        additional_requirements: data.additional_requirements || undefined,
      },
      model_config: {
        platform: data.platform,
        model: data.model,
        options: {
          grounding: data.grounding,
          temperature: data.temperature,
        },
      },
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
      setSubmitError(err instanceof Error ? err.message : 'Failed to create run');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-8">
      {submitError && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3">
          <AlertCircle className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-red-700">{submitError}</p>
        </div>
      )}

      {/* 工程-1 入力 */}
      <section className="bg-white rounded-lg border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          工程-1: 入力情報
        </h2>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              キーワード <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              {...register('keyword')}
              className={cn(
                'w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500',
                errors.keyword ? 'border-red-300' : 'border-gray-300'
              )}
              placeholder="例: SEO対策 初心者"
            />
            {errors.keyword && (
              <p className="mt-1 text-sm text-red-600">{errors.keyword.message}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              ターゲットオーディエンス
            </label>
            <input
              type="text"
              {...register('target_audience')}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="例: Webマーケティング初心者"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              競合URL
            </label>
            {competitorUrls.map((url, index) => (
              <div key={index} className="flex gap-2 mb-2">
                <input
                  type="url"
                  value={url}
                  onChange={(e) => updateCompetitorUrl(index, e.target.value)}
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
                  placeholder="https://example.com/article"
                />
                <button
                  type="button"
                  onClick={() => removeCompetitorUrl(index)}
                  className="px-3 py-2 text-gray-400 hover:text-red-500 transition-colors"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
            ))}
            <button
              type="button"
              onClick={addCompetitorUrl}
              className="inline-flex items-center gap-1 text-sm text-primary-600 hover:text-primary-700"
            >
              <Plus className="h-4 w-4" />
              URLを追加
            </button>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              追加要件
            </label>
            <textarea
              {...register('additional_requirements')}
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="追加の要件や注意点があれば記載してください"
            />
          </div>
        </div>
      </section>

      {/* モデル設定 */}
      <section className="bg-white rounded-lg border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">モデル設定</h2>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              プラットフォーム
            </label>
            <div className="flex gap-2">
              {(['gemini', 'openai', 'anthropic'] as LLMPlatform[]).map((p) => (
                <button
                  key={p}
                  type="button"
                  onClick={() => handlePlatformChange(p)}
                  className={cn(
                    'px-4 py-2 text-sm font-medium rounded-md transition-colors',
                    platform === p
                      ? 'bg-primary-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  )}
                >
                  {p.charAt(0).toUpperCase() + p.slice(1)}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              モデル
            </label>
            <select
              {...register('model')}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              {PLATFORM_MODELS[platform].map((model) => (
                <option key={model} value={model}>
                  {model}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                {...register('grounding')}
                className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
              />
              <span className="text-sm text-gray-700">Grounding有効</span>
            </label>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Temperature: {watch('temperature')}
            </label>
            <input
              type="range"
              min="0"
              max="2"
              step="0.1"
              {...register('temperature', { valueAsNumber: true })}
              className="w-full"
            />
          </div>
        </div>
      </section>

      {/* ツール設定 */}
      <section className="bg-white rounded-lg border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">ツール設定</h2>

        <div className="grid grid-cols-2 gap-4">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              {...register('serp_fetch')}
              className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
            />
            <span className="text-sm text-gray-700">SERP取得</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              {...register('page_fetch')}
              className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
            />
            <span className="text-sm text-gray-700">ページ取得</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              {...register('url_verify')}
              className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
            />
            <span className="text-sm text-gray-700">URL検証</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              {...register('pdf_extract')}
              className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
            />
            <span className="text-sm text-gray-700">PDF抽出</span>
          </label>
        </div>
      </section>

      {/* 実行オプション */}
      <section className="bg-white rounded-lg border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">実行オプション</h2>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              リトライ上限
            </label>
            <input
              type="number"
              min="1"
              max="10"
              {...register('retry_limit', { valueAsNumber: true })}
              className="w-24 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>

          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              {...register('repair_enabled')}
              className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
            />
            <span className="text-sm text-gray-700">決定的修正を有効にする</span>
          </label>
        </div>
      </section>

      {/* 送信ボタン */}
      <div className="flex justify-end gap-4">
        <a
          href="/runs"
          className="px-6 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
        >
          キャンセル
        </a>
        <button
          type="submit"
          disabled={submitting}
          className="px-6 py-2 text-sm font-medium text-white bg-primary-600 rounded-md hover:bg-primary-700 disabled:opacity-50 transition-colors"
        >
          {submitting ? '作成中...' : 'Run作成'}
        </button>
      </div>
    </form>
  );
}
