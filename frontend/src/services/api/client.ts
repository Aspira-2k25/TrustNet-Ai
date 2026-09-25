/**
 * TrustNet AI — Central API Gateway Client
 * Enforces all browser communication to flow strictly through the API Gateway.
 */

export const API_BASE_URL: string =
  import.meta.env.VITE_API_GATEWAY_URL || 'http://localhost:8000';

class HttpClient {
  private token: string | null = localStorage.getItem('trustnet_token');

  setToken(token: string | null): void {
    this.token = token;
    if (token) {
      localStorage.setItem('trustnet_token', token);
    } else {
      localStorage.removeItem('trustnet_token');
    }
  }

  getToken(): string | null {
    return this.token;
  }

  getHeaders(customHeaders: Record<string, string> = {}, requiresAuth: boolean = true): Record<string, string> {
    const headers: Record<string, string> = { ...customHeaders };
    const effectiveToken = this.token || (import.meta.env.DEV ? 'mock_jwt_developer_token' : null);
    if (requiresAuth && effectiveToken) {
      headers['Authorization'] = `Bearer ${effectiveToken}`;
    }
    return headers;
  }

  async request<T>(endpoint: string, options: RequestInit = {}, requiresAuth: boolean = true): Promise<T> {
    const url = endpoint.startsWith('http') ? endpoint : `${API_BASE_URL}${endpoint}`;
    const headers = this.getHeaders(
      (options.headers as Record<string, string>) || {},
      requiresAuth
    );

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      let errorMessage = `API request failed with status ${response.status}`;
      try {
        const errorJson = await response.json();
        if (errorJson.detail) {
          errorMessage = typeof errorJson.detail === 'string'
            ? errorJson.detail
            : (errorJson.detail.message || JSON.stringify(errorJson.detail));
        } else if (errorJson.message) {
          errorMessage = errorJson.message;
        }
      } catch {
        // Fall back to HTTP status message
      }
      throw new Error(errorMessage);
    }

    return response.json() as Promise<T>;
  }
}

export const httpClient = new HttpClient();
