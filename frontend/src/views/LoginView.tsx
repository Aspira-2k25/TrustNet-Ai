import React, { useState } from 'react';
import { LogIn, Lock, Mail, AlertCircle, ArrowRight } from 'lucide-react';
import { api } from '../services/api';
import type { User } from '../types';

interface LoginViewProps {
  onLoginSuccess: (user: User) => void;
  onGoToRegister: () => void;
}

export const LoginView: React.FC<LoginViewProps> = ({ onLoginSuccess, onGoToRegister }) => {
  const [email, setEmail] = useState<string>('analyst@trustnet.ai');
  const [password, setPassword] = useState<string>('SecurePassword123!');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      const { user } = await api.login(email, password);
      onLoginSuccess(user);
    } catch (err: any) {
      setError(err.message || 'Failed to authenticate.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto mt-20 px-6">
      <div className="bg-[#13161f] border border-[#1e2231] rounded-2xl p-9">
        <div className="text-center mb-7">
          <div className="w-12 h-12 rounded-xl bg-indigo-600 flex items-center justify-center mx-auto mb-4">
            <LogIn size={22} color="#ffffff" />
          </div>
          <h1 className="text-2xl font-bold text-white mb-1.5">
            Welcome Back
          </h1>
          <p className="text-sm text-slate-400">
            Sign in to access forensic scan history and telemetry
          </p>
        </div>

        {error && (
          <div className="flex items-center gap-2 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-300 text-xs mb-5">
            <AlertCircle size={16} className="text-red-400 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col gap-5">
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">
              Email Address
            </label>
            <div className="flex items-center gap-2.5 px-3.5 py-2.5 rounded-lg bg-[#0f1117] border border-[#1e2231] focus-within:border-indigo-500/40 transition-colors">
              <Mail size={16} className="text-slate-500" />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="bg-transparent border-none outline-none text-sm text-white w-full placeholder:text-slate-600"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">
              Password
            </label>
            <div className="flex items-center gap-2.5 px-3.5 py-2.5 rounded-lg bg-[#0f1117] border border-[#1e2231] focus-within:border-indigo-500/40 transition-colors">
              <Lock size={16} className="text-slate-500" />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="bg-transparent border-none outline-none text-sm text-white w-full placeholder:text-slate-600"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className={`flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-semibold mt-2 transition-all ${isLoading ? 'bg-[#1a1e2a] text-slate-500 cursor-not-allowed' : 'bg-indigo-600 hover:bg-indigo-500 text-white'}`}
          >
            {isLoading ? 'Authenticating...' : 'Sign In'}
            <ArrowRight size={16} />
          </button>
        </form>

        <div className="text-center mt-6 text-xs text-slate-500">
          Don't have an account?{' '}
          <span
            onClick={onGoToRegister}
            className="text-indigo-400 cursor-pointer font-medium hover:text-indigo-300"
          >
            Create Researcher Account
          </span>
        </div>
      </div>
    </div>
  );
};
