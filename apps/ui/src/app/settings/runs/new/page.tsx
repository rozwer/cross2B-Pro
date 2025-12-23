"use client";

import { useState, useEffect } from "react";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { RunCreateForm } from "@/components/runs/RunCreateForm";
import { RunCreateWizard } from "@/components/runs/wizard";
import { WORKFLOW_STEPS, type StepConfig } from "@/components/workflow";
import type { ModelConfig, StepModelConfig, ToolConfig } from "@/lib/types";

type FormMode = "wizard" | "legacy";

export default function NewRunPage() {
  const [formMode, setFormMode] = useState<FormMode>("wizard");
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

  // Build model config from step configs
  const configurableSteps = stepConfigs.filter(
    (s) => s.isConfigurable && s.stepId !== "approval"
  );
  const firstStep = configurableSteps[0] || stepConfigs[0];

  const modelConfig: ModelConfig = {
    platform: firstStep.aiModel,
    model: firstStep.modelName,
    options: {
      grounding: firstStep.grounding,
      temperature: firstStep.temperature,
    },
  };

  const stepConfigsPayload: StepModelConfig[] | undefined =
    configurableSteps.length > 0
      ? configurableSteps.map((step) => ({
          step_id: step.stepId,
          platform: step.aiModel,
          model: step.modelName,
          temperature: step.temperature,
          grounding: step.grounding,
          retry_limit: step.retryLimit,
          repair_enabled: step.repairEnabled,
        }))
      : undefined;

  const toolConfig: ToolConfig = {
    serp_fetch: true,
    page_fetch: true,
    url_verify: true,
    pdf_extract: false,
  };

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <Link
          href="/settings"
          className="inline-flex items-center gap-1.5 text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 mb-4"
        >
          <ArrowLeft className="w-4 h-4" />
          設定に戻る
        </Link>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-gray-900 dark:text-gray-100">
              新規Run作成
            </h1>
            <p className="text-gray-500 dark:text-gray-400 mt-1">
              SEO記事生成の設定を入力してください
            </p>
          </div>

          {/* Form Mode Toggle */}
          <div className="flex items-center gap-2 bg-gray-100 dark:bg-gray-800 rounded-lg p-1">
            <button
              type="button"
              onClick={() => setFormMode("wizard")}
              className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                formMode === "wizard"
                  ? "bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm"
                  : "text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
              }`}
            >
              詳細入力
            </button>
            <button
              type="button"
              onClick={() => setFormMode("legacy")}
              className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                formMode === "legacy"
                  ? "bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm"
                  : "text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
              }`}
            >
              簡易入力
            </button>
          </div>
        </div>
      </div>

      {/* Form */}
      {formMode === "wizard" ? (
        <RunCreateWizard
          modelConfig={modelConfig}
          stepConfigs={stepConfigsPayload}
          toolConfig={toolConfig}
          options={{ retry_limit: 3, repair_enabled: true }}
        />
      ) : (
        <div className="max-w-3xl">
          <RunCreateForm />
        </div>
      )}
    </div>
  );
}
