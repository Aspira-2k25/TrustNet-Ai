import { httpClient } from './client';

export const detectionApi = {
  /**
   * Dispatches direct detection request through the API Gateway (/api/v1/detect/file).
   */
  async detectFile(file: File, enableExplanation: boolean = false): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('enable_explanation', String(enableExplanation));

    return httpClient.request('/api/v1/detect/file', {
      method: 'POST',
      body: formData,
    });
  },
};
