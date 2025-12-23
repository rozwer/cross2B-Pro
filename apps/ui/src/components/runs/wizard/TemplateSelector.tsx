"use client";

import { useState, useEffect, useCallback } from "react";
import { HearingTemplate, HearingTemplateData } from "@/lib/types";
import { api } from "@/lib/api";

interface TemplateSelectorProps {
  onSelectTemplate: (template: HearingTemplate | null) => void;
  onSaveAsTemplate: () => void;
  currentData: HearingTemplateData;
  hasUnsavedChanges: boolean;
}

export function TemplateSelector({
  onSelectTemplate,
  onSaveAsTemplate,
  currentData: _currentData,
  hasUnsavedChanges,
}: TemplateSelectorProps) {
  // _currentData is reserved for future use (e.g., template comparison)
  void _currentData;
  const [templates, setTemplates] = useState<HearingTemplate[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>("");

  // Load templates on mount
  useEffect(() => {
    loadTemplates();
  }, []);

  const loadTemplates = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await api.hearingTemplates.list({ limit: 100 });
      setTemplates(response.items);
    } catch (err) {
      console.error("Failed to load templates:", err);
      setError("テンプレートの読み込みに失敗しました");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectTemplate = useCallback(
    (e: React.ChangeEvent<HTMLSelectElement>) => {
      const templateId = e.target.value;
      setSelectedTemplateId(templateId);

      if (!templateId) {
        onSelectTemplate(null);
        return;
      }

      const template = templates.find((t) => t.id === templateId);
      if (template) {
        onSelectTemplate(template);
      }
    },
    [templates, onSelectTemplate]
  );

  return (
    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        {/* Template Selector */}
        <div className="flex-1">
          <label
            htmlFor="template-select"
            className="block text-sm font-medium text-blue-900 mb-1"
          >
            テンプレートから開始
          </label>
          <div className="flex items-center gap-2">
            <select
              id="template-select"
              value={selectedTemplateId}
              onChange={handleSelectTemplate}
              disabled={isLoading}
              className="flex-1 px-3 py-2 border border-blue-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
            >
              <option value="">新規入力（テンプレートなし）</option>
              {templates.map((template) => (
                <option key={template.id} value={template.id}>
                  {template.name}
                  {template.description ? ` - ${template.description}` : ""}
                </option>
              ))}
            </select>
            <button
              type="button"
              onClick={loadTemplates}
              disabled={isLoading}
              className="px-3 py-2 text-sm text-blue-600 hover:text-blue-800 disabled:text-gray-400"
              title="テンプレートを再読み込み"
            >
              {isLoading ? (
                <span className="inline-block w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
              ) : (
                <svg
                  className="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                  />
                </svg>
              )}
            </button>
          </div>
          {error && <p className="mt-1 text-sm text-red-600">{error}</p>}
        </div>

        {/* Save as Template Button */}
        <div className="flex-shrink-0">
          <button
            type="button"
            onClick={onSaveAsTemplate}
            disabled={!hasUnsavedChanges}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
          >
            テンプレートとして保存
          </button>
        </div>
      </div>

      {templates.length === 0 && !isLoading && !error && (
        <p className="mt-2 text-sm text-blue-700">
          保存済みのテンプレートはありません。入力後「テンプレートとして保存」で再利用できます。
        </p>
      )}
    </div>
  );
}
