import { Suspense, lazy, useState } from 'react';
import { Navbar } from './components/Navbar';
import { PageSkeleton } from './components/Skeleton';

// Lazy load views for performance
const LandingView = lazy(() => import('./views/LandingView').then(m => ({ default: m.LandingView })));
const DashboardView = lazy(() => import('./views/DashboardView').then(m => ({ default: m.DashboardView })));
const ScanUploadView = lazy(() => import('./views/ScanUploadView').then(m => ({ default: m.ScanUploadView })));
const ReportView = lazy(() => import('./views/ReportView').then(m => ({ default: m.ReportView })));
const LoginView = lazy(() => import('./views/LoginView').then(m => ({ default: m.LoginView })));
const RegisterView = lazy(() => import('./views/RegisterView').then(m => ({ default: m.RegisterView })));
import type { ScanRecord, User } from './types';

// Benchmark reference records for presentation and initial dashboard telemetry
const BENCHMARK_SCANS: ScanRecord[] = [
  {
    id: 'scan-ff-c23-0182',
    user_id: 'usr-researcher-1',
    status: 'SUCCESS',
    content_type: 'image',
    filename: 'faceforensics_c23_manipulated_sample.jpg',
    file_size_bytes: 842190,
    mime_type: 'image/jpeg',
    created_at: new Date(Date.now() - 3600000 * 2).toISOString(),
    image_preview_url: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=500&auto=format&fit=crop&q=80',
    result: {
      scan_id: 'scan-ff-c23-0182',
      module: 'image_deepfake',
      detector_id: 'image_deepfake.efficientnet_b0.v1',
      model_version: 'v1.0.0',
      preprocessing_version: 'v1.0.0',
      native_score: 0.12,
      native_score_semantics: 'probability_of_negative_class',
      risk_score: 88,
      confidence: 0.94,
      label: 'fake',
      verdict: 'AI_GENERATED',
      has_face: true,
      status: 'SUCCESS',
      evidence: [
        {
          feature_or_region: 'facial_boundary_artifacts',
          contribution: 0.88,
          human_readable_note: 'High frequency blending discontinuities detected around the jawline and periocular boundaries.',
        },
        {
          feature_or_region: 'fft_spectral_residuals',
          contribution: 0.74,
          human_readable_note: 'Checkerboard convolution artifacts identified in frequency spectrum.',
        }
      ],
      analyzers: [
        { name: 'EfficientNet-B0 Convolutional Backbone', category: 'primary_ml', status: 'APPLIED', finding: 'Spatial feature divergence consistent with generative synthesis.' },
        { name: 'TrustNet Vision AI', category: 'local_vision_reasoning', status: 'APPLIED', finding: 'Visual verdict: suspicious (confidence: 94%). Synthetically manipulated facial landmarks.' },
        { name: 'FFT High-Frequency Residual Analyzer', category: 'frequency', status: 'APPLIED', finding: 'Periodic grid artifacts detected in 2D Discrete Fourier Transform spectrum.' },
      ],
      processing_time_ms: 195,
      timestamp: new Date(Date.now() - 3600000 * 2).toISOString(),
    },
    trust_score: {
      scan_id: 'scan-ff-c23-0182',
      trust_risk_score: 88,
      risk_level: 'CRITICAL',
      reporting_modules: ['image_deepfake'],
      module_scores: { 'image_deepfake': 88 },
      confidence: 0.94,
      contradiction_detected: false,
      evidence: [
        {
          feature_or_region: 'facial_boundary_artifacts',
          contribution: 0.88,
          human_readable_note: 'High frequency blending discontinuities detected around the jawline and periocular boundaries.',
        }
      ],
      explanation: 'TrustNet synthesized a Risk Score of 88/100 (CRITICAL RISK). Deep learning inspection identified pronounced facial warping artifacts and frequency domain GAN residuals.',
      timestamp: new Date(Date.now() - 3600000 * 2).toISOString(),
    },
  },
  {
    id: 'scan-vid-surv-7721',
    user_id: 'usr-researcher-1',
    status: 'SUCCESS',
    content_type: 'video',
    filename: 'surveillance_cctv_suspect_deepfake.mp4',
    file_size_bytes: 14520300,
    mime_type: 'video/mp4',
    created_at: new Date(Date.now() - 3600000 * 5).toISOString(),
    result: {
      scan_id: 'scan-vid-surv-7721',
      module: 'video_deepfake',
      detector_id: 'video_deepfake.temporal_sync.v2',
      model_version: 'v2.1.0',
      preprocessing_version: 'v2.0.0',
      native_score: 0.18,
      native_score_semantics: 'probability_of_negative_class',
      risk_score: 82,
      confidence: 0.93,
      label: 'fake',
      verdict: 'AI_GENERATED',
      has_face: true,
      status: 'SUCCESS',
      evidence: [
        {
          feature_or_region: 'temporal_facial_jitter',
          contribution: 0.85,
          human_readable_note: 'Inter-frame landmark discontinuity observed across frames 42 to 118.',
        }
      ],
      analyzers: [
        { name: 'Temporal Landmark Consistency (3D CNN)', category: 'temporal', status: 'APPLIED', finding: 'High frequency phase shifts in eye-blink cycle and jaw coordinates.' },
        { name: 'Audio-Visual Sync Lip Flap Matcher', category: 'multimodal', status: 'APPLIED', finding: 'Phoneme to viseme mapping divergence exceeding threshold.' },
      ],
      processing_time_ms: 1240,
      timestamp: new Date(Date.now() - 3600000 * 5).toISOString(),
    },
    trust_score: {
      scan_id: 'scan-vid-surv-7721',
      trust_risk_score: 82,
      risk_level: 'CRITICAL',
      reporting_modules: ['video_deepfake'],
      module_scores: { 'video_deepfake': 82 },
      confidence: 0.93,
      contradiction_detected: false,
      evidence: [
        {
          feature_or_region: 'temporal_facial_jitter',
          contribution: 0.85,
          human_readable_note: 'Inter-frame landmark discontinuity observed across frames 42 to 118.',
        }
      ],
      explanation: 'TrustNet evaluated this video evidence with a Risk Score of 82/100 (CRITICAL RISK). Pronounced temporal frame jitter confirms synthetic face reenactment.',
      timestamp: new Date(Date.now() - 3600000 * 5).toISOString(),
    },
  },
  {
    id: 'scan-aud-wire-3310',
    user_id: 'usr-researcher-1',
    status: 'SUCCESS',
    content_type: 'audio',
    filename: 'executive_wire_fraud_voice_clone.wav',
    file_size_bytes: 4210000,
    mime_type: 'audio/wav',
    created_at: new Date(Date.now() - 3600000 * 10).toISOString(),
    result: {
      scan_id: 'scan-aud-wire-3310',
      module: 'audio_deepfake',
      detector_id: 'audio_deepfake.vocoder_flux.v1',
      model_version: 'v1.4.0',
      preprocessing_version: 'v1.2.0',
      native_score: 0.15,
      native_score_semantics: 'probability_of_negative_class',
      risk_score: 85,
      confidence: 0.95,
      label: 'fake',
      verdict: 'AI_GENERATED',
      has_face: false,
      status: 'SUCCESS',
      evidence: [
        {
          feature_or_region: 'synthetic_vocoder_harmonics',
          contribution: 0.89,
          human_readable_note: 'Unnatural phase uniformity and high-frequency spectral cutoff consistent with neural vocoder.',
        }
      ],
      analyzers: [
        { name: 'Neural Vocoder Residual Classifier', category: 'spectral', status: 'APPLIED', finding: 'Phase discontinuity matching synthetic text-to-speech architectures.' },
      ],
      processing_time_ms: 380,
      timestamp: new Date(Date.now() - 3600000 * 10).toISOString(),
    },
    trust_score: {
      scan_id: 'scan-aud-wire-3310',
      trust_risk_score: 85,
      risk_level: 'CRITICAL',
      reporting_modules: ['audio_deepfake'],
      module_scores: { 'audio_deepfake': 85 },
      confidence: 0.95,
      contradiction_detected: false,
      evidence: [
        {
          feature_or_region: 'synthetic_vocoder_harmonics',
          contribution: 0.89,
          human_readable_note: 'Unnatural phase uniformity consistent with neural vocoder synthesis.',
        }
      ],
      explanation: 'TrustNet classified this audio recording with a Risk Score of 85/100 (CRITICAL RISK). Neural vocoder phase signatures confirm synthetic voice cloning.',
      timestamp: new Date(Date.now() - 3600000 * 10).toISOString(),
    },
  },
  {
    id: 'scan-url-bank-8921',
    user_id: 'usr-researcher-1',
    status: 'SUCCESS',
    content_type: 'url',
    filename: 'https://secure-bank-login-update-auth.com',
    file_size_bytes: 0,
    mime_type: 'text/uri-list',
    created_at: new Date(Date.now() - 3600000 * 15).toISOString(),
    result: {
      scan_id: 'scan-url-bank-8921',
      module: 'phishing_url',
      detector_id: 'phishing_url.homoglyph_dns.v1',
      model_version: 'v1.1.0',
      preprocessing_version: 'v1.0.0',
      native_score: 0.04,
      native_score_semantics: 'probability_of_negative_class',
      risk_score: 96,
      confidence: 0.98,
      label: 'fake',
      verdict: 'AI_GENERATED',
      has_face: false,
      status: 'SUCCESS',
      evidence: [
        {
          feature_or_region: 'homoglyph_brand_spoofing',
          contribution: 0.96,
          human_readable_note: 'Cyrillic homoglyph character detected substituting Latin character in domain authority string.',
        }
      ],
      analyzers: [
        { name: 'Homoglyph & Punycode Threat Resolver', category: 'dns', status: 'APPLIED', finding: 'Deceptive script substitution identified in domain authority.' },
      ],
      processing_time_ms: 92,
      timestamp: new Date(Date.now() - 3600000 * 15).toISOString(),
    },
    trust_score: {
      scan_id: 'scan-url-bank-8921',
      trust_risk_score: 96,
      risk_level: 'CRITICAL',
      reporting_modules: ['phishing_url'],
      module_scores: { 'phishing_url': 96 },
      confidence: 0.98,
      contradiction_detected: false,
      evidence: [
        {
          feature_or_region: 'homoglyph_brand_spoofing',
          contribution: 0.96,
          human_readable_note: 'Cyrillic homoglyph character detected in domain authority string.',
        }
      ],
      explanation: 'TrustNet flagged this target URL with a Risk Score of 96/100 (CRITICAL RISK). High-threat homoglyph typosquatting indicates malicious credential harvesting.',
      timestamp: new Date(Date.now() - 3600000 * 15).toISOString(),
    },
  },
  {
    id: 'scan-auth-dslr-0931',
    user_id: 'usr-researcher-1',
    status: 'SUCCESS',
    content_type: 'image',
    filename: 'authentic_nikon_portrait_raw.jpg',
    file_size_bytes: 1450200,
    mime_type: 'image/jpeg',
    created_at: new Date(Date.now() - 3600000 * 20).toISOString(),
    image_preview_url: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=500&auto=format&fit=crop&q=80',
    result: {
      scan_id: 'scan-auth-dslr-0931',
      module: 'image_deepfake',
      detector_id: 'image_deepfake.efficientnet_b0.v1',
      model_version: 'v1.0.0',
      preprocessing_version: 'v1.0.0',
      native_score: 0.92,
      native_score_semantics: 'probability_of_negative_class',
      risk_score: 8,
      confidence: 0.96,
      label: 'real',
      verdict: 'AUTHENTIC',
      has_face: true,
      status: 'SUCCESS',
      evidence: [
        {
          feature_or_region: 'natural_sensor_noise',
          contribution: 0.08,
          human_readable_note: 'Consistent Bayer filter demosaicing and uniform sensor noise distribution.',
        }
      ],
      analyzers: [
        { name: 'EfficientNet-B0 Convolutional Backbone', category: 'primary_ml', status: 'APPLIED', finding: 'Natural texture distribution consistent with camera sensor capture.' },
      ],
      processing_time_ms: 180,
      timestamp: new Date(Date.now() - 3600000 * 20).toISOString(),
    },
    trust_score: {
      scan_id: 'scan-auth-dslr-0931',
      trust_risk_score: 8,
      risk_level: 'LOW',
      reporting_modules: ['image_deepfake'],
      module_scores: { 'image_deepfake': 8 },
      confidence: 0.96,
      contradiction_detected: false,
      evidence: [
        {
          feature_or_region: 'natural_sensor_noise',
          contribution: 0.08,
          human_readable_note: 'Consistent Bayer filter demosaicing and uniform sensor noise distribution.',
        }
      ],
      explanation: 'TrustNet verified this media with a Risk Score of 8/100 (LOW RISK). Sensor noise patterns and optical chromatic continuity are consistent with authentic camera capture.',
      timestamp: new Date(Date.now() - 3600000 * 20).toISOString(),
    },
  },
  {
    id: 'scan-txt-scam-4821',
    user_id: 'usr-researcher-1',
    status: 'SUCCESS',
    content_type: 'text',
    filename: 'fake_verified_purchase_campaign.txt',
    file_size_bytes: 280,
    mime_type: 'text/plain',
    created_at: new Date(Date.now() - 3600000 * 24).toISOString(),
    result: {
      scan_id: 'scan-txt-scam-4821',
      module: 'fake_review',
      detector_id: 'fake_review.stylometry_nlp.v1',
      model_version: 'v1.0.0',
      preprocessing_version: 'v1.0.0',
      native_score: 0.11,
      native_score_semantics: 'probability_of_negative_class',
      risk_score: 89,
      confidence: 0.94,
      label: 'fake',
      verdict: 'AI_GENERATED',
      has_face: false,
      status: 'SUCCESS',
      evidence: [
        {
          feature_or_region: 'synthetic_burstiness_anomaly',
          contribution: 0.88,
          human_readable_note: 'Low perplexity score and uniform sentence lengths match generative LLM text patterns.',
        }
      ],
      analyzers: [
        { name: 'LLM Stylometric Perplexity Engine', category: 'nlp', status: 'APPLIED', finding: 'High probability of synthetic generative text composition.' },
      ],
      processing_time_ms: 110,
      timestamp: new Date(Date.now() - 3600000 * 24).toISOString(),
    },
    trust_score: {
      scan_id: 'scan-txt-scam-4821',
      trust_risk_score: 89,
      risk_level: 'CRITICAL',
      reporting_modules: ['fake_review'],
      module_scores: { 'fake_review': 89 },
      confidence: 0.94,
      contradiction_detected: false,
      evidence: [
        {
          feature_or_region: 'synthetic_burstiness_anomaly',
          contribution: 0.88,
          human_readable_note: 'Low perplexity score and uniform sentence lengths match generative LLM text patterns.',
        }
      ],
      explanation: 'TrustNet classified this message with a Risk Score of 89/100 (CRITICAL RISK). Generative language phrasing patterns trigger high-confidence scam markers.',
      timestamp: new Date(Date.now() - 3600000 * 24).toISOString(),
    },
  },
];

