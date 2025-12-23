"use client";

import { useState } from "react";
import { HearingTemplateData } from "@/lib/types";
import { api } from "@/lib/api";

interface SaveTemplateModalProps {
  isOpen: boolean;
  onClose: () => void;
  templateData: HearingTemplateData;
  onSaveSuccess: () => void;
}

export function SaveTemplateModal({
  isOpen,
  onClose,
  templateData,
  onSaveSuccess,
}: SaveTemplateModalProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!name.trim()) {
      setError("テンプレート名を入力してください");
      return;
    }

    setIsSaving(true);
    setError(null);

    try {
      await api.hearingTemplates.create({
        name: name.trim(),
        description: description.trim() || undefined,
        data: templateData,
      });
      onSaveSuccess();
      onClose();
      // Reset form
      setName("");
      setDescription("");
    } catch (err) {
      console.error("Failed to save template:", err);
      if (err instanceof Error) {
        if (err.message.includes("already exists")) {
          setError("同じ名前のテンプレートが既に存在します");
        } else {
          setError(err.message);
        }
      } else {
        setError("テンプレートの保存に失敗しました");
      }
    } finally {
      setIsSaving(false);
    }
  };

  const handleClose = () => {
    if (!isSaving) {
      setError(null);
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
        onClick={handleClose}
      />

      {/* Modal */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div className="relative bg-white rounded-lg shadow-xl max-w-md w-full p-6">
          {/* Header */}
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">
              テンプレートとして保存
            </h3>
            <button
              type="button"
              onClick={handleClose}
              disabled={isSaving}
              className="text-gray-400 hover:text-gray-600 disabled:cursor-not-allowed"
            >
              <svg
                className="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>

          {/* Form */}
          <form onSubmit={handleSave}>
            <div className="space-y-4">
              {/* Name */}
              <div>
                <label
                  htmlFor="template-name"
                  className="block text-sm font-medium text-gray-700 mb-1"
                >
                  テンプレート名 <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  id="template-name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="例: 派遣社員向けeラーニング記事"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  disabled={isSaving}
                  autoFocus
                />
              </div>

              {/* Description */}
              <div>
                <label
                  htmlFor="template-description"
                  className="block text-sm font-medium text-gray-700 mb-1"
                >
                  説明（任意）
                </label>
                <textarea
                  id="template-description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="このテンプレートの用途を記入"
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                  disabled={isSaving}
                />
              </div>

              {/* Error */}
              {error && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-md">
                  <p className="text-sm text-red-600">{error}</p>
                </div>
              )}

              {/* Preview Summary */}
              <div className="p-3 bg-gray-50 border border-gray-200 rounded-md">
                <p className="text-xs font-medium text-gray-500 uppercase mb-2">
                  保存される内容
                </p>
                <ul className="text-sm text-gray-600 space-y-1">
                  <li>
                    <span className="font-medium">事業内容:</span>{" "}
                    {templateData.business.description.substring(0, 30)}
                    {templateData.business.description.length > 30 ? "..." : ""}
                  </li>
                  <li>
                    <span className="font-medium">キーワード:</span>{" "}
                    {templateData.keyword.main_keyword ||
                      templateData.keyword.theme_topics?.substring(0, 20) ||
                      "未設定"}
                  </li>
                  <li>
                    <span className="font-medium">記事スタイル:</span>{" "}
                    {templateData.strategy.article_style === "standalone"
                      ? "スタンドアロン"
                      : "トピッククラスター"}
                  </li>
                </ul>
              </div>
            </div>

            {/* Actions */}
            <div className="mt-6 flex justify-end gap-3">
              <button
                type="button"
                onClick={handleClose}
                disabled={isSaving}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md disabled:cursor-not-allowed transition-colors"
              >
                キャンセル
              </button>
              <button
                type="submit"
                disabled={isSaving || !name.trim()}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
              >
                {isSaving ? (
                  <span className="flex items-center gap-2">
                    <span className="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    保存中...
                  </span>
                ) : (
                  "保存"
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
