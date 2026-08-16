import React from 'react';
import { Shield, LogOut } from 'lucide-react';
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
    { label: 'Analyze', tab: 'scan' },
    { label: 'History', tab: 'dashboard' },
  ];

  return (
    <header className="sticky top-0 z-50 bg-[#0f1117]/90 backdrop-blur-md border-b border-[#1e2231]">
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
        {/* Brand Logo */}
        <div
          onClick={() => setActiveTab('landing')}
          className="flex items-center gap-2.5 cursor-pointer select-none"
        >
          <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center">
            <Shield size={17} className="text-white" />
          </div>
          <span className="text-[17px] font-bold text-white tracking-tight">
            TrustNet
          </span>
        </div>

        {/* Center Nav Items */}
        <nav className="hidden md:flex items-center gap-1">
          {navItems.map((item) => (
            <button
              key={item.tab}
              onClick={() => setActiveTab(item.tab)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === item.tab
                  ? 'text-white bg-white/[0.07]'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]'
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
            className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold transition-colors"
          >
            Scan Now
          </button>

          {user && (
            <button
              onClick={onLogout}
              title="Logout"
              className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-white/[0.06] transition-colors"
            >
              <LogOut size={16} />
            </button>
          )}
        </div>
      </div>
    </header>
  );
};
