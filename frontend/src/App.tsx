import { Suspense, lazy, useState, useEffect } from 'react';
import { Navbar } from './components/Navbar';
import { PageSkeleton } from './components/Skeleton';

// Lazy load views for performance
const LandingView = lazy(() => import('./views/LandingView').then(m => ({ default: m.LandingView })));
const DashboardView = lazy(() => import('./views/DashboardView').then(m => ({ default: m.DashboardView })));
const ScanUploadView = lazy(() => import('./views/ScanUploadView').then(m => ({ default: m.ScanUploadView })));
const ReportView = lazy(() => import('./views/ReportView').then(m => ({ default: m.ReportView })));
const PhishingReport = lazy(() => import('./components/phishing_url/PhishingReport').then(m => ({ default: m.PhishingReport })));
const LoginView = lazy(() => import('./views/LoginView').then(m => ({ default: m.LoginView })));
const RegisterView = lazy(() => import('./views/RegisterView').then(m => ({ default: m.RegisterView })));
import { scanApi } from './services/api/scan.api';
import { authApi } from './services/api/auth.api';
import { httpClient } from './services/api/client';
import type { ScanRecord, User } from './types';

export function App() {
  const [activeTab, setActiveTab] = useState<'landing' | 'dashboard' | 'scan' | 'login' | 'register' | 'report'>('landing');
  const [user, setUser] = useState<User | null>(null);
  const [scans, setScans] = useState<ScanRecord[]>([]);
  const [selectedScan, setSelectedScan] = useState<ScanRecord | null>(null);
  const [historyError, setHistoryError] = useState('');
  useEffect(() => {
    const sessionToken = httpClient.getToken();
    if (sessionToken) authApi.getMe().then(current => {
      if (httpClient.getToken() === sessionToken) setUser(current);
    }).catch(() => {if (httpClient.getToken() === sessionToken) setUser(null);});
  }, []);
  useEffect(() => {
    let cancelled = false;
    const loadHistory = async () => {
      const loaded = new Map<string, ScanRecord>();
      let total = 0;
      for (let offset = 0; offset < 1000 && !cancelled; offset += 100) {
        const response = await scanApi.listScans(100, offset);
        total = response.data.total;
        for (const scan of response.data.scans) loaded.set(scan.id, scan);
        if (loaded.size >= total || response.data.scans.length < 100) break;
      }
      if (!cancelled) {
        setScans([...loaded.values()]);
        setHistoryError(total > loaded.size ? `Showing ${loaded.size} most recent persisted scans of ${total}. Older scans remain available through the API.` : '');
      }
    };
    loadHistory().catch((e: Error) => {if (!cancelled) {setScans([]);setHistoryError(`History unavailable: ${e.message}`);}});
    return () => {cancelled = true;};
  }, [user]);

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
        onLogout={() => {httpClient.setToken(null);setUser(null);setScans([]);setSelectedScan(null);setActiveTab('landing');}}
      />

      <main className="flex-1">
        {historyError && <p role="alert" className="text-amber-300 text-xs px-6 pt-4">{historyError}</p>}
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

          {activeTab === 'report' && selectedScan?.content_type === 'url' && (
            <PhishingReport scan={selectedScan} onBack={() => setActiveTab('dashboard')}/>
          )}
          {activeTab === 'report' && selectedScan && selectedScan.content_type !== 'url' && (
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
