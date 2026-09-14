import React, { useState } from 'react';
import { Lock, Mail, AlertCircle, ArrowRight, Shield, User as UserIcon } from 'lucide-react';
import { api } from '../services/api';
import type { User } from '../types';

interface RegisterViewProps {
  onRegisterSuccess: (user: User) => void;
  onGoToLogin: () => void;
}

export const RegisterView: React.FC<RegisterViewProps> = ({ onRegisterSuccess, onGoToLogin }) => {
  const [name, setName] = useState<string>('Alex Johnson');
  const [email, setEmail] = useState<string>('alex@example.com');
  const [password, setPassword] = useState<string>('SecurePass123!');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      const { user } = await api.register(email, password, 'user');
      onRegisterSuccess(user);
    } catch (err: any) {
      setError(err.message || 'Registration failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto mt-12 px-6 mb-12">
      {/* Header */}
      <div className="text-center mb-6">
        <div className="w-12 h-12 rounded-xl bg-[#111d38] border border-[#00b4d8]/40 flex items-center justify-center mx-auto mb-3 shadow-3d-sm">
          <Shield size={24} className="text-[#00b4d8] fill-[#00b4d8]/20" />
        </div>
        <h1 className="text-2xl font-bold text-[#f8fafc] font-serif tracking-tight">
          Create an Account
        </h1>
        <p className="text-xs text-[#94a3b8] mt-1">
          Join TrustNet to easily check images, videos, audio, text messages, and links.
        </p>
      </div>

      <div className="bg-[#111d38] border border-[#1e3a5f] rounded-2xl p-7 shadow-3d-card">
        {error && (
          <div className="flex items-center gap-2 p-3.5 rounded-xl bg-red-950/70 border border-red-800 text-red-300 text-xs mb-5 shadow-sm">
            <AlertCircle size={16} className="text-red-400 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <label className="block text-xs font-bold text-[#94a3b8] mb-1.5">
              Full Name
            </label>
            <div className="flex items-center gap-2.5 px-3.5 py-2.5 rounded-xl bg-[#0b132b] border border-[#1e3a5f] focus-within:border-[#00b4d8] transition-all">
              <UserIcon size={16} className="text-[#64748b]" />
              <input
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Alex Johnson"
                className="bg-transparent border-none outline-none text-xs text-[#f8fafc] w-full placeholder:text-[#64748b]"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold text-[#94a3b8] mb-1.5">
              Email Address
            </label>
            <div className="flex items-center gap-2.5 px-3.5 py-2.5 rounded-xl bg-[#0b132b] border border-[#1e3a5f] focus-within:border-[#00b4d8] transition-all">
              <Mail size={16} className="text-[#64748b]" />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="bg-transparent border-none outline-none text-xs text-[#f8fafc] w-full placeholder:text-[#64748b]"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold text-[#94a3b8] mb-1.5">
              Password
            </label>
            <div className="flex items-center gap-2.5 px-3.5 py-2.5 rounded-xl bg-[#0b132b] border border-[#1e3a5f] focus-within:border-[#00b4d8] transition-all">
              <Lock size={16} className="text-[#64748b]" />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="bg-transparent border-none outline-none text-xs text-[#f8fafc] w-full placeholder:text-[#64748b]"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className={`mt-3 py-3 rounded-xl font-bold text-xs flex items-center justify-center gap-2 transition-all cursor-pointer shadow-3d-sm ${
              isLoading
                ? 'bg-[#1c2541] text-[#64748b] border border-[#1e3a5f] cursor-not-allowed'
                : 'bg-[#0077b6] hover:bg-[#0096c7] text-white'
            }`}
          >
            <span>{isLoading ? 'Creating Account...' : 'Create Account'}</span>
            <ArrowRight size={14} />
          </button>
        </form>

        <div className="mt-6 pt-4 border-t border-[#1e3a5f] text-center">
          <p className="text-xs text-[#94a3b8]">
            Already have an account?{' '}
            <button
              onClick={onGoToLogin}
              className="text-[#00b4d8] hover:text-[#38bdf8] font-bold cursor-pointer transition-colors"
            >
              Sign In
            </button>
          </p>
        </div>
      </div>
    </div>
  );
};
