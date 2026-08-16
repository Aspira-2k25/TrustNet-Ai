export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
export type ScanStatus = 'PENDING' | 'SUCCESS' | 'FAILED';
export type ClassificationVerdict = 'AUTHENTIC' | 'LIKELY_AUTHENTIC' | 'UNCERTAIN' | 'LIKELY_AI_MANIPULATED' | 'SUSPICIOUS' | 'AI_GENERATED';

export interface EvidenceItem {
  feature_or_region: string;
  contribution: number;
  human_readable_note: string;
}

export interface AnalyzerStatus {
  name: string;
  category: 'primary_ml' | 'frequency' | 'compression' | 'face_forensics' | 'semantic_forensics' | 'micro_forensics' | 'sensor_forensics' | string;
  status: 'APPLIED' | 'SKIPPED';
  reason?: string;
  finding?: string;
}

export interface DetectionResult {
  scan_id: string;
  module: string;
  detector_id: string;
  model_version: string;
  preprocessing_version: string;
  native_score: number;
  native_score_semantics: string;
  risk_score: number; // 0.0 to 100.0
  confidence: number; // 0.0 to 1.0
  label: string;
  verdict: ClassificationVerdict;
  has_face: boolean;
  status: ScanStatus;
  evidence: EvidenceItem[];
  analyzers: AnalyzerStatus[];
  processing_time_ms: number;
  timestamp: string;
  explanation?: string;
  metadata?: Record<string, any>;
  error_code?: string;
  error_message?: string;
}

export interface TrustScoreResult {
  scan_id: string;
  trust_risk_score: number; // 0.0 to 100.0
  risk_level: RiskLevel;
  reporting_modules: string[];
  module_scores: Record<string, number>;
  confidence: number;
  contradiction_detected: boolean;
  evidence: EvidenceItem[];
  explanation: string;
  timestamp: string;
}

export interface ScanRecord {
  id: string;
  user_id: string;
  status: ScanStatus;
  content_type: 'image' | 'text' | 'url';
  media_storage_key?: string;
  filename?: string;
  mime_type?: string;
  file_size?: number;
  file_size_bytes?: number;
  image_preview_url?: string;
  result?: DetectionResult;
  trust_score?: TrustScoreResult;
  created_at: string;
  updated_at?: string;
}

export interface User {
  id: string;
  email: string;
  role: 'USER' | 'ADMIN' | 'researcher' | string;
  is_active?: boolean;
  created_at?: string;
}

export interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
}
