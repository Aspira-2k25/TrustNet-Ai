export interface ResultPresentation {
  verdict_key: 'looks_ai'|'looks_edited'|'scam'|'risky'|'no_clear_signs'|'not_sure'|'incomplete';
  headline:string; reasons:Array<{text:string;evidence_id:string}>; next_steps:string[];
  level:Record<string,'low'|'medium'|'high'>; limits:string[]; details:Record<string,unknown>;
  checks?:Array<{name:string;state:'warning'|'uncertain'|'incomplete';text:string;evidence_id:string}>;
  locales?:Record<string,Omit<ResultPresentation,'locales'|'details'>>;
}
export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL' | 'UNKNOWN';
export type ScanStatus = 'PENDING' | 'QUEUED' | 'PROCESSING' | 'PARTIAL_SUCCESS' | 'UNAVAILABLE' | 'TIMEOUT' | 'SUCCESS' | 'FAILED';
export type ClassificationVerdict = 'INCONCLUSIVE' | 'LIKELY_AI_GENERATED' | 'LIKELY_MANIPULATED' | 'AUTHENTIC' | 'LIKELY_AUTHENTIC' | 'UNCERTAIN' | 'LIKELY_AI_MANIPULATED' | 'SUSPICIOUS' | 'AI_GENERATED' | 'SMISHING_RISK' | 'SPAM_SCREENING' | 'LOW_SMISHING_SIGNAL' | 'UNKNOWN' | 'NO_STRONG_INDICATORS' | 'LIKELY_SCAM' | 'UNABLE_TO_ASSESS';

export interface EvidenceItem {
  feature_or_region: string;
  contribution: number;
  human_readable_note: string;
}

export interface AnalyzerStatus {
  name: string;
  category: 'primary_ml' | 'frequency' | 'compression' | 'face_forensics' | 'semantic_forensics' | 'micro_forensics' | 'sensor_forensics' | 'local_vision_reasoning' | string;
  status: 'APPLIED' | 'SKIPPED' | 'UNAVAILABLE' | string;
  reason?: string;
  finding?: string;
}

export interface VisionAnalysis {
  status: 'APPLIED' | 'UNAVAILABLE' | string;
  model_name?: string;
  visual_verdict?: 'suspicious' | 'authentic' | 'inconclusive' | string;
  confidence?: number;
  observations?: string[];
  suspicious_regions?: Array<{ region: string; reason: string }>;
  supporting_evidence?: string[];
  contradicting_evidence?: string[];
  uncertainties?: string[];
  simple_explanation?: string;
  thinking_process?: string;
  reason?: string;
}

export interface DetectionResult {
  presentation?:ResultPresentation;
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
  vision_analysis?: VisionAnalysis;
  metadata?: Record<string, any>;
  error_code?: string;
  error_message?: string;
}

export interface TrustScoreResult {
  scan_id: string;
  trust_risk_score: number | null; // 0.0 to 100.0
  risk_level: RiskLevel;
  reporting_modules: string[];
  module_scores: Record<string, number>;
  confidence: number;
  contradiction_detected: boolean;
  contradiction_flag?: boolean;
  contradiction_details?: string;
  evidence: EvidenceItem[];
  explanation: string;
  vision_analysis?: VisionAnalysis;
  metadata?: Record<string, any>;
  timestamp: string;
}

export interface ScanRecord {
  id: string;
  user_id: string;
  status: ScanStatus;
  content_type: 'image' | 'video' | 'audio' | 'text' | 'url';
  raw_input?: string;
  media_storage_key?: string;
  filename?: string;
  mime_type?: string;
  file_size?: number;
  file_size_bytes?: number;
  dimensions?: { width: number; height: number };
  image_preview_url?: string;
  result?: DetectionResult;
  trust_score?: TrustScoreResult;
  vision_analysis?: VisionAnalysis;
  metadata?: Record<string, any>;
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
