import { httpClient } from './client';

export const trustApi = {
  /**
   * Fetches the fused trust score for a specific scan ID via API Gateway.
   */
  async getScore(scanId: string): Promise<any> {
    return httpClient.request(`/api/v1/trust/scores/${scanId}`);
  },

  /**
   * Request multi-detector score fusion via API Gateway.
   */
  async fuseScores(payload: any): Promise<any> {
    return httpClient.request('/api/v1/trust/fuse', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
  },
};
