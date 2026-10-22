import React, { useState } from 'react';
import { Lock, Mail, AlertCircle, ArrowRight, Shield } from 'lucide-react';
import { api } from '../services/api';
import type { User } from '../types';

interface LoginViewProps {
  onLoginSuccess: (user: User) => void;
  onGoToRegister: () => void;
}

export const LoginView: React.FC<LoginViewProps> = ({ onLoginSuccess, onGoToRegister }) => {
  const [email, setEmail] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      const { user } = await api.login(email, password);
      onLoginSuccess(user);
      if (window.opener && !window.opener.closed) {
        try {
          window.opener.postMessage({ type: 'TRUSTNET_LOGIN_SUCCESS', user }, '*');
        } catch {}
        setTimeout(() => {
          try { window.close(); } catch {}
        }, 600);
      }
    } catch (err: any) {
      setError(err.message || 'Login failed. Please check your email and password.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto mt-14 px-6">
      {/* Header */}
      <div className="text-center mb-6">
        <div className="w-12 h-12 rounded-xl bg-white border border-[#24695b]/40 flex items-center justify-center mx-auto mb-3 ">
          <Shield size={24} className="text-[#24695b] fill-[#24695b]/20" />
        </div>
        <h1 className="text-2xl font-bold text-[#202b31] font-sans tracking-tight">
          Welcome Back
        </h1>
        <p className="text-xs text-[#53636d] mt-1">
          Sign in to your TrustNet account to view your past checks and reports.
        </p>
      </div>

      <div className="bg-white border border-[#cbd3d7] rounded-2xl p-7 ">
        {error && (
          <div className="flex items-center gap-2 p-3.5 rounded-xl bg-red-50/70 border border-red-800 text-red-800 text-xs mb-5 shadow-sm">
            <AlertCircle size={16} className="text-red-400 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <label className="block text-xs font-bold text-[#53636d] mb-1.5">
              Email Address
            </label>
            <div className="flex items-center gap-2.5 px-3.5 py-2.5 rounded-xl bg-white border border-[#cbd3d7] focus-within:border-[#24695b] transition-all">
              <Mail size={16} className="text-[#53636d]" />
              <input
                type="email"
                aria-label="Email address"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="bg-transparent border-none outline-none text-xs text-[#202b31] w-full placeholder:text-[#53636d]"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold text-[#53636d] mb-1.5">
              Password
            </label>
            <div className="flex items-center gap-2.5 px-3.5 py-2.5 rounded-xl bg-white border border-[#cbd3d7] focus-within:border-[#24695b] transition-all">
              <Lock size={16} className="text-[#53636d]" />
              <input
                type="password"
                aria-label="Password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="bg-transparent border-none outline-none text-xs text-[#202b31] w-full placeholder:text-[#53636d]"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className={`mt-3 py-3 rounded-xl font-bold text-xs flex items-center justify-center gap-2 transition-all cursor-pointer  ${
              isLoading
                ? 'bg-[#e8ece7] text-[#53636d] border border-[#cbd3d7] cursor-not-allowed'
                : 'bg-[#24695b] hover:bg-[#194b40] text-white'
            }`}
          >
            <span>{isLoading ? 'Signing In...' : 'Sign In'}</span>
            <ArrowRight size={14} />
          </button>
        </form>

        <div className="mt-6 pt-4 border-t border-[#cbd3d7] text-center">
          <p className="text-xs text-[#53636d]">
            Don't have an account yet?{' '}
            <button
              onClick={onGoToRegister}
              className="text-[#24695b] hover:text-[#194b40] font-bold cursor-pointer transition-colors"
            >
              Create Account
            </button>
          </p>
        </div>
      </div>
    </div>
  );
};
