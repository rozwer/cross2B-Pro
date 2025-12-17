'use client';

import { Sun, Moon, Monitor } from 'lucide-react';
import { useTheme } from './ThemeProvider';
import { cn } from '@/lib/utils';

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();

  return (
    <div className="flex items-center gap-1 p-1 bg-gray-100 dark:bg-gray-800 rounded-lg">
      <button
        onClick={() => setTheme('light')}
        className={cn(
          'p-2 rounded-md transition-all',
          theme === 'light'
            ? 'bg-white dark:bg-gray-700 text-primary-600 shadow-sm'
            : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
        )}
        title="ライトモード"
      >
        <Sun className="h-4 w-4" />
      </button>
      <button
        onClick={() => setTheme('dark')}
        className={cn(
          'p-2 rounded-md transition-all',
          theme === 'dark'
            ? 'bg-white dark:bg-gray-700 text-primary-600 shadow-sm'
            : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
        )}
        title="ダークモード"
      >
        <Moon className="h-4 w-4" />
      </button>
      <button
        onClick={() => setTheme('system')}
        className={cn(
          'p-2 rounded-md transition-all',
          theme === 'system'
            ? 'bg-white dark:bg-gray-700 text-primary-600 shadow-sm'
            : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
        )}
        title="システム設定に従う"
      >
        <Monitor className="h-4 w-4" />
      </button>
    </div>
  );
}
