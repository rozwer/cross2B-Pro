"use client";

import { useCallback, useEffect, useState } from "react";
import { HearingTemplate } from "@/lib/types";
import { api } from "@/lib/api";

interface TemplateManagerModalProps {
  isOpen: boolean;
  onClose: () => void;
  onTemplatesChanged?: () => void;
}

export function TemplateManagerModal({
  isOpen,
  onClose,
  onTemplatesChanged,
}: TemplateManagerModalProps) {
  const [templates, setTemplates] = useState<HearingTemplate[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editTemplateId, setEditTemplateId] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [busyTemplateId, setBusyTemplateId] = useState<string | null>(null);
  const [busyAction, setBusyAction] = useState<"save" | "delete" | null>(null);

  const loadTemplates = useCallback(async () => {
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
  }, []);

  useEffect(() => {
    if (isOpen) {
      loadTemplates();
    }
  }, [isOpen, loadTemplates]);

  const startEdit = (template: HearingTemplate) => {
    setEditTemplateId(template.id);
    setEditName(template.name);
    setEditDescription(template.description || "");
    setError(null);
  };

  const cancelEdit = () => {
    setEditTemplateId(null);
    setEditName("");
    setEditDescription("");
    setError(null);
  };

  const handleSave = async (templateId: string) => {
    if (!editName.trim()) {
      setError("テンプレート名を入力してください");
      return;
    }

    setBusyTemplateId(templateId);
    setBusyAction("save");
    setError(null);

    try {
      await api.hearingTemplates.update(templateId, {
        name: editName.trim(),
        description: editDescription.trim() || undefined,
      });
      await loadTemplates();
      onTemplatesChanged?.();
      cancelEdit();
    } catch (err) {
      console.error("Failed to update template:", err);
      setError("テンプレートの更新に失敗しました");
    } finally {
      setBusyTemplateId(null);
      setBusyAction(null);
    }
  };

  const handleDelete = async (template: HearingTemplate) => {
    if (!confirm(`テンプレート「${template.name}」を削除しますか？`)) {
      return;
    }

    setBusyTemplateId(template.id);
    setBusyAction("delete");
    setError(null);

    try {
      await api.hearingTemplates.delete(template.id);
      if (editTemplateId === template.id) {
        cancelEdit();
      }
      await loadTemplates();
      onTemplatesChanged?.();
    } catch (err) {
      console.error("Failed to delete template:", err);
      setError("テンプレートの削除に失敗しました");
    } finally {
      setBusyTemplateId(null);
      setBusyAction(null);
    }
  };

  const handleClose = () => {
    if (!busyTemplateId) {
      cancelEdit();
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
        onClick={handleClose}
      />

      {/* Modal */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div className="relative bg-white rounded-lg shadow-xl max-w-2xl w-full p-6">
          {/* Header */}
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">テンプレート管理</h3>
            <button
              type="button"
              onClick={handleClose}
              disabled={!!busyTemplateId}
              className="text-gray-400 hover:text-gray-600 disabled:cursor-not-allowed"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm text-gray-500">テンプレートの名称や説明を編集・削除できます。</p>
            <button
              type="button"
              onClick={loadTemplates}
              disabled={isLoading}
              className="px-3 py-1.5 text-sm text-blue-600 hover:text-blue-800 disabled:text-gray-400"
            >
              {isLoading ? "読み込み中..." : "再読み込み"}
            </button>
          </div>

          {/* Error */}
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}

          {/* Template List */}
          <div className="space-y-3 max-h-[60vh] overflow-y-auto">
            {isLoading && (
              <div className="p-4 text-sm text-gray-500">テンプレートを読み込み中...</div>
            )}
            {!isLoading && templates.length === 0 && (
              <div className="p-4 text-sm text-gray-500">テンプレートがありません。</div>
            )}
            {!isLoading &&
              templates.map((template) => {
                const isEditing = editTemplateId === template.id;
                const isBusy = busyTemplateId === template.id;
                const updatedAt = template.updated_at
                  ? new Date(template.updated_at).toLocaleString()
                  : "不明";

                return (
                  <div key={template.id} className="border border-gray-200 rounded-md p-4">
                    {isEditing ? (
                      <div className="space-y-3">
                        <div>
                          <label className="block text-xs text-gray-500 mb-1">テンプレート名</label>
                          <input
                            type="text"
                            value={editName}
                            onChange={(e) => setEditName(e.target.value)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                            disabled={isBusy}
                          />
                        </div>
                        <div>
                          <label className="block text-xs text-gray-500 mb-1">説明（任意）</label>
                          <textarea
                            value={editDescription}
                            onChange={(e) => setEditDescription(e.target.value)}
                            rows={2}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm resize-none"
                            disabled={isBusy}
                          />
                        </div>
                        <div className="flex justify-end gap-2">
                          <button
                            type="button"
                            onClick={cancelEdit}
                            disabled={isBusy}
                            className="px-3 py-1.5 text-sm text-gray-600 hover:text-gray-800 disabled:cursor-not-allowed"
                          >
                            キャンセル
                          </button>
                          <button
                            type="button"
                            onClick={() => handleSave(template.id)}
                            disabled={isBusy}
                            className="px-4 py-1.5 text-sm text-white bg-blue-600 hover:bg-blue-700 rounded-md disabled:bg-gray-400"
                          >
                            {isBusy && busyAction === "save" ? "保存中..." : "保存"}
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
                        <div>
                          <p className="font-medium text-gray-900">{template.name}</p>
                          <p className="text-sm text-gray-600">
                            {template.description || "説明なし"}
                          </p>
                          <p className="text-xs text-gray-400 mt-1">更新: {updatedAt}</p>
                        </div>
                        <div className="flex gap-2">
                          <button
                            type="button"
                            onClick={() => startEdit(template)}
                            disabled={isBusy}
                            className="px-3 py-1.5 text-sm text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md disabled:cursor-not-allowed"
                          >
                            編集
                          </button>
                          <button
                            type="button"
                            onClick={() => handleDelete(template)}
                            disabled={isBusy}
                            className="px-3 py-1.5 text-sm text-red-600 bg-red-50 hover:bg-red-100 rounded-md disabled:cursor-not-allowed"
                          >
                            {isBusy && busyAction === "delete" ? "削除中..." : "削除"}
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
          </div>
        </div>
      </div>
    </div>
  );
}
