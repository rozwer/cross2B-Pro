'use client';

import { cn } from '@/lib/utils';

interface LoadingProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  text?: string;
  variant?: 'spinner' | 'dots' | 'pulse';
}

export function Loading({ size = 'md', className, text, variant = 'spinner' }: LoadingProps) {
  const sizeClasses = {
    sm: 'h-4 w-4',
    md: 'h-8 w-8',
    lg: 'h-12 w-12',
  };

  const textSizeClasses = {
    sm: 'text-xs',
    md: 'text-sm',
    lg: 'text-base',
  };

  return (
    <div className={cn('flex flex-col items-center justify-center gap-3', className)}>
      {variant === 'spinner' && (
        <div className="relative">
          <div
            className={cn(
              'rounded-full border-2 border-gray-200',
              sizeClasses[size]
            )}
          />
          <div
            className={cn(
              'absolute inset-0 rounded-full border-2 border-transparent border-t-primary-500 animate-spin',
              sizeClasses[size]
            )}
          />
        </div>
      )}

      {variant === 'dots' && (
        <div className="flex items-center gap-1.5">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className={cn(
                'rounded-full bg-primary-500',
                size === 'sm' ? 'h-1.5 w-1.5' : size === 'md' ? 'h-2 w-2' : 'h-3 w-3'
              )}
              style={{
                animation: 'bounce 1.4s infinite ease-in-out both',
                animationDelay: `${i * 0.16}s`,
              }}
            />
          ))}
        </div>
      )}

      {variant === 'pulse' && (
        <div className="relative">
          <div
            className={cn(
              'rounded-full bg-primary-100',
              sizeClasses[size]
            )}
          />
          <div
            className={cn(
              'absolute inset-0 rounded-full bg-primary-500 animate-ping opacity-75',
              sizeClasses[size]
            )}
          />
        </div>
      )}

      {text && (
        <p className={cn('text-gray-500 font-medium animate-pulse', textSizeClasses[size])}>
          {text}
        </p>
      )}
    </div>
  );
}

export function LoadingPage({ text = '読み込み中...' }: { text?: string }) {
  return (
    <div className="min-h-[400px] flex items-center justify-center animate-fade-in">
      <div className="flex flex-col items-center gap-6">
        {/* Animated logo placeholder */}
        <div className="relative">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-400 to-primary-600 shadow-lg shadow-primary-500/20 animate-pulse" />
          <div className="absolute -inset-2 rounded-3xl bg-primary-500/20 animate-ping" />
        </div>

        {/* Progress bar */}
        <div className="w-48 progress-bar progress-bar-indeterminate" />

        {/* Text */}
        <p className="text-sm text-gray-500 font-medium">{text}</p>
      </div>
    </div>
  );
}

export function LoadingOverlay({ text }: { text?: string }) {
  return (
    <div className="absolute inset-0 glass flex items-center justify-center z-20 animate-fade-in">
      <div className="flex flex-col items-center gap-4 p-6 bg-white rounded-2xl shadow-soft">
        <Loading size="md" variant="spinner" />
        {text && <p className="text-sm text-gray-600 font-medium">{text}</p>}
      </div>
    </div>
  );
}

// Skeleton components for loading states
export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        'shimmer rounded-lg',
        className
      )}
    />
  );
}

export function CardSkeleton() {
  return (
    <div className="card p-5 space-y-4 animate-fade-in">
      <div className="flex items-start justify-between">
        <div className="space-y-2 flex-1">
          <Skeleton className="h-5 w-3/4" />
          <Skeleton className="h-3 w-1/4" />
        </div>
        <Skeleton className="h-6 w-20 rounded-full" />
      </div>
      <div className="space-y-2">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-2/3" />
      </div>
    </div>
  );
}

export function ListSkeleton({ count = 3 }: { count?: number }) {
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {Array.from({ length: count }).map((_, i) => (
        <CardSkeleton key={i} />
      ))}
    </div>
  );
}
