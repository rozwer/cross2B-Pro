/**
 * Authentication Manager for API and WebSocket connections
 *
 * Security requirements:
 * - Uses sessionStorage (lower XSS risk than localStorage)
 * - Implements token refresh mechanism
 * - Handles 401 errors with automatic refresh
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export class AuthManager {
  private static readonly TOKEN_KEY = 'auth_token';
  private static readonly REFRESH_KEY = 'refresh_token';
  private static readonly TOKEN_EXPIRY_KEY = 'token_expiry';

  /**
   * Get the current access token
   */
  static getToken(): string | null {
    if (typeof window === 'undefined') return null;
    return sessionStorage.getItem(this.TOKEN_KEY);
  }

  /**
   * Store access and refresh tokens
   */
  static setToken(token: string, refreshToken?: string, expiresIn?: number): void {
    if (typeof window === 'undefined') return;
    sessionStorage.setItem(this.TOKEN_KEY, token);
    if (refreshToken) {
      sessionStorage.setItem(this.REFRESH_KEY, refreshToken);
    }
    if (expiresIn) {
      const expiry = Date.now() + expiresIn * 1000;
      sessionStorage.setItem(this.TOKEN_EXPIRY_KEY, expiry.toString());
    }
  }

  /**
   * Clear all authentication tokens
   */
  static clearToken(): void {
    if (typeof window === 'undefined') return;
    sessionStorage.removeItem(this.TOKEN_KEY);
    sessionStorage.removeItem(this.REFRESH_KEY);
    sessionStorage.removeItem(this.TOKEN_EXPIRY_KEY);
  }

  /**
   * Check if the token is expired or about to expire (within 1 minute)
   */
  static isTokenExpired(): boolean {
    if (typeof window === 'undefined') return true;
    const expiry = sessionStorage.getItem(this.TOKEN_EXPIRY_KEY);
    if (!expiry) return true;
    // Consider token expired if less than 1 minute remaining
    return Date.now() > parseInt(expiry, 10) - 60000;
  }

  /**
   * Attempt to refresh the access token
   */
  static async refreshToken(): Promise<string | null> {
    if (typeof window === 'undefined') return null;

    const refreshToken = sessionStorage.getItem(this.REFRESH_KEY);
    if (!refreshToken) {
      this.clearToken();
      return null;
    }

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

      const data = await response.json();
      const { access_token, refresh_token: newRefresh, expires_in } = data;
      this.setToken(access_token, newRefresh, expires_in);
      return access_token;
    } catch {
      this.clearToken();
      return null;
    }
  }

  /**
   * Get a valid token, refreshing if necessary
   */
  static async getValidToken(): Promise<string | null> {
    const token = this.getToken();
    if (!token) return null;

    if (this.isTokenExpired()) {
      return await this.refreshToken();
    }

    return token;
  }

  /**
   * Check if user is authenticated
   */
  static isAuthenticated(): boolean {
    return this.getToken() !== null;
  }

  /**
   * Redirect to login page
   */
  static redirectToLogin(): void {
    if (typeof window !== 'undefined') {
      window.location.href = '/login';
    }
  }
}

export default AuthManager;
