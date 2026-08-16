import React, { useState } from 'react';
import { UserPlus, Lock, Mail, AlertCircle, ArrowRight, Briefcase } from 'lucide-react';
import { api } from '../services/api';
import type { User } from '../types';

interface RegisterViewProps {
  onRegisterSuccess: (user: User) => void;
  onGoToLogin: () => void;
}

export const RegisterView: React.FC<RegisterViewProps> = ({ onRegisterSuccess, onGoToLogin }) => {
  const [email, setEmail] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [confirmPassword, setConfirmPassword] = useState<string>('');
  const [role, setRole] = useState<string>('researcher');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    if (password.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }

    setIsLoading(true);
    try {
      const { user } = await api.register(email, password, role);
      onRegisterSuccess(user);
    } catch (err: any) {
      setError(err.message || 'Registration failed.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto mt-16 px-6">
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-9 shadow-sm">
        <div className="text-center mb-7">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center mx-auto mb-4">
            <UserPlus size={24} color="#ffffff" />
          </div>
          <h1 className="text-2xl font-extrabold text-white mb-1.5">
            Create Account
          </h1>
          <p className="text-sm text-slate-400">
            Register as a TrustNet forensic analyst or researcher
          </p>
        </div>

        {error && (
          <div className="flex items-center gap-2 p-3 rounded-lg bg-rose-950/40 border border-rose-800/60 text-rose-300 text-xs mb-5">
            <AlertCircle size={16} className="text-rose-400 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <label className="block text-xs font-semibold text-slate-400 mb-1.5">
              Email Address
            </label>
            <div className="flex items-center gap-2.5 px-3.5 py-2.5 rounded-lg bg-slate-950 border border-slate-800">
              <Mail size={16} className="text-slate-500" />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@institution.edu"
                className="bg-transparent border-none outline-none text-sm text-white w-full placeholder:text-slate-600"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-400 mb-1.5">
              Password
            </label>
            <div className="flex items-center gap-2.5 px-3.5 py-2.5 rounded-lg bg-slate-950 border border-slate-800">
              <Lock size={16} className="text-slate-500" />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Min. 8 characters"
                className="bg-transparent border-none outline-none text-sm text-white w-full placeholder:text-slate-600"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-400 mb-1.5">
              Confirm Password
            </label>
            <div className="flex items-center gap-2.5 px-3.5 py-2.5 rounded-lg bg-slate-950 border border-slate-800">
              <Lock size={16} className="text-slate-500" />
              <input
                type="password"
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="bg-transparent border-none outline-none text-sm text-white w-full placeholder:text-slate-600"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-400 mb-1.5">
              Role
            </label>
            <div className="flex items-center gap-2.5 px-3.5 py-2.5 rounded-lg bg-slate-950 border border-slate-800">
              <Briefcase size={16} className="text-slate-500" />
              <select
                value={role}
                onChange={(e) => setRole(e.target.value)}
                className="bg-transparent border-none outline-none text-sm text-white w-full appearance-none cursor-pointer"
              >
                <option value="researcher" className="bg-slate-900 text-white">Researcher</option>
                <option value="analyst" className="bg-slate-900 text-white">Analyst</option>
              </select>
            </div>
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className={`flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-bold mt-2 transition-all ${isLoading ? 'bg-slate-800 text-slate-500 cursor-not-allowed' : 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-lg shadow-indigo-600/30 hover:from-indigo-500 hover:to-purple-500'}`}
          >
            {isLoading ? 'Creating Account...' : 'Create Account'}
            <ArrowRight size={16} />
          </button>
        </form>

        <div className="text-center mt-6 text-xs text-slate-500">
          Already have an account?{' '}
          <span
            onClick={onGoToLogin}
            className="text-indigo-400 cursor-pointer font-semibold hover:text-indigo-300"
          >
            Sign In
          </span>
        </div>
      </div>
    </div>
  );
};
