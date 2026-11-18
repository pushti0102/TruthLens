import { useEffect, useState } from 'react';
import api from '../services/api';
import { useAuth } from '../store/AuthContext';
import {
  Shield, CheckCircle, AlertTriangle, XCircle, Cpu, Lock,
  Activity, BarChart2, Clock, Check
} from 'lucide-react';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts';

const VERDICT_COLORS = {
  VERIFIED_TRUSTED: '#22d3ee',
  VERIFIED_TRUSTED_WITH_AI_CONFLICT: '#a78bfa',
  SUSPICIOUS_AI: '#f59e0b',
  INTEGRITY_MISMATCH: '#f87171',
  INVALID_SIGNATURE: '#ef4444',
  INCONCLUSIVE: '#94a3b8',
};

function StatCard({ icon: Icon, label, value, sub, color = 'cyan' }) {
  const colorMap = {
    cyan: 'text-cyan-400 bg-cyan-400/10',
    green: 'text-green-400 bg-green-400/10',
    amber: 'text-amber-400 bg-amber-400/10',
    red: 'text-red-400 bg-red-400/10',
    purple: 'text-purple-400 bg-purple-400/10',
  };
  return (
    <div className="bg-slate-800 border border-slate-700 rounded-xl p-5 shadow-lg">
      <div className="flex items-center gap-3 mb-3">
        <div className={`p-2 rounded-lg ${colorMap[color]}`}>
          <Icon className={`h-5 w-5 ${colorMap[color].split(' ')[0]}`} />
        </div>
        <span className="text-slate-400 text-sm">{label}</span>
      </div>
      <p className="text-3xl font-bold text-white">{value ?? 0}</p>
      {sub && <p className="text-xs text-slate-500 mt-1">{sub}</p>}
    </div>
  );
}

function StatusBadge({ ok, label }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium ${
        ok ? 'bg-green-500/20 text-green-400 border border-green-500/30'
           : 'bg-red-500/20 text-red-400 border border-red-500/30'
      }`}
    >
      {ok ? <CheckCircle className="h-3 w-3" /> : <XCircle className="h-3 w-3" />}
      {label}
    </span>
  );
}

function VerdictBadge({ verdict }) {
  const cfg = {
    VERIFIED_TRUSTED: { color: 'text-cyan-400 bg-cyan-400/10 border-cyan-400/20', label: 'Trusted' },
    INTEGRITY_MISMATCH: { color: 'text-red-400 bg-red-400/10 border-red-400/20', label: 'Mismatch' },
    INVALID_SIGNATURE: { color: 'text-red-400 bg-red-400/10 border-red-400/20', label: 'Bad Sig' },
    SUSPICIOUS_AI: { color: 'text-amber-400 bg-amber-400/10 border-amber-400/20', label: 'Suspicious' },
    INCONCLUSIVE: { color: 'text-slate-400 bg-slate-400/10 border-slate-400/20', label: 'Inconclusive' },
    VERIFIED_TRUSTED_WITH_AI_CONFLICT: { color: 'text-purple-400 bg-purple-400/10 border-purple-400/20', label: 'AI Conflict' },
  }[verdict] || { color: 'text-slate-400 bg-slate-700', label: verdict || 'Unknown' };

  return (
    <span className={`text-xs px-2.5 py-0.5 rounded-full border font-medium ${cfg.color}`}>
      {cfg.label}
    </span>
  );
}

export default function Dashboard() {
  const { user } = useAuth();
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    api.get('/api/dashboard/summary')
      .then((r) => setSummary(r.data))
      .catch(() => setError('Failed to load dashboard data.'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-80">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-cyan-400" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-80 text-red-400">
        <AlertTriangle className="h-5 w-5 mr-2" /> {error}
      </div>
    );
  }

  const pieData = summary
    ? [
        { name: 'VERIFIED_TRUSTED', value: summary.provenance_matched },
        { name: 'INTEGRITY_MISMATCH', value: summary.integrity_mismatches },
        { name: 'INCONCLUSIVE', value: summary.unregistered_count },
      ].filter((d) => d.value > 0)
    : [];

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">
            Welcome back, <span className="text-cyan-400">{user?.full_name || user?.email}</span>
          </h1>
          <p className="text-slate-400 text-sm mt-1">TruthLens Media Verification Platform</p>
        </div>
        {/* System status badges */}
        <div className="flex flex-wrap gap-2.5">
          <StatusBadge ok={true} label="Database (SQLite)" />
          <StatusBadge ok={summary?.crypto_ready} label="Cryptography (ECDSA)" />
          <StatusBadge ok={summary?.model_ready} label="AI Detection (ViT)" />
        </div>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={Shield} label="Total Verifications" value={summary?.total_verifications} color="cyan" />
        <StatCard icon={Cpu} label="AI Analyses" value={summary?.ai_analyses_completed} color="purple" />
        <StatCard icon={Lock} label="Verified Provenance" value={summary?.provenance_matched} color="green" />
        <StatCard icon={AlertTriangle} label="Integrity Mismatches" value={summary?.integrity_mismatches} color="red" />
      </div>

      {/* Chart + recent */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Verdict distribution chart */}
        <div className="bg-slate-800 border border-slate-700 rounded-xl p-6 shadow-lg">
          <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
            <BarChart2 className="h-5 w-5 text-cyan-400" /> Verdict Distribution
          </h3>
          {pieData.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  dataKey="value"
                  paddingAngle={3}
                >
                  {pieData.map((entry) => (
                    <Cell key={entry.name} fill={VERDICT_COLORS[entry.name] || '#64748b'} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
                  itemStyle={{ color: '#e2e8f0' }}
                />
                <Legend formatter={(v) => <span className="text-slate-400 text-xs">{v.replace(/_/g, ' ')}</span>} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-48 text-slate-500 text-sm">
              No verification data yet. Upload some media to get started!
            </div>
          )}
        </div>

        {/* Recent verifications */}
        <div className="bg-slate-800 border border-slate-700 rounded-xl p-6 shadow-lg">
          <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
            <Clock className="h-5 w-5 text-cyan-400" /> Recent Verifications
          </h3>
          {summary?.recent_activity?.length > 0 ? (
            <div className="space-y-3 max-h-[260px] overflow-y-auto pr-1">
              {summary.recent_activity.map((v) => (
                <div key={v.id} className="flex items-center justify-between py-2 border-b border-slate-700/60 last:border-0">
                  <div className="min-w-0 pr-2">
                    <p className="text-white text-sm font-medium truncate">{v.filename}</p>
                    <p className="text-slate-500 text-xs">{v.created_at}</p>
                  </div>
                  <div className="flex-shrink-0">
                    <VerdictBadge verdict={v.overall_status} />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex items-center justify-center h-48 text-slate-500 text-sm">
              No recent verifications.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
