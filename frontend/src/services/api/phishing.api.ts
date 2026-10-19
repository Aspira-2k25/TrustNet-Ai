import { httpClient } from './client';
import type { ScanRecord } from '../../types';
export async function submitPhishing(url: string, signal: AbortSignal): Promise<ScanRecord> {
  const response = await httpClient.request<{data: ScanRecord}>('/api/v1/scans/url', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({url}), signal});
  return response.data;
}
export async function retrievePhishing(scanId: string, signal: AbortSignal): Promise<ScanRecord> {
  const response = await httpClient.request<{data: ScanRecord}>(`/api/v1/scans/${encodeURIComponent(scanId)}`, {signal});
  if (response.data.content_type !== 'url' || response.data.id !== scanId) throw new Error('Unexpected phishing scan response');
  return response.data;
}
