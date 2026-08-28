import React from "react";

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  badge?: string;
  badgeColor?: "emerald" | "blue" | "amber" | "indigo" | "rose" | "sky" | "orange";
  trend?: string;
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  subtitle,
  badge,
  badgeColor = "emerald",
}) => {
  const badgeColorMap = {
    emerald: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
    blue: "bg-blue-500/10 text-blue-400 border-blue-500/30",
    amber: "bg-amber-500/10 text-amber-400 border-amber-500/30",
    indigo: "bg-indigo-500/10 text-indigo-400 border-indigo-500/30",
    rose: "bg-rose-500/10 text-rose-400 border-rose-500/30",
    sky: "bg-sky-500/10 text-sky-400 border-sky-500/30",
    orange: "bg-orange-500/10 text-orange-400 border-orange-500/30",
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col justify-between hover:border-slate-700 transition-colors shadow-sm">
      <div className="flex items-center justify-between gap-2 mb-2">
        <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
          {title}
        </span>
        {badge && (
          <span
            className={`text-xs px-2 py-0.5 rounded border font-medium ${badgeColorMap[badgeColor]}`}
          >
            {badge}
          </span>
        )}
      </div>
      <div>
        <div className="text-2xl font-extrabold text-white tracking-tight">{value}</div>
        {subtitle && <div className="text-xs text-slate-400 mt-1">{subtitle}</div>}
      </div>
    </div>
  );
};
