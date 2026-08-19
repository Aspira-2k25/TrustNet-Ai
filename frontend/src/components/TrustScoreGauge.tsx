import React from 'react';
import type { RiskLevel } from '../types';

interface TrustScoreGaugeProps {
  score: number; // 0 to 100
  riskLevel: RiskLevel;
  size?: number;
  label?: string;
}

export const TrustScoreGauge: React.FC<TrustScoreGaugeProps> = ({
  score,
  riskLevel,
  size = 200,
  label = 'Risk Score',
}) => {
  const strokeWidth = 10;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const normalizedScore = Math.min(100, Math.max(0, score));
  const strokeDashoffset = circumference - (normalizedScore / 100) * circumference;

  const getColor = (level: RiskLevel) => {
    switch (level) {
      case 'LOW':
        return '#34d399';
      case 'MEDIUM':
        return '#fbbf24';
      case 'HIGH':
        return '#fb923c';
      case 'CRITICAL':
        return '#f87171';
      default:
        return '#818cf8';
    }
  };

  const getBadgeClasses = (level: RiskLevel) => {
    switch (level) {
      case 'LOW':
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
      case 'MEDIUM':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
      case 'HIGH':
        return 'bg-orange-500/10 text-orange-400 border-orange-500/20';
      case 'CRITICAL':
        return 'bg-red-500/10 text-red-400 border-red-500/20';
    }
  };

  const themeColor = getColor(riskLevel);

  return (
    <div className="flex flex-col items-center gap-3">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
          {/* Background Track */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="transparent"
            stroke="rgba(255, 255, 255, 0.06)"
            strokeWidth={strokeWidth}
          />
          {/* Animated Value Arc */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="transparent"
            stroke={themeColor}
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            style={{
              transition: 'stroke-dashoffset 1.2s cubic-bezier(0.4, 0, 0.2, 1), stroke 0.5s ease',
            }}
          />
        </svg>

        {/* Center Content */}
        <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
          <span
            className="font-mono font-bold text-white leading-none"
            style={{ fontSize: size * 0.26 }}
          >
            {normalizedScore}
          </span>
          <span
            className="font-medium text-slate-500 uppercase tracking-wider mt-1"
            style={{ fontSize: size * 0.07 }}
          >
            {label}
          </span>
        </div>
      </div>

      {/* Risk Level Badge */}
      <div className={`px-3.5 py-1 rounded-full text-xs font-semibold border ${getBadgeClasses(riskLevel)}`}>
        {riskLevel} Risk
      </div>
    </div>
  );
};
