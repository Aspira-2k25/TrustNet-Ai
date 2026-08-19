import { useState } from 'react';
import { Navbar } from './components/Navbar';
import { LandingView } from './views/LandingView';
import { DashboardView } from './views/DashboardView';
import { ScanUploadView } from './views/ScanUploadView';
import { ReportView } from './views/ReportView';
import { LoginView } from './views/LoginView';
import { RegisterView } from './views/RegisterView';
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
        },
        {
          feature_or_region: 'corneal_specular_inconsistency',
          contribution: 0.61,
          human_readable_note: 'Asymmetrical corneal light reflections across left and right pupils.',
        }
      ],
      analyzers: [
        { name: 'EfficientNet-B0 Convolutional Backbone', category: 'primary_ml', status: 'APPLIED', finding: 'Spatial feature divergence consistent with generative synthesis.' },
        { name: 'FFT High-Frequency Residual Analyzer', category: 'frequency', status: 'APPLIED', finding: 'Periodic grid artifacts detected in 2D Discrete Fourier Transform spectrum.' },
        { name: 'Error Level Analysis (ELA)', category: 'compression', status: 'APPLIED', finding: 'Inconsistent 8x8 DCT compression error levels across local regions.' },
        { name: 'Face Landmark & Boundary Warping (Face X-Ray)', category: 'face_forensics', status: 'APPLIED', finding: 'Blending boundary discontinuities identified along jawline and orbital regions.' },
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
        },
        {
          feature_or_region: 'fft_spectral_residuals',
          contribution: 0.74,
          human_readable_note: 'Checkerboard convolution artifacts identified in frequency spectrum.',
        }
      ],
      explanation: 'TrustNet synthesized a Risk Score of 88/100 (CRITICAL RISK). Deep learning inspection identified pronounced facial warping artifacts and frequency domain GAN residuals with 94% model confidence.',
      timestamp: new Date(Date.now() - 3600000 * 2).toISOString(),
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
    created_at: new Date(Date.now() - 3600000 * 8).toISOString(),
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
        },
        {
          feature_or_region: 'chromatic_aberration_continuity',
          contribution: 0.04,
          human_readable_note: 'Continuous radial chromatic aberration across optical elements.',
        }
      ],
      analyzers: [
        { name: 'EfficientNet-B0 Convolutional Backbone', category: 'primary_ml', status: 'APPLIED', finding: 'Natural texture distribution consistent with camera sensor capture.' },
        { name: 'FFT High-Frequency Residual Analyzer', category: 'frequency', status: 'APPLIED', finding: 'Uniform radial frequency roll-off.' },
        { name: 'Error Level Analysis (ELA)', category: 'compression', status: 'APPLIED', finding: 'Homogeneous compression surface.' },
        { name: 'Face Landmark & Boundary Warping (Face X-Ray)', category: 'face_forensics', status: 'APPLIED', finding: 'Consistent facial skin texture and natural specular eye reflections.' },
      ],
      processing_time_ms: 180,
      timestamp: new Date(Date.now() - 3600000 * 8).toISOString(),
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
      timestamp: new Date(Date.now() - 3600000 * 8).toISOString(),
    },
  },
  {
    id: 'scan-landscape-4821',
    user_id: 'usr-researcher-1',
    status: 'SUCCESS',
    content_type: 'image',
    filename: 'landscape_ai_generated_midjourney.png',
    file_size_bytes: 2105600,
    mime_type: 'image/png',
    created_at: new Date(Date.now() - 3600000 * 24).toISOString(),
    image_preview_url: 'https://images.unsplash.com/photo-1506744038136-46273834b3fb?w=500&auto=format&fit=crop&q=80',
    result: {
      scan_id: 'scan-landscape-4821',
      module: 'image_deepfake',
      detector_id: 'image_deepfake.efficientnet_b0.v1',
      model_version: 'v1.0.0',
      preprocessing_version: 'v1.0.0',
      native_score: 0.22,
      native_score_semantics: 'probability_of_negative_class',
      risk_score: 78,
      confidence: 0.91,
      label: 'fake',
      verdict: 'AI_GENERATED',
      has_face: false,
      status: 'SUCCESS',
      evidence: [
        {
          feature_or_region: 'fft_spectral_residuals',
          contribution: 0.82,
          human_readable_note: 'Periodic grid artifacts in 2D DFT spectrum consistent with diffusion model synthesis.',
        },
        {
          feature_or_region: 'compression_error_variance',
          contribution: 0.65,
          human_readable_note: 'Non-uniform Error Level Analysis surface across foreground and background elements.',
        },
      ],
      analyzers: [
        { name: 'EfficientNet-B0 Convolutional Backbone', category: 'primary_ml', status: 'APPLIED', finding: 'Spatial feature divergence consistent with diffusion model synthesis.' },
        { name: 'FFT High-Frequency Residual Analyzer', category: 'frequency', status: 'APPLIED', finding: 'Periodic grid artifacts in 2D DFT spectrum.' },
        { name: 'Error Level Analysis (ELA)', category: 'compression', status: 'APPLIED', finding: 'Non-uniform compression error surface.' },
        { name: 'Face Landmark & Boundary Warping (Face X-Ray)', category: 'face_forensics', status: 'SKIPPED', reason: 'No human facial landmark identified; skipped to prevent false positives.' },
      ],
      processing_time_ms: 162,
      timestamp: new Date(Date.now() - 3600000 * 24).toISOString(),
    },
    trust_score: {
      scan_id: 'scan-landscape-4821',
      trust_risk_score: 78,
      risk_level: 'HIGH',
      reporting_modules: ['image_deepfake'],
      module_scores: { 'image_deepfake': 78 },
      confidence: 0.91,
      contradiction_detected: false,
      evidence: [
        {
          feature_or_region: 'fft_spectral_residuals',
          contribution: 0.82,
          human_readable_note: 'Periodic grid artifacts in 2D DFT spectrum consistent with diffusion model synthesis.',
        },
      ],
      explanation: 'TrustNet synthesized a Risk Score of 78/100 (HIGH RISK). Frequency domain analysis revealed diffusion model synthesis patterns. Face X-Ray was skipped — no human face detected.',
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
    <div className="min-h-screen flex flex-col bg-[#0f1117] text-slate-200">
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        user={user}
        onLogout={() => setUser(null)}
      />

      <main className="flex-1">
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
      </main>

      {/* Footer */}
      <footer className="border-t border-[#1e2231] py-8 px-6 bg-[#0c0d12] mt-16">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="font-bold text-white text-sm">TrustNet</span>
            <span className="text-slate-500 text-xs font-normal">
              &bull; AI-Powered Forensic Intelligence &amp; Synthetic Media Defense
            </span>
          </div>

          <div className="flex items-center gap-5 text-xs text-slate-500">
            <span>Puter.js AI SDK</span>
            <span>2D Fourier FFT</span>
            <span>Fast ELA Detector</span>
            <span>FastAPI Core</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
