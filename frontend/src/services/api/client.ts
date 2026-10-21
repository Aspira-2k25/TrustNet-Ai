/**
 * TrustNet AI — Central API Gateway Client
 * Enforces all browser communication to flow strictly through the API Gateway.
 */

export const API_BASE_URL: string =
  import.meta.env.VITE_API_GATEWAY_URL || (import.meta.env.DEV ? '' : 'http://127.0.0.1:8000');

class HttpClient {
  private token: string | null = localStorage.getItem('trustnet_token');

  setToken(token: string | null): void {
    this.token = token;
    if (token) {
      localStorage.setItem('trustnet_token', token);
      localStorage.removeItem('trustnet_logged_out');
    } else {
      localStorage.removeItem('trustnet_token');
      localStorage.setItem('trustnet_logged_out', 'true');
    }
  }

  getToken(): string | null {
    return this.token;
  }

  getHeaders(customHeaders: Record<string, string> = {}, requiresAuth: boolean = true): Record<string, string> {
    const headers: Record<string, string> = { ...customHeaders };
    const effectiveToken = this.token;
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

    const requestToken=this.token;
    const controller=new AbortController();
    const abort=()=>controller.abort();
    if(options.signal?.aborted)controller.abort();
    else options.signal?.addEventListener('abort',abort,{once:true});
    const timer=setTimeout(()=>controller.abort(),40000);
    let response:Response;
    try {response = await fetch(url, {
      ...options,
      headers,
      signal:controller.signal,
    });} finally {clearTimeout(timer);options.signal?.removeEventListener('abort',abort);}
    if(response.status===401&&requiresAuth&&requestToken&&this.token===requestToken){
      this.setToken(null);
      window.dispatchEvent(new Event('trustnet-session-expired'));
    }

    if (!response.ok) {
      let errorMessage = `API request failed with status ${response.status}`;
      try {
        const errorJson = await response.json();
        if (errorJson.error) {
          errorMessage = typeof errorJson.error === 'string'
            ? errorJson.error
            : (errorJson.error.message || JSON.stringify(errorJson.error));
        } else if (errorJson.detail) {
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
