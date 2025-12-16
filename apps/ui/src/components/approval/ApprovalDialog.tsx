'use client';

import { useState, useEffect, useRef } from 'react';
import { CheckCircle, XCircle, X, Loader2, ArrowLeft, ShieldCheck, ShieldX } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ApprovalDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onApprove: () => Promise<void>;
  onReject: (reason: string) => Promise<void>;
  runId: string;
}

type DialogMode = 'select' | 'approve' | 'reject';

export function ApprovalDialog({
  isOpen,
  onClose,
  onApprove,
  onReject,
  runId,
}: ApprovalDialogProps) {
  const [mode, setMode] = useState<DialogMode>('select');
  const [rejectReason, setRejectReason] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    if (isOpen) {
      dialog.showModal();
      document.body.style.overflow = 'hidden';
    } else {
      dialog.close();
      document.body.style.overflow = '';
    }

    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    const handleCancel = (e: Event) => {
      e.preventDefault();
      setMode('select');
      setRejectReason('');
      setError(null);
      onClose();
    };

    dialog.addEventListener('cancel', handleCancel);
    return () => dialog.removeEventListener('cancel', handleCancel);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [onClose]);

  const handleApprove = async () => {
    setLoading(true);
    setError(null);
    try {
      await onApprove();
      handleClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : '承認に失敗しました');
    } finally {
      setLoading(false);
    }
  };

  const handleReject = async () => {
    if (!rejectReason.trim()) {
      setError('却下理由を入力してください');
      return;
    }

    setLoading(true);
    setError(null);
    try {
      await onReject(rejectReason);
      handleClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : '却下に失敗しました');
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setMode('select');
    setRejectReason('');
    setError(null);
    onClose();
  };

  const handleBackdropClick = (e: React.MouseEvent<HTMLDialogElement>) => {
    if (e.target === dialogRef.current) {
      handleClose();
    }
  };

  return (
    <dialog
      ref={dialogRef}
      className="fixed inset-0 z-50 bg-transparent p-0 m-0 max-w-none max-h-none w-full h-full"
      onClick={handleBackdropClick}
    >
      <div className="fixed inset-0 flex items-center justify-center p-4">
        <div className="card w-full max-w-md shadow-soft-lg animate-scale-in overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between p-5 border-b border-gray-100">
            <div className="flex items-center gap-3">
              {mode !== 'select' && (
                <button
                  onClick={() => setMode('select')}
                  className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-all"
                >
                  <ArrowLeft className="h-4 w-4" />
                </button>
              )}
              <h2 className="text-lg font-semibold text-gray-900">
                {mode === 'select' && '承認確認'}
                {mode === 'approve' && '承認の確認'}
                {mode === 'reject' && '却下の確認'}
              </h2>
            </div>
            <button
              onClick={handleClose}
              className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-all"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Content */}
          <div className="p-5">
            {mode === 'select' && (
              <SelectMode onApprove={() => setMode('approve')} onReject={() => setMode('reject')} />
            )}

            {mode === 'approve' && (
              <ApproveMode
                loading={loading}
                error={error}
                onConfirm={handleApprove}
                onCancel={() => setMode('select')}
              />
            )}

            {mode === 'reject' && (
              <RejectMode
                reason={rejectReason}
                setReason={setRejectReason}
                loading={loading}
                error={error}
                onConfirm={handleReject}
                onCancel={() => setMode('select')}
              />
            )}
          </div>
        </div>
      </div>
    </dialog>
  );
}

function SelectMode({
  onApprove,
  onReject,
}: {
  onApprove: () => void;
  onReject: () => void;
}) {
  return (
    <div className="space-y-4">
      <p className="text-sm text-gray-600 text-center">
        このRunの承認処理を選択してください
      </p>

      <div className="grid grid-cols-2 gap-3">
        <button
          onClick={onApprove}
          className="group flex flex-col items-center gap-3 p-5 bg-white border-2 border-gray-200 rounded-xl hover:border-success-300 hover:bg-success-50 transition-all"
        >
          <div className="p-3 rounded-xl bg-success-100 text-success-600 group-hover:scale-110 transition-transform">
            <ShieldCheck className="h-6 w-6" />
          </div>
          <span className="text-sm font-semibold text-gray-900 group-hover:text-success-700">
            承認
          </span>
        </button>

        <button
          onClick={onReject}
          className="group flex flex-col items-center gap-3 p-5 bg-white border-2 border-gray-200 rounded-xl hover:border-error-300 hover:bg-error-50 transition-all"
        >
          <div className="p-3 rounded-xl bg-error-100 text-error-600 group-hover:scale-110 transition-transform">
            <ShieldX className="h-6 w-6" />
          </div>
          <span className="text-sm font-semibold text-gray-900 group-hover:text-error-700">
            却下
          </span>
        </button>
      </div>
    </div>
  );
}

function ApproveMode({
  loading,
  error,
  onConfirm,
  onCancel,
}: {
  loading: boolean;
  error: string | null;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="space-y-4">
      <div className="flex justify-center">
        <div className="p-4 rounded-2xl bg-success-100">
          <CheckCircle className="h-10 w-10 text-success-600" />
        </div>
      </div>

      <div className="text-center">
        <p className="text-gray-600">
          このRunを承認して後続の工程を開始しますか？
        </p>
      </div>

      {error && (
        <div className="p-3 bg-error-50 border border-error-200 rounded-lg">
          <p className="text-sm text-error-700">{error}</p>
        </div>
      )}

      <div className="flex gap-3">
        <button
          onClick={onCancel}
          disabled={loading}
          className="btn btn-secondary flex-1"
        >
          戻る
        </button>
        <button
          onClick={onConfirm}
          disabled={loading}
          className="btn btn-primary flex-1 bg-success-600 hover:bg-success-700"
        >
          {loading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              処理中...
            </>
          ) : (
            <>
              <CheckCircle className="h-4 w-4" />
              承認する
            </>
          )}
        </button>
      </div>
    </div>
  );
}

function RejectMode({
  reason,
  setReason,
  loading,
  error,
  onConfirm,
  onCancel,
}: {
  reason: string;
  setReason: (reason: string) => void;
  loading: boolean;
  error: string | null;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="space-y-4">
      <div className="flex justify-center">
        <div className="p-4 rounded-2xl bg-error-100">
          <XCircle className="h-10 w-10 text-error-600" />
        </div>
      </div>

      <div className="text-center">
        <p className="text-gray-600">
          このRunを却下します。却下理由を入力してください。
        </p>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          却下理由 <span className="text-error-500">*</span>
        </label>
        <textarea
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          rows={3}
          className="input resize-none"
          placeholder="却下の理由を入力してください..."
        />
      </div>

      {error && (
        <div className="p-3 bg-error-50 border border-error-200 rounded-lg">
          <p className="text-sm text-error-700">{error}</p>
        </div>
      )}

      <div className="flex gap-3">
        <button
          onClick={onCancel}
          disabled={loading}
          className="btn btn-secondary flex-1"
        >
          戻る
        </button>
        <button
          onClick={onConfirm}
          disabled={loading}
          className="btn btn-danger flex-1"
        >
          {loading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              処理中...
            </>
          ) : (
            <>
              <XCircle className="h-4 w-4" />
              却下する
            </>
          )}
        </button>
      </div>
    </div>
  );
}
