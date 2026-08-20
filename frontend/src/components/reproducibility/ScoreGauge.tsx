import { ShieldCheck, AlertTriangle, AlertCircle, Award } from 'lucide-react';
import type { CategoryScore } from './types';

interface ScoreGaugeProps {
  score: number;
  grade: string;
  venue: string;
  categories: CategoryScore[];
}

export function ScoreGauge({ score, grade, venue, categories }: Readonly<ScoreGaugeProps>) {
  const radius = 56;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (Math.min(100, Math.max(0, score)) / 100) * circumference;

  const getScoreColor = (val: number) => {
    if (val >= 90) return 'text-emerald-400 stroke-emerald-500';
    if (val >= 75) return 'text-blue-400 stroke-blue-500';
    if (val >= 60) return 'text-amber-400 stroke-amber-500';
    return 'text-rose-400 stroke-rose-500';
  };

  const colorClasses = getScoreColor(score);

  return (
    <div className="bg-surface border border-border rounded-xl p-5 shadow-sm flex flex-col md:flex-row items-center gap-6">
      {/* Radial Gauge */}
      <div className="relative flex items-center justify-center shrink-0">
        <svg className="w-36 h-36 -rotate-90 transform" viewBox="0 0 140 140">
          <circle
            cx="70"
            cy="70"
            r={radius}
            className="stroke-surface-hover/80"
            strokeWidth="10"
            fill="transparent"
          />
          <circle
            cx="70"
            cy="70"
            r={radius}
            className={`${colorClasses} transition-all duration-700 ease-out`}
            strokeWidth="10"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            fill="transparent"
          />
        </svg>
        <div className="absolute flex flex-col items-center justify-center text-center">
          <span className="text-3xl font-extrabold tracking-tight text-text">
            {score.toFixed(0)}
            <span className="text-sm font-normal text-text-dim">/100</span>
          </span>
          <div className="flex items-center gap-1 mt-0.5">
            <Award className="w-3.5 h-3.5 text-primary" />
            <span className="text-xs font-bold uppercase tracking-wider text-primary">{grade}</span>
          </div>
        </div>
      </div>

      {/* Overview & Breakdown */}
      <div className="flex-1 w-full flex flex-col gap-3">
        <div className="flex items-center justify-between border-b border-border pb-2">
          <div>
            <h3 className="text-sm font-semibold text-text">Reproducibility Index</h3>
            <p className="text-xs text-text-dim">
              Evaluated against <span className="font-semibold text-text uppercase">{venue}</span> conference checklist
            </p>
          </div>
          <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-primary/10 text-primary border border-primary/20">
            Certified Grade {grade}
          </span>
        </div>

        {/* Category Bars */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
          {categories.map((cat) => {
            const catColor = cat.score >= 80 ? 'bg-emerald-500' : cat.score >= 60 ? 'bg-amber-500' : 'bg-rose-500';
            const Icon = cat.score >= 80 ? ShieldCheck : cat.score >= 60 ? AlertTriangle : AlertCircle;
            const iconColor = cat.score >= 80 ? 'text-emerald-400' : cat.score >= 60 ? 'text-amber-400' : 'text-rose-400';

            return (
              <div key={cat.category} className="bg-bg/60 border border-border/60 rounded-lg p-2 flex flex-col gap-1">
                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-1.5 font-medium text-text capitalize">
                    <Icon className={`w-3.5 h-3.5 ${iconColor}`} />
                    <span>{cat.category}</span>
                  </div>
                  <span className="font-semibold text-text-dim">
                    {cat.score.toFixed(0)}%
                  </span>
                </div>
                <div className="w-full h-1.5 bg-surface-hover rounded-full overflow-hidden">
                  <div
                    className={`h-full ${catColor} rounded-full transition-all duration-500`}
                    style={{ width: `${Math.max(5, cat.score)}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
