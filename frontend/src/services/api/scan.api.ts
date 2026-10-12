import { httpClient } from './client';
import type { ScanRecord } from '../../types';

export const scanApi = {
  async getLimits(): Promise<{data:{image_mb:number}}> {return httpClient.request('/api/v1/scans/limits');},
  async analyzeScam(text: string, context: {message_type?: 'sms'|'email'; subject?: string; claimed_sender?: string; reply_to?: string; text_format?: 'plain'|'html'; optional_analysis?: boolean} = {}): Promise<ScanRecord> {
    const res = await httpClient.request<{data: ScanRecord}>('/api/v1/scans/scam/analyze', {
      method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({text, ...context})
    });
    return res.data;
  },
  /**
   * Uploads an image for forensic deepfake analysis.
   * Dispatched strictly through API Gateway (/api/v1/scans/analyze).
   * Direct microservice bypass to ports 8002/8003 has been removed for production security.
   */
  async uploadImageScan(file: File, enableExplanation: boolean = false): Promise<ScanRecord> {
    const objectUrl = URL.createObjectURL(file);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('modality', 'image');
    formData.append('enable_explanation', String(enableExplanation));

    const json = await httpClient.request<{ data: any; status: string }>(
      '/api/v1/scans/analyze',
      {
        method: 'POST',
        body: formData,
      },
      true
    );

    const data = json.data;
    data.image_preview_url = objectUrl;
    return data as ScanRecord;
  },

  /**
   * Async file scan upload via message broker pipeline.
   */
  async uploadFile(file: File, modality: 'image' | 'audio' | 'video'): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('modality', modality);

    return httpClient.request('/api/v1/scans/upload', {
      method: 'POST',
      body: formData,
    });
  },

  /**
   * Scan text (SMS, WhatsApp message, email, or review).
   */
  async scanText(text: string): Promise<any> {
    return httpClient.request('/api/v1/scans/text', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    });
  },

  /**
   * Scan URL for phishing and homoglyph threats.
   */
  async scanUrl(url: string): Promise<any> {
    return httpClient.request('/api/v1/scans/url', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
    });
  },

  /**
   * Poll scan status by ID.
   */
  async getScanStatus(scanId: string): Promise<any> {
    return httpClient.request(`/api/v1/scans/${scanId}/status`);
  },

  /**
   * Retrieve scan history with pagination.
   */
  async listScans(limit: number = 20, offset: number = 0): Promise<any> {
    const page = Math.floor(offset / limit) + 1;
    return httpClient.request(`/api/v1/scans?limit=${limit}&page=${page}`);
  },
};
