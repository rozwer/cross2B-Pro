"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Plus,
  Settings,
  FileText,
  LayoutDashboard,
} from "lucide-react";
import { ThemeToggle } from "@/components/theme";
import { cn } from "@/lib/utils";

export function Navigation() {
  const pathname = usePathname();

  const isActive = (path: string) => {
    if (path === "/") {
      return pathname === "/";
    }
    return pathname.startsWith(path);
  };

  return (
    <nav className="flex items-center gap-1 sm:gap-2">
      {/* Main Navigation Links */}
      <Link
        href="/"
        className={cn(
          "inline-flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg transition-all",
          isActive("/")
            ? "text-primary-600 dark:text-primary-400 bg-primary-50 dark:bg-primary-900/30"
            : "text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-800"
        )}
      >
        <LayoutDashboard className="h-4 w-4" />
        <span className="hidden md:inline">ダッシュボード</span>
      </Link>
      <Link
        href="/articles"
        className={cn(
          "inline-flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg transition-all",
          isActive("/articles")
            ? "text-primary-600 dark:text-primary-400 bg-primary-50 dark:bg-primary-900/30"
            : "text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-800"
        )}
      >
        <FileText className="h-4 w-4" />
        <span className="hidden md:inline">成果物</span>
      </Link>

      <div className="h-6 w-px bg-gray-200 dark:bg-gray-700 mx-1 hidden sm:block" />

      <ThemeToggle />
      <Link
        href="/settings"
        className={cn(
          "inline-flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg transition-all",
          isActive("/settings")
            ? "text-primary-600 dark:text-primary-400 bg-primary-50 dark:bg-primary-900/30"
            : "text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-800"
        )}
      >
        <Settings className="h-4 w-4" />
        <span className="hidden lg:inline">Settings</span>
      </Link>
      <Link href="/settings/runs/new" className="btn btn-primary">
        <Plus className="h-4 w-4" />
        <span className="hidden sm:inline">New Run</span>
      </Link>
    </nav>
  );
}
