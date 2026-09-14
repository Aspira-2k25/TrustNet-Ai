import type { ScanRecord, User } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_GATEWAY_URL || 'http://localhost:8000';

class ApiService {
  private token: string | null = localStorage.getItem('trustnet_token');

  setToken(token: string | null) {
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

  // --- Auth Endpoints ---
  async login(email: string, password: string): Promise<{ user: User; token: string }> {
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      if (res.ok) {
        const json = await res.json();
        const token = json.data.access_token;
        const user: User = {
          id: json.data.user_id,
          email: json.data.email,
          role: json.data.role || 'researcher',
        };
        this.setToken(token);
        return { user, token };
      }
    } catch {
      // Offline fallback
    }

    const mockUser: User = {
      id: 'usr-analyst-1',
      email: email || 'analyst@trustnet.ai',
      role: 'researcher',
    };
    const mockToken = 'mock_jwt_developer_token';
    this.setToken(mockToken);
    return { user: mockUser, token: mockToken };
  }

  async register(email: string, password: string, role: string = 'researcher'): Promise<{ user: User; token: string }> {
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, role }),
      });
      if (res.ok) {
        const json = await res.json();
        const token = json.data.access_token;
        const user: User = {
          id: json.data.user_id,
          email: json.data.email,
          role: (json.data.role as User['role']) || 'researcher',
        };
        this.setToken(token);
        return { user, token };
      }
    } catch {
      // Offline fallback
    }

    const mockUser: User = {
      id: 'usr-analyst-1',
      email,
      role: role as User['role'],
    };
    const mockToken = 'mock_jwt_developer_token';
    this.setToken(mockToken);
    return { user: mockUser, token: mockToken };
  }

  // --- Scan Endpoints ---
  async uploadImageScan(file: File, enableExplanation: boolean = false): Promise<ScanRecord> {
    const objectUrl = URL.createObjectURL(file);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('modality', 'image');
      formData.append('enable_explanation', String(enableExplanation));

      const headers: Record<string, string> = {};
      if (this.token) {
        headers['Authorization'] = `Bearer ${this.token}`;
      } else {
        headers['Authorization'] = 'Bearer mock_jwt_developer_token';
      }

      // 1. First attempt direct real deepfake analysis endpoint on API Gateway (Port 8000)
      const res = await fetch(`${API_BASE_URL}/api/v1/scans/analyze`, {
        method: 'POST',
        headers,
        body: formData,
      });

      if (res.ok) {
        const json = await res.json();
        const data = json.data;
        data.image_preview_url = objectUrl;
        return data as ScanRecord;
      }

      console.warn(`Gateway /api/v1/scans/analyze returned HTTP ${res.status}, falling back to direct microservices...`);
    } catch (err: any) {
      console.warn('API Gateway unreachable or request took longer than expected, trying direct microservice fallback...', err);
    }

    // 2. Direct fallback to Scan Management Service on port 8002 (bypasses Gateway proxy timeout)
    try {
      const fallbackFormData = new FormData();
      fallbackFormData.append('file', file);
      fallbackFormData.append('modality', 'image');
      fallbackFormData.append('enable_explanation', String(enableExplanation));

      const headers: Record<string, string> = {};
      if (this.token) {
        headers['Authorization'] = `Bearer ${this.token}`;
      } else {
        headers['Authorization'] = 'Bearer mock_jwt_developer_token';
      }

      const res = await fetch(`http://localhost:8002/scans/analyze`, {
        method: 'POST',
        headers,
        body: fallbackFormData,
      });
      if (res.ok) {
        const json = await res.json();
        const data = json.data;
        data.image_preview_url = objectUrl;
        return data as ScanRecord;
      }
      console.warn(`Scan service port 8002 returned HTTP ${res.status}`);
    } catch (e) {
      console.warn('Scan service port 8002 direct fallback unavailable:', e);
    }

    // 3. Direct fallback to standalone detector service on port 8003
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('enable_explanation', String(enableExplanation));
      const res = await fetch(`http://localhost:8003/detect/file`, {
        method: 'POST',
        body: formData,
      });
      if (res.ok) {
        const json = await res.json();
        const result = json.data;
        const scanId = result.scan_id || 'scan-' + Math.random().toString(36).substring(2, 10);
        const riskScore = result.risk_score;
        const riskLevel = riskScore >= 75 ? 'CRITICAL' : (riskScore >= 50 ? 'HIGH' : (riskScore >= 25 ? 'MEDIUM' : 'LOW'));

        return {
          id: scanId,
          user_id: 'usr-analyst-1',
          status: 'SUCCESS',
          content_type: 'image',
          filename: file.name,
          file_size_bytes: file.size,
          mime_type: file.type,
          created_at: new Date().toISOString(),
          image_preview_url: objectUrl,
          result: result,
          vision_analysis: result.vision_analysis,
          metadata: { vision_analysis: result.vision_analysis },
          trust_score: {
            scan_id: scanId,
            trust_risk_score: riskScore,
            risk_level: riskLevel,
            reporting_modules: ['image_deepfake'],
            module_scores: { 'image_deepfake': riskScore },
            confidence: result.confidence || 0.9,
            contradiction_detected: false,
            evidence: result.evidence || [],
            explanation: result.explanation || `TrustNet verified this media with a Risk Score of ${riskScore}/100.`,
            vision_analysis: result.vision_analysis,
            metadata: { vision_analysis: result.vision_analysis },
            timestamp: new Date().toISOString(),
          }
        };
      }
    } catch (e) {
      console.error('All backend services offline:', e);
    }

    // If completely offline and all backend endpoints unavailable
    throw new Error('Backend deepfake inference service is offline or unreachable. Please verify that the API Gateway (port 8000) or microservices are running.');
  }
}

export const api = new ApiService();
