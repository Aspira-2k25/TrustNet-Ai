import { Shield, LogOut } from 'lucide-react';
import type { User } from '../types';
import { useResultLanguage } from '../services/resultLanguage.ts';

type Page = 'home' | 'dashboard' | 'scan' | 'login' | 'register' | 'report';
interface Props { activeTab: Page; setActiveTab: (page: Page) => void; user: User | null; onLogout: () => void }

export function Navbar({ activeTab, setActiveTab, user, onLogout }: Props) {
  const {language,setLanguage}=useResultLanguage();
  return <header className="workspace-header">
    <button className="brand" onClick={() => setActiveTab('home')} aria-label="TrustNet home">
      <Shield size={25} strokeWidth={1.6} aria-hidden="true"/>
      <span><strong>TrustNet</strong><small>Evidence workspace</small></span>
    </button>
    <nav aria-label="Main navigation">
      <button aria-current={activeTab === 'home' ? 'page' : undefined} onClick={() => setActiveTab('home')}>Home</button>
      <button aria-current={['scan','report'].includes(activeTab) ? 'page' : undefined} onClick={() => setActiveTab('scan')}>Checker</button>
      <button aria-current={activeTab === 'dashboard' ? 'page' : undefined} onClick={() => setActiveTab('dashboard')}>History</button>
    </nav>
    <div className="account-controls"><label className="text-sm"><span className="sr-only">Result language</span><select aria-label="Result language" value={language} onChange={e=>setLanguage(e.target.value==='hi'?'hi':'en')}><option value="en">English</option><option value="hi">Hindi / Hinglish</option></select></label>{user ? <>
      <span className="account-name">{user.email}</span>
      <button onClick={onLogout} aria-label="Sign out"><LogOut size={18}/></button>
    </> : <button className="primary-button" onClick={() => setActiveTab('login')}>Sign in</button>}</div>
  </header>;
}
