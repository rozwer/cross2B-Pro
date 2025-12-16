import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import Link from 'next/link';
import { Sparkles, Plus, LayoutDashboard } from 'lucide-react';
import './globals.css';

const inter = Inter({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-inter',
});

export const metadata: Metadata = {
  title: 'SEO Article Generator',
  description: 'SEO記事自動生成システム - 社内エンジニア向けUI',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ja" className={inter.variable}>
      <body className={inter.className}>
        <div className="min-h-screen bg-gray-50">
          {/* Header */}
          <header className="glass sticky top-0 z-50 border-b border-gray-200/50">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <div className="flex justify-between items-center h-16">
                {/* Logo */}
                <Link
                  href="/runs"
                  className="flex items-center gap-3 group"
                >
                  <div className="flex items-center justify-center w-9 h-9 rounded-xl gradient-primary shadow-sm group-hover:shadow-md transition-shadow">
                    <Sparkles className="h-5 w-5 text-white" />
                  </div>
                  <span className="text-lg font-semibold text-gray-900 hidden sm:block">
                    SEO Generator
                  </span>
                </Link>

                {/* Navigation */}
                <nav className="flex items-center gap-2">
                  <Link
                    href="/runs"
                    className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-all"
                  >
                    <LayoutDashboard className="h-4 w-4" />
                    <span className="hidden sm:inline">Dashboard</span>
                  </Link>
                  <Link
                    href="/runs/new"
                    className="btn btn-primary"
                  >
                    <Plus className="h-4 w-4" />
                    <span className="hidden sm:inline">New Run</span>
                  </Link>
                </nav>
              </div>
            </div>

            {/* Decorative gradient line */}
            <div className="h-[2px] w-full bg-gradient-to-r from-transparent via-primary-500/30 to-transparent" />
          </header>

          {/* Main Content */}
          <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <div className="animate-fade-in">
              {children}
            </div>
          </main>

          {/* Footer */}
          <footer className="border-t border-gray-200 mt-auto">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
              <div className="flex flex-col sm:flex-row justify-between items-center gap-4 text-sm text-gray-500">
                <p>SEO Article Generator v1.0</p>
                <p className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-primary-500 animate-pulse" />
                  System Online
                </p>
              </div>
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}
