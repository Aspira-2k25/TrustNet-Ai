import React from 'react';
import { Shield, LogOut, User as UserIcon } from 'lucide-react';
import type { User } from '../types';

interface NavbarProps {
  activeTab: 'landing' | 'dashboard' | 'scan' | 'login' | 'register' | 'report';
  setActiveTab: (tab: 'landing' | 'dashboard' | 'scan' | 'login' | 'register' | 'report') => void;
  user: User | null;
  onLogout: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ activeTab, setActiveTab, user, onLogout }) => {
  const navItems: { label: string; tab: 'landing' | 'scan' | 'dashboard' }[] = [
    { label: 'Home', tab: 'landing' },
    { label: 'Threat Scanner (All 6 Types)', tab: 'scan' },
    { label: 'Scan History', tab: 'dashboard' },
  ];

  return (
    <header className="sticky top-0 z-50 bg-[#0b132b]/95 backdrop-blur-md border-b border-[#1e3a5f] shadow-3d-card">
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
        {/* Brand Logo */}
        <div
          onClick={() => setActiveTab('landing')}
          className="flex items-center gap-3 cursor-pointer select-none group"
        >
          <div className="w-10 h-10 rounded-xl bg-[#111d38] border border-[#00b4d8]/40 flex items-center justify-center shadow-3d-sm group-hover:scale-105 transition-transform">
            <Shield size={20} className="text-[#00b4d8] fill-[#00b4d8]/20" />
          </div>

          <div className="flex flex-col">
            <span className="text-xl font-bold text-[#f8fafc] tracking-tight font-serif">
              TrustNet <span className="text-[#00b4d8] font-sans font-black">AI</span>
            </span>
            <span className="text-[11px] text-[#94a3b8] font-medium">
              Digital Trust &amp; Cyber Scam Defense
            </span>
          </div>
        </div>

        {/* Center Nav Items */}
        <nav className="hidden md:flex items-center gap-1.5 p-1 rounded-xl bg-[#080e20] border border-[#1e3a5f]">
          {navItems.map((item) => (
            <button
              key={item.tab}
              onClick={() => setActiveTab(item.tab)}
              className={`px-4 py-2 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                activeTab === item.tab
                  ? 'text-white bg-[#0077b6] shadow-sm'
                  : 'text-[#94a3b8] hover:text-[#f8fafc] hover:bg-[#111d38]'
              }`}
            >
              {item.label}
            </button>
          ))}
        </nav>

        {/* Right Section */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => setActiveTab('scan')}
            className="px-4 py-2 rounded-xl bg-[#0077b6] hover:bg-[#0096c7] text-white text-xs font-bold transition-all shadow-3d-sm flex items-center gap-1.5 cursor-pointer"
          >
            <span>Scan Something Now</span>
          </button>

          {user ? (
            <div className="flex items-center gap-2">
              <span className="hidden sm:inline-block text-xs font-semibold text-[#cbd5e1] max-w-[150px] truncate" title={user.email}>
                {user.email}
              </span>
              <button
                onClick={onLogout}
                title="Sign Out"
                className="p-2 rounded-xl text-[#94a3b8] hover:text-red-400 hover:bg-red-950/40 border border-[#1e3a5f] transition-all cursor-pointer"
              >
                <LogOut size={16} />
              </button>
            </div>
          ) : (
            <button
              onClick={() => setActiveTab('login')}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold text-[#cbd5e1] hover:text-white hover:bg-[#111d38] border border-[#1e3a5f] transition-all cursor-pointer"
            >
              <UserIcon size={14} className="text-[#00b4d8]" />
              <span>Sign In</span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
};
