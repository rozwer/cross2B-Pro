"use client";

import { useState, useCallback, useMemo, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  ArticleHearingInput,
  BusinessInput,
  KeywordInput,
  StrategyInput,
  WordCountInput,
  CTAInput,
  ModelConfig,
  StepModelConfig,
  ToolConfig,
  KeywordSuggestion,
  HearingTemplate,
  HearingTemplateData,
  ServiceConfig,
} from "@/lib/types";
import { api } from "@/lib/api";
import { WizardProgress } from "./WizardProgress";
import { WizardNavigation } from "./WizardNavigation";
import { TemplateSelector } from "./TemplateSelector";
import { SaveTemplateModal } from "./SaveTemplateModal";
import { TemplateManagerModal } from "./TemplateManagerModal";
import { Step1Business } from "./steps/Step1Business";
import { Step2Keyword } from "./steps/Step2Keyword";
import { Step3Strategy } from "./steps/Step3Strategy";
import { Step4WordCount } from "./steps/Step4WordCount";
import { Step5CTA } from "./steps/Step5CTA";
import { Step6Confirm } from "./steps/Step6Confirm";

const WIZARD_STEPS = [
  { id: 1, label: "事業内容", description: "事業内容とターゲット" },
  { id: 2, label: "キーワード", description: "キーワード選定" },
  { id: 3, label: "記事戦略", description: "記事のスタイル" },
  { id: 4, label: "文字数", description: "文字数設定" },
  { id: 5, label: "CTA", description: "CTA設定" },
  { id: 6, label: "確認", description: "最終確認" },
];

// Default values for each section
const DEFAULT_BUSINESS: BusinessInput = {
  description: "",
  target_cv: "inquiry",
  target_audience: "",
  company_strengths: "",
};

const DEFAULT_KEYWORD: KeywordInput = {
  status: "undecided",
};

const DEFAULT_STRATEGY: StrategyInput = {
  article_style: "standalone",
};

const DEFAULT_WORD_COUNT: WordCountInput = {
  mode: "ai_balanced",
};

const DEFAULT_CTA: CTAInput = {
  type: "single",
  position_mode: "fixed",
  single: {
    url: "https://cross-learning.jp/",
    text: "クロスラーニングの詳細を見る",
    description: "クロスラーニング広報サイトのTOPページ",
  },
};

interface WizardFormData {
  business: BusinessInput;
  keyword: KeywordInput;
  strategy: StrategyInput;
  word_count: WordCountInput;
  cta: CTAInput;
  confirmed: boolean;
  // GitHub integration (Phase 2)
  github_repo_url: string;
  // Execution options
  enable_step1_approval: boolean;
}

interface RunCreateWizardProps {
  modelConfig: ModelConfig;
  stepConfigs?: StepModelConfig[];
  toolConfig?: ToolConfig;
  options?: {
    retry_limit?: number;
    repair_enabled?: boolean;
    enable_step1_approval?: boolean;
  };
}

