import React from 'react';
import { Shield, Globe, LogOut } from 'lucide-react';
import type { User } from '../types';

interface NavbarProps {
  activeTab: 'landing' | 'dashboard' | 'scan' | 'login' | 'register' | 'report';
  setActiveTab: (tab: 'landing' | 'dashboard' | 'scan' | 'login' | 'register' | 'report') => void;
  user: User | null;
  onLogout: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ activeTab, setActiveTab, user, onLogout }) => {
  return (
    <header className="sticky top-0 z-50 bg-[#08090d]/90 backdrop-blur-md border-b border-[#161922]">
      <div className="max-w-7xl mx-auto px-6 h-[68px] flex items-center justify-between">
        {/* Brand Logo */}
        <div
          onClick={() => setActiveTab('landing')}
          className="flex items-center gap-2.5 cursor-pointer select-none"
        >
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#ff4500] to-[#ff6b00] flex items-center justify-center shadow-lg shadow-orange-500/20">
            <Shield size={18} className="text-white" />
          </div>
          <div className="flex items-center tracking-wider">
            <span className="text-lg font-black text-white">TRUST</span>
            <span className="text-lg font-black text-[#ff4500]">[NET]</span>
          </div>
        </div>

        {/* Center Nav Items */}
        <nav className="hidden md:flex items-center gap-7 text-xs font-bold uppercase tracking-widest text-slate-400">
          <button
            onClick={() => setActiveTab('landing')}
            className={`transition-colors hover:text-white ${activeTab === 'landing' ? 'text-white' : ''}`}
          >
            HOME
          </button>
          <button
            onClick={() => setActiveTab('scan')}
            className={`relative py-1 transition-colors hover:text-white ${activeTab === 'scan' ? 'text-[#ff4500]' : ''}`}
          >
            ANALYZE
            {activeTab === 'scan' && (
              <span className="absolute bottom-0 left-0 right-0 h-[2px] bg-[#ff4500]" />
            )}
          </button>
          <button
            onClick={() => setActiveTab('dashboard')}
            className={`transition-colors hover:text-white ${activeTab === 'dashboard' ? 'text-white' : ''}`}
          >
            HISTORY
          </button>
          <a
            href="#learn"
            onClick={(e) => { e.preventDefault(); setActiveTab('landing'); }}
            className="transition-colors hover:text-white"
          >
            LEARN
          </a>
          <a
            href="#community"
            onClick={(e) => { e.preventDefault(); setActiveTab('landing'); }}
            className="transition-colors hover:text-white"
          >
            COMMUNITY
          </a>
        </nav>

        {/* Right Section */}
        <div className="flex items-center gap-4">
          <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded border border-[#212634] text-xs font-semibold text-slate-400">
            <Globe size={13} className="text-slate-400" />
            <span>ENGLISH</span>
          </div>

          <button
            onClick={() => setActiveTab('scan')}
            className="px-4 py-2 rounded bg-gradient-to-r from-[#ff4500] to-[#ff6b00] hover:from-[#ff5722] hover:to-[#ff7a1a] text-white text-xs font-black uppercase tracking-wider shadow-lg shadow-orange-500/25 transition-all"
          >
            SCAN NOW
          </button>

          {user && (
            <button
              onClick={onLogout}
              title="Logout"
              className="p-2 rounded border border-[#212634] text-slate-400 hover:text-rose-400 transition-colors"
            >
              <LogOut size={14} />
            </button>
          )}
        </div>
      </div>
    </header>
  );
};
