/**
 * TrustNet AI — API Service Entry Point
 * Modularized under frontend/src/services/api/ for clean separation of concerns.
 */

import { api } from './api/index';

export { api, httpClient, API_BASE_URL, authApi, scanApi, trustApi, detectionApi } from './api/index';
export default api;