export function App() {
  const [activeTab, setActiveTab] = useState<'landing' | 'dashboard' | 'scan' | 'login' | 'register' | 'report'>('landing');
  const [user, setUser] = useState<User | null>({
    id: 'usr-researcher-1',
    email: 'analyst@trustnet.ai',
    role: 'researcher',
  });
  const [scans, setScans] = useState<ScanRecord[]>(BENCHMARK_SCANS);
  const [selectedScan, setSelectedScan] = useState<ScanRecord | null>(BENCHMARK_SCANS[0]);

  const handleScanCompleted = (newScan: ScanRecord) => {
    setScans((prev) => [newScan, ...prev]);
    setSelectedScan(newScan);
  };

  const handleSelectScanForReport = (scan: ScanRecord) => {
    setSelectedScan(scan);
    setActiveTab('report');
  };

  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground">
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        user={user}
        onLogout={() => setUser(null)}
      />

      <main className="flex-1">
        <Suspense fallback={<PageSkeleton />}>
          {activeTab === 'landing' && (
            <LandingView
              onStartScan={() => setActiveTab('scan')}
              onExploreDashboard={() => setActiveTab('dashboard')}
            />
          )}

          {activeTab === 'dashboard' && (
            <DashboardView
              scans={scans}
              onSelectScan={handleSelectScanForReport}
              onNewScan={() => setActiveTab('scan')}
            />
          )}

          {activeTab === 'scan' && (
            <ScanUploadView
              onScanCompleted={handleScanCompleted}
              onViewReport={handleSelectScanForReport}
            />
          )}

          {activeTab === 'report' && selectedScan && (
            <ReportView
              scan={selectedScan}
              onBack={() => setActiveTab('dashboard')}
            />
          )}

          {activeTab === 'login' && (
            <LoginView
              onLoginSuccess={(loggedUser) => {
                setUser(loggedUser);
                setActiveTab('dashboard');
              }}
              onGoToRegister={() => setActiveTab('register')}
            />
          )}

          {activeTab === 'register' && (
            <RegisterView
              onRegisterSuccess={(newUser) => {
                setUser(newUser);
                setActiveTab('dashboard');
              }}
              onGoToLogin={() => setActiveTab('login')}
            />
          )}
        </Suspense>
      </main>

      {/* Footer */}
      <footer className="border-t border-[#1e3a5f] py-8 px-6 bg-[#0b132b] mt-16 shadow-3d-card">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="font-bold text-foreground text-sm">TrustNet AI</span>
            <span className="text-muted-foreground text-xs font-normal">
              &bull; Enterprise Forensic Intelligence &amp; Synthetic Media Defense
            </span>
          </div>

          <div className="flex items-center gap-5 text-xs text-muted-foreground">
            <span>TrustNet Vision AI</span>
            <span>Spectral &amp; Temporal Engines</span>
            <span>Zero-Trust Verification</span>
            <span>Enterprise Core</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
