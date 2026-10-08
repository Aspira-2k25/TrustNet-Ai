import { httpClient } from './client';
import { authApi } from './auth.api';
import { scanApi } from './scan.api';
import { trustApi } from './trust.api';
import { detectionApi } from './detection.api';
import type { User, ScanRecord } from '../../types';

export { httpClient, API_BASE_URL } from './client';
export { authApi } from './auth.api';
export { scanApi } from './scan.api';
export { trustApi } from './trust.api';
export { detectionApi } from './detection.api';

/**
 * Unified API Client preserving complete backward compatibility with existing views.
 */
class ApiService {
  setToken(token: string | null): void {
    httpClient.setToken(token);
  }

  getToken(): string | null {
    return httpClient.getToken();
  }

  async login(email: string, password: string): Promise<{ user: User; token: string }> {
    return authApi.login(email, password);
  }

  async register(email: string, password: string, role: string = 'researcher'): Promise<{ user: User; token: string }> {
    return authApi.register(email, password, role);
  }

  async uploadImageScan(file: File, enableExplanation: boolean = false): Promise<ScanRecord> {
    return scanApi.uploadImageScan(file, enableExplanation);
  }

  async detectFile(file: File, enableExplanation: boolean = false): Promise<any> {
    return detectionApi.detectFile(file, enableExplanation);
  }

  async getScanStatus(scanId: string): Promise<any> {
    return scanApi.getScanStatus(scanId);
  }

  async listScans(limit: number = 20, offset: number = 0): Promise<any> {
    return scanApi.listScans(limit, offset);
  }

  async getTrustScore(scanId: string): Promise<any> {
    return trustApi.getScore(scanId);
  }
}

export const api = new ApiService();
