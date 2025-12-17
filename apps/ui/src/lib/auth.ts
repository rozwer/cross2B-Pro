/**
 * Authentication Manager for SEO Article Generator
 *
 * VULN-005: API認証の実装
 * - sessionStorage でトークン管理（localStorage より XSS リスク低減）
 * - トークンリフレッシュ機構
 * - 401エラー時の自動リフレッシュ
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface AuthTokens {
  access_token: string;
  refresh_token?: string;
  token_type: string;
  expires_in?: number;
}

export interface AuthUser {
  tenant_id: string;
  user_id: string;
  email?: string;
  roles?: string[];
}

/**
 * AuthManager - セキュアなトークン管理クラス
 *
 * セキュリティ要件:
 * - sessionStorage 使用（XSS リスク低減）
 * - トークンリフレッシュ機構
 * - 認証失敗時のクリーンアップ
 */
export class AuthManager {
  private static readonly TOKEN_KEY = 'auth_token';
  private static readonly REFRESH_KEY = 'refresh_token';
  private static readonly USER_KEY = 'auth_user';

  // トークン有効期限（秒）
  private static readonly ACCESS_TOKEN_EXPIRES = 15 * 60; // 15分
  private static readonly REFRESH_TOKEN_EXPIRES = 7 * 24 * 60 * 60; // 7日

  // リフレッシュ中フラグ（重複防止）
  private static refreshPromise: Promise<string | null> | null = null;

  /**
   * アクセストークンを取得
   */
  static getToken(): string | null {
    if (typeof window === 'undefined') return null;
    return sessionStorage.getItem(this.TOKEN_KEY);
  }

  /**
   * リフレッシュトークンを取得
   */
  static getRefreshToken(): string | null {
    if (typeof window === 'undefined') return null;
    return sessionStorage.getItem(this.REFRESH_KEY);
  }

  /**
   * ユーザー情報を取得
   */
  static getUser(): AuthUser | null {
    if (typeof window === 'undefined') return null;
    const userJson = sessionStorage.getItem(this.USER_KEY);
    if (!userJson) return null;
    try {
      return JSON.parse(userJson) as AuthUser;
    } catch {
      return null;
    }
  }

  /**
   * トークンを保存
   */
  static setToken(accessToken: string, refreshToken?: string): void {
    if (typeof window === 'undefined') return;
    sessionStorage.setItem(this.TOKEN_KEY, accessToken);
    if (refreshToken) {
      sessionStorage.setItem(this.REFRESH_KEY, refreshToken);
    }
  }

  /**
   * ユーザー情報を保存
   */
  static setUser(user: AuthUser): void {
    if (typeof window === 'undefined') return;
    sessionStorage.setItem(this.USER_KEY, JSON.stringify(user));
  }

  /**
   * 認証情報をクリア（ログアウト）
   */
  static clearToken(): void {
    if (typeof window === 'undefined') return;
    sessionStorage.removeItem(this.TOKEN_KEY);
    sessionStorage.removeItem(this.REFRESH_KEY);
    sessionStorage.removeItem(this.USER_KEY);
  }

  /**
   * 認証済みかどうか
   */
  static isAuthenticated(): boolean {
    return this.getToken() !== null;
  }

  /**
   * テナントIDを取得
   */
  static getTenantId(): string | null {
    const user = this.getUser();
    return user?.tenant_id ?? null;
  }

  /**
   * トークンリフレッシュを実行
   *
   * 重複リクエストを防ぐため、既存のリフレッシュ処理があれば待機
   */
  static async refreshToken(): Promise<string | null> {
    // 既存のリフレッシュ処理があれば待機
    if (this.refreshPromise) {
      return this.refreshPromise;
    }

    const refreshToken = this.getRefreshToken();
    if (!refreshToken) {
      this.clearToken();
      return null;
    }

    // リフレッシュ処理を開始
    this.refreshPromise = this.performRefresh(refreshToken);

    try {
      return await this.refreshPromise;
    } finally {
      this.refreshPromise = null;
    }
  }

  /**
   * 実際のリフレッシュAPIコール
   */
  private static async performRefresh(refreshToken: string): Promise<string | null> {
    try {
      const response = await fetch(`${API_BASE}/api/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (!response.ok) {
        this.clearToken();
        return null;
      }

      const data: AuthTokens = await response.json();
      this.setToken(data.access_token, data.refresh_token);
      return data.access_token;
    } catch {
      this.clearToken();
      return null;
    }
  }

  /**
   * ログイン処理
   */
  static async login(email: string, password: string): Promise<boolean> {
    try {
      const response = await fetch(`${API_BASE}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        return false;
      }

      const data = await response.json();
      this.setToken(data.access_token, data.refresh_token);

      if (data.user) {
        this.setUser(data.user);
      }

      return true;
    } catch {
      return false;
    }
  }

  /**
   * ログアウト処理
   */
  static async logout(): Promise<void> {
    const token = this.getToken();

    if (token) {
      try {
        await fetch(`${API_BASE}/api/auth/logout`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
          },
        });
      } catch {
        // エラーは無視（サーバー側でセッション期限切れの可能性）
      }
    }

    this.clearToken();
  }

  /**
   * 認証ヘッダーを生成
   */
  static getAuthHeaders(): Record<string, string> {
    const token = this.getToken();
    if (!token) {
      return {};
    }
    return {
      'Authorization': `Bearer ${token}`,
    };
  }

  /**
   * 401エラー時のハンドリング（リダイレクト）
   *
   * NOTE: 開発段階では認証機能が未実装のため、リダイレクトを無効化
   */
  static handleUnauthorized(): void {
    this.clearToken();
    if (typeof window !== 'undefined') {
      // TODO: 認証機能実装後に有効化
      // const returnUrl = encodeURIComponent(window.location.pathname + window.location.search);
      // window.location.href = `/login?returnUrl=${returnUrl}`;
      console.warn('[Auth] Unauthorized - authentication not implemented yet');
    }
  }
}

/**
 * 認証付きfetchラッパー
 *
 * 401エラー時に自動でトークンリフレッシュを試行
 */
export async function authenticatedFetch(
  input: RequestInfo | URL,
  init?: RequestInit
): Promise<Response> {
  const token = AuthManager.getToken();

  const headers = new Headers(init?.headers);
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const response = await fetch(input, {
    ...init,
    headers,
  });

  // 401エラーの場合、トークンリフレッシュを試行
  if (response.status === 401) {
    const newToken = await AuthManager.refreshToken();

    if (newToken) {
      // 新しいトークンで再試行
      headers.set('Authorization', `Bearer ${newToken}`);
      return fetch(input, {
        ...init,
        headers,
      });
    }

    // リフレッシュ失敗時はログインページへ
    AuthManager.handleUnauthorized();
    throw new Error('Unauthorized');
  }

  return response;
}

export default AuthManager;