export function RunCreateWizard({
  modelConfig,
  stepConfigs,
  toolConfig,
  options,
}: RunCreateWizardProps) {
  const router = useRouter();
  const [currentStep, setCurrentStep] = useState(1);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // Form state
  const [formData, setFormData] = useState<WizardFormData>({
    business: DEFAULT_BUSINESS,
    keyword: DEFAULT_KEYWORD,
    strategy: DEFAULT_STRATEGY,
    word_count: DEFAULT_WORD_COUNT,
    cta: DEFAULT_CTA,
    confirmed: false,
    github_repo_url: "",
    enable_step1_approval: options?.enable_step1_approval ?? true,
  });

  // Load GitHub repo URL on mount
  // Priority: 1. Recent run's github_repo_url, 2. Default settings, 3. Empty
  useEffect(() => {
    const loadGitHubRepoUrl = async () => {
      try {
        // First, try to get github_repo_url from the most recent run
        const runsResponse = await api.runs.list({ limit: 10 });
        if (runsResponse.items.length > 0) {
          // Find the first run with a github_repo_url by fetching details
          for (const runSummary of runsResponse.items) {
            try {
              const run = await api.runs.get(runSummary.id);
              if (run.github_repo_url) {
                setFormData((prev) => ({
                  ...prev,
                  github_repo_url: run.github_repo_url || "",
                }));
                return; // Found a recent repo URL, done
              }
            } catch {
              // Skip this run if we can't fetch it
              continue;
            }
          }
        }

        // Fallback: try default settings if no recent run has github_repo_url
        const response = await api.settings.get("github");
        const config = response.config as ServiceConfig | null;
        if (config?.default_repo_url) {
          setFormData((prev) => ({
            ...prev,
            github_repo_url: config.default_repo_url || "",
          }));
        }
      } catch {
        // Ignore errors - settings are optional
      }
    };
    loadGitHubRepoUrl();
  }, []);

  // Keyword suggestions state
  const [keywordSuggestions, setKeywordSuggestions] = useState<KeywordSuggestion[] | null>(null);
  const [isLoadingSuggestions, setIsLoadingSuggestions] = useState(false);

  // Validation errors per step
  const [validationErrors, setValidationErrors] = useState<Record<number, string[]>>({});

  // Template state
  const [loadedTemplate, setLoadedTemplate] = useState<HearingTemplate | null>(null);
  const [showSaveTemplateModal, setShowSaveTemplateModal] = useState(false);
  const [showTemplateManager, setShowTemplateManager] = useState(false);
  const [templateRefreshKey, setTemplateRefreshKey] = useState(0);

  const refreshTemplates = useCallback(() => {
    setTemplateRefreshKey((prev) => prev + 1);
  }, []);

  // Update a specific section of form data
  const updateFormData = useCallback(<K extends keyof WizardFormData>(
    section: K,
    data: Partial<WizardFormData[K]>
  ) => {
    setFormData((prev) => ({
      ...prev,
      [section]: {
        ...(prev[section] as object),
        ...data,
      },
    }));
  }, []);

  // Validate current step
  const validateStep = useCallback((step: number): string[] => {
    const errors: string[] = [];

    switch (step) {
      case 1: // Business
        if (!formData.business.description || formData.business.description.length < 10) {
          errors.push("事業内容は10文字以上で入力してください");
        }
        if (!formData.business.target_audience || formData.business.target_audience.length < 10) {
          errors.push("ターゲット読者は10文字以上で入力してください");
        }
        if (!formData.business.company_strengths || formData.business.company_strengths.length < 10) {
          errors.push("自社の強みは10文字以上で入力してください");
        }
        if (formData.business.target_cv === "other" && !formData.business.target_cv_other) {
          errors.push("その他のCV目標を入力してください");
        }
        break;

      case 2: // Keyword
        if (formData.keyword.status === "decided") {
          if (!formData.keyword.main_keyword) {
            errors.push("メインキーワードを入力してください");
          }
        } else {
          if (!formData.keyword.selected_keyword && !formData.keyword.theme_topics) {
            errors.push("テーマを入力するか、キーワード候補を選択してください");
          }
        }
        break;

      case 3: // Strategy
        if (formData.strategy.article_style === "topic_cluster") {
          if (!formData.strategy.child_topics || formData.strategy.child_topics.length === 0) {
            errors.push("トピッククラスター戦略の場合、子記事トピックを入力してください");
          }
        }
        break;

      case 4: // Word Count
        if (formData.word_count.mode === "manual") {
          if (!formData.word_count.target || formData.word_count.target < 1000) {
            errors.push("文字数は1000以上で指定してください");
          }
        }
        break;

      case 5: // CTA
        if (formData.cta.type === "single") {
          if (!formData.cta.single?.url || !formData.cta.single?.text) {
            errors.push("CTA URL と テキストを入力してください");
          }
        } else {
          if (!formData.cta.staged?.early?.url || !formData.cta.staged?.mid?.url || !formData.cta.staged?.final?.url) {
            errors.push("すべてのCTA（Early/Mid/Final）の情報を入力してください");
          }
        }
        break;

      case 6: // Confirm
        if (!formData.confirmed) {
          errors.push("内容を確認してチェックを入れてください");
        }
        break;
    }

    return errors;
  }, [formData]);

  // Go to next step
  const handleNext = useCallback(() => {
    const errors = validateStep(currentStep);
    if (errors.length > 0) {
      setValidationErrors((prev) => ({ ...prev, [currentStep]: errors }));
      return;
    }

    setValidationErrors((prev) => ({ ...prev, [currentStep]: [] }));
    setCurrentStep((prev) => Math.min(prev + 1, WIZARD_STEPS.length));
  }, [currentStep, validateStep]);

  // Go to previous step
  const handleBack = useCallback(() => {
    setCurrentStep((prev) => Math.max(prev - 1, 1));
  }, []);

  // Generate keyword suggestions
  const handleGenerateKeywords = useCallback(async () => {
    if (!formData.keyword.theme_topics || formData.keyword.theme_topics.length < 10) {
      setValidationErrors((prev) => ({
        ...prev,
        2: ["テーマは10文字以上で入力してください"],
      }));
      return;
    }

    setIsLoadingSuggestions(true);
    // Clear previous suggestion errors
    setValidationErrors((prev) => ({
      ...prev,
      2: [],
    }));

    try {
      const response = await api.keywords.suggest({
        theme_topics: formData.keyword.theme_topics,
        business_description: formData.business.description,
        target_audience: formData.business.target_audience,
      });
      setKeywordSuggestions(response.suggestions);
    } catch (error) {
      console.error("Failed to generate keywords:", error);
      const errorMessage =
        error instanceof Error
          ? `キーワード候補の生成に失敗しました: ${error.message}`
          : "キーワード候補の生成に失敗しました。しばらくしてから再試行してください。";
      setValidationErrors((prev) => ({
        ...prev,
        2: [errorMessage],
      }));
    } finally {
      setIsLoadingSuggestions(false);
    }
  }, [formData.keyword.theme_topics, formData.business.description, formData.business.target_audience]);

  // Select a keyword from suggestions
  const handleSelectKeyword = useCallback((suggestion: KeywordSuggestion) => {
    updateFormData("keyword", {
      selected_keyword: {
        keyword: suggestion.keyword,
        estimated_volume: suggestion.estimated_volume,
        estimated_competition: suggestion.estimated_competition,
        relevance_score: suggestion.relevance_score,
      },
    });
  }, [updateFormData]);

  // Handle template selection
  const handleSelectTemplate = useCallback((template: HearingTemplate | null) => {
    setLoadedTemplate(template);
    if (template) {
      // Load template data into form
      setFormData({
        business: template.data.business,
        keyword: template.data.keyword,
        strategy: template.data.strategy,
        word_count: template.data.word_count,
        cta: template.data.cta,
        confirmed: false, // Always reset confirmation
        github_repo_url: "", // Reset GitHub repo on template load
        enable_step1_approval: options?.enable_step1_approval ?? true, // Reset to default
      });
      // Clear any validation errors
      setValidationErrors({});
    }
  }, []);

  // Get current template data (for saving)
  const currentTemplateData: HearingTemplateData = useMemo(() => ({
    business: formData.business,
    keyword: formData.keyword,
    strategy: formData.strategy,
    word_count: formData.word_count,
    cta: formData.cta,
  }), [formData]);

  // Check if form has meaningful data to save
  const hasUnsavedChanges: boolean = useMemo(() => {
    // Check if there's any meaningful data entered
    return Boolean(
      formData.business.description.length > 0 ||
      formData.business.target_audience.length > 0 ||
      formData.keyword.main_keyword ||
      formData.keyword.theme_topics ||
      formData.keyword.selected_keyword
    );
  }, [formData]);

  // Submit the form
  const handleSubmit = useCallback(async () => {
    // Validate all steps
    const allErrors: string[] = [];
    for (let step = 1; step <= WIZARD_STEPS.length; step++) {
      allErrors.push(...validateStep(step));
    }

    if (allErrors.length > 0) {
      setSubmitError(allErrors.join(", "));
      return;
    }

    setIsSubmitting(true);
    setSubmitError(null);

    try {
      const input: ArticleHearingInput = {
        format_type: "article_hearing_v1",  // Required for discriminated union
        business: formData.business,
        keyword: formData.keyword,
        strategy: formData.strategy,
        word_count: formData.word_count,
        cta: formData.cta,
        confirmed: formData.confirmed,
      };

      // Normalize step_ids: convert dots to underscores (step6.5 -> step6_5)
      const normalizedStepConfigs = stepConfigs?.map((sc) => ({
        ...sc,
        step_id: sc.step_id.replace(/\./g, "_"),
      }));

      const run = await api.runs.create({
        input,
        model_config: modelConfig,
        step_configs: normalizedStepConfigs,
        tool_config: toolConfig,
        options: {
          ...options,
          enable_step1_approval: formData.enable_step1_approval,
        },
        // GitHub integration (Phase 2) - only send if set
        github_repo_url: formData.github_repo_url || undefined,
      });

      // Navigate to the run detail page
      router.push(`/runs/${run.id}`);
    } catch (error) {
      console.error("Failed to create run:", error);
      setSubmitError(error instanceof Error ? error.message : "ランの作成に失敗しました");
    } finally {
      setIsSubmitting(false);
    }
  }, [formData, modelConfig, stepConfigs, toolConfig, options, validateStep, router]);

  // Render current step content
  const renderStepContent = () => {
    switch (currentStep) {
      case 1:
        return (
          <Step1Business
            data={formData.business}
            onChange={(data) => updateFormData("business", data)}
            errors={validationErrors[1] || []}
          />
        );
      case 2:
        return (
          <Step2Keyword
            data={formData.keyword}
            onChange={(data) => updateFormData("keyword", data)}
            suggestions={keywordSuggestions}
            isLoadingSuggestions={isLoadingSuggestions}
            onGenerateSuggestions={handleGenerateKeywords}
            onSelectKeyword={handleSelectKeyword}
            businessDescription={formData.business.description}
            errors={validationErrors[2] || []}
          />
        );
      case 3:
        return (
          <Step3Strategy
            data={formData.strategy}
            onChange={(data) => updateFormData("strategy", data)}
            mainKeyword={formData.keyword.main_keyword || formData.keyword.selected_keyword?.keyword || ""}
            businessDescription={formData.business.description}
            targetAudience={formData.business.target_audience}
            errors={validationErrors[3] || []}
          />
        );
      case 4:
        return (
          <Step4WordCount
            data={formData.word_count}
            onChange={(data) => updateFormData("word_count", data)}
            articleStyle={formData.strategy.article_style}
            errors={validationErrors[4] || []}
          />
        );
      case 5:
        return (
          <Step5CTA
            data={formData.cta}
            onChange={(data) => updateFormData("cta", data)}
            errors={validationErrors[5] || []}
          />
        );
      case 6:
        return (
          <Step6Confirm
            formData={formData}
            onConfirm={(confirmed: boolean) => setFormData((prev) => ({ ...prev, confirmed }))}
            onGitHubRepoChange={(repoUrl: string) => setFormData((prev) => ({ ...prev, github_repo_url: repoUrl }))}
            onStep1ApprovalChange={(enabled: boolean) => setFormData((prev) => ({ ...prev, enable_step1_approval: enabled }))}
            errors={validationErrors[6] || []}
          />
        );
      default:
        return null;
    }
  };

  return (
    <div className="max-w-4xl mx-auto">
      {/* Template Selector (only on first step) */}
      {currentStep === 1 && (
        <TemplateSelector
          onSelectTemplate={handleSelectTemplate}
          onSaveAsTemplate={() => setShowSaveTemplateModal(true)}
          onManageTemplates={() => setShowTemplateManager(true)}
          currentData={currentTemplateData}
          hasUnsavedChanges={hasUnsavedChanges}
          refreshKey={templateRefreshKey}
        />
      )}

      {/* Loaded Template Indicator */}
      {loadedTemplate && currentStep === 1 && (
        <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-md flex items-center justify-between">
          <div className="flex items-center gap-2">
            <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span className="text-sm text-green-800">
              テンプレート「{loadedTemplate.name}」を読み込みました
            </span>
          </div>
          <button
            type="button"
            onClick={() => setLoadedTemplate(null)}
            className="text-xs text-green-600 hover:text-green-800"
          >
            クリア
          </button>
        </div>
      )}

      {/* Progress Bar */}
      <WizardProgress steps={WIZARD_STEPS} currentStep={currentStep} />

      {/* Step Content */}
      <div className="mt-8 bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-6">
          {WIZARD_STEPS[currentStep - 1].label}
        </h2>
        <p className="text-sm text-gray-500 mb-6">
          {WIZARD_STEPS[currentStep - 1].description}
        </p>

        {renderStepContent()}

        {/* Submit Error */}
        {submitError && (
          <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-md">
            <p className="text-sm text-red-600">{submitError}</p>
          </div>
        )}
      </div>

      {/* Navigation */}
      <WizardNavigation
        currentStep={currentStep}
        totalSteps={WIZARD_STEPS.length}
        onBack={handleBack}
        onNext={handleNext}
        onSubmit={handleSubmit}
        isSubmitting={isSubmitting}
        canSubmit={formData.confirmed}
      />

      {/* Save Template Modal */}
      <SaveTemplateModal
        isOpen={showSaveTemplateModal}
        onClose={() => setShowSaveTemplateModal(false)}
        templateData={currentTemplateData}
        onSaveSuccess={() => {
          refreshTemplates();
          console.log("Template saved successfully");
        }}
      />

      <TemplateManagerModal
        isOpen={showTemplateManager}
        onClose={() => setShowTemplateManager(false)}
        onTemplatesChanged={refreshTemplates}
      />
    </div>
  );
}
