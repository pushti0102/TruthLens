import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../services/api';
import { useAuth } from '../store/AuthContext';
import {
  ShieldCheck,
  AlertTriangle,
  XCircle,
  Cpu,
  Lock,
  BarChart2,
  Clock,
  CheckCircle2,
  ArrowRight,
  HelpCircle,
  FileSearch,
  ExternalLink
} from 'lucide-react';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts';

const VERDICT_COLORS = {
  VERIFIED_TRUSTED: '#22C55E',
  VERIFIED_TRUSTED_WITH_AI_CONFLICT: '#A78BFA',
  SUSPICIOUS_AI: '#F59E0B',
  INTEGRITY_MISMATCH: '#EF4444',
  INVALID_SIGNATURE: '#EF4444',
  INCONCLUSIVE: '#94A3B8',
};

function MetricCard({ icon: Icon, label, value, sub, statusColor = 'purple' }) {
  const iconStyles = {
    purple: 'text-brand-purple-light bg-brand-purple/10 border-brand-purple/20',
    green: 'text-status-genuine bg-status-genuine/10 border-status-genuine/20',
    amber: 'text-status-warning bg-status-warning/10 border-status-warning/20',
    red: 'text-status-invalid bg-status-invalid/10 border-status-invalid/20',
    neutral: 'text-text-muted bg-dark-elevated border-dark-border',
  }[statusColor] || 'text-brand-purple-light bg-brand-purple/10 border-brand-purple/20';

  return (
    <div className="bg-dark-card border border-dark-border rounded-lg p-5 flex flex-col justify-between shadow-xs hover:border-dark-border/80 transition-all">
      <div className="flex items-center justify-between mb-3">
        <span className="text-text-muted text-xs font-medium uppercase tracking-wider">{label}</span>
        <div className={`p-2 rounded-lg border ${iconStyles}`}>
          <Icon className="h-4 w-4" />
        </div>
      </div>
      <div>
        <div className="text-2xl lg:text-3xl font-bold text-text-main font-mono tracking-tight">
          {typeof value === 'number' ? value.toLocaleString() : (value ?? 0)}
        </div>
        {sub && <p className="text-[11px] text-text-muted mt-1">{sub}</p>}
      </div>
    </div>
  );
}

function StatusIndicator({ ok, label }) {
  return (
    <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-dark-elevated border border-dark-border text-xs">
      <span className={`h-2 w-2 rounded-full ${ok ? 'bg-status-genuine' : 'bg-status-invalid'}`} />
      <span className="text-text-main font-medium">{label}</span>
      <span className="text-[10px] text-text-muted">({ok ? 'Active' : 'Offline'})</span>
    </div>
  );
}

function VerdictBadge({ verdict }) {
  const cfg = {
    VERIFIED_TRUSTED: {
      color: 'text-status-genuine bg-status-genuine/10 border-status-genuine/20',
      label: 'Verified Trusted',
      icon: CheckCircle2,
    },
    INTEGRITY_MISMATCH: {
      color: 'text-status-invalid bg-status-invalid/10 border-status-invalid/20',
      label: 'Tamper Detected',
      icon: XCircle,
    },
    INVALID_SIGNATURE: {
      color: 'text-status-invalid bg-status-invalid/10 border-status-invalid/20',
      label: 'Invalid Signature',
      icon: XCircle,
    },
    SUSPICIOUS_AI: {
      color: 'text-status-warning bg-status-warning/10 border-status-warning/20',
      label: 'AI Generated',
      icon: AlertTriangle,
    },
    INCONCLUSIVE: {
      color: 'text-text-muted bg-dark-elevated border-dark-border',
      label: 'Inconclusive',
      icon: HelpCircle,
    },
    VERIFIED_TRUSTED_WITH_AI_CONFLICT: {
      color: 'text-brand-purple-light bg-brand-purple/10 border-brand-purple/20',
      label: 'Trusted (AI Conflict)',
      icon: CheckCircle2,
    },
  }[verdict] || {
    color: 'text-text-muted bg-dark-elevated border-dark-border',
    label: verdict ? verdict.replace(/_/g, ' ') : 'Unknown',
    icon: HelpCircle,
  };

  const Icon = cfg.icon;

  return (
    <span className={`inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded border font-medium ${cfg.color}`}>
      <Icon className="h-3 w-3 shrink-0" />
      <span>{cfg.label}</span>
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
      .catch(() => setError('Failed to retrieve system forensics summary.'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-3">
        <div className="animate-spin rounded-full h-8 w-8 border-2 border-brand-purple border-t-transparent" />
        <span className="text-text-muted text-xs font-mono uppercase tracking-wider">Loading forensics metrics...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-7xl mx-auto p-6 md:p-8">
        <div className="p-4 rounded-lg bg-status-invalid/10 border border-status-invalid/20 text-status-invalid flex items-center gap-3">
          <AlertTriangle className="h-5 w-5 shrink-0" />
          <span className="text-sm font-medium">{error}</span>
        </div>
      </div>
    );
  }

  const pieData = summary
    ? [
        { name: 'VERIFIED_TRUSTED', displayName: 'Verified Provenance', value: summary.provenance_matched },
        { name: 'SUSPICIOUS_AI', displayName: 'AI Flagged', value: summary.ai_analyses_completed ? Math.max(0, summary.total_verifications - summary.provenance_matched - summary.integrity_mismatches - summary.unregistered_count) : 0 },
        { name: 'INTEGRITY_MISMATCH', displayName: 'Integrity Tampered', value: summary.integrity_mismatches },
        { name: 'INCONCLUSIVE', displayName: 'Unregistered / Inconclusive', value: summary.unregistered_count },
      ].filter((d) => d.value > 0)
    : [];

  return (
    <div className="max-w-7xl mx-auto p-6 md:p-8 lg:p-10 space-y-8">
      {/* SaaS Welcome Banner */}
      <div className="bg-dark-card border border-dark-border rounded-lg p-6 lg:p-8 flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="space-y-2 max-w-2xl">
          <div className="inline-flex items-center gap-2 px-2.5 py-0.5 rounded text-[11px] font-mono bg-brand-purple/10 text-brand-purple-light border border-brand-purple/20">
            <span>MEDIA AUTHENTICITY INTELLIGENCE</span>
          </div>
          <h1 className="text-2xl lg:text-3xl font-bold text-text-main tracking-tight">
            Verify digital media. Examine evidence. Build trust.
          </h1>
          <p className="text-text-muted text-sm leading-relaxed">
            TruthLens combines multi-model deep learning forensics, SHA-256 cryptographic hashing, and ECDSA digital signatures to evaluate media authenticity and provenance.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 shrink-0">
          <Link
            to="/verify"
            className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-lg bg-brand-purple hover:bg-brand-purple-light text-white font-medium text-sm transition-all shadow-xs"
          >
            <ShieldCheck className="h-4 w-4" />
            <span>Verify Media</span>
            <ArrowRight className="h-4 w-4 ml-1" />
          </Link>
          <Link
            to="/history"
            className="inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-dark-elevated hover:bg-dark-border text-text-main font-medium text-sm border border-dark-border transition-all"
          >
            <Clock className="h-4 w-4 text-text-muted" />
            <span>View Logs</span>
          </Link>
        </div>
      </div>

      {/* System Engine Health Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 rounded-lg bg-dark-card border border-dark-border text-xs">
        <span className="text-text-muted uppercase tracking-wider font-semibold text-[11px] flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-status-genuine animate-pulse" />
          Forensic Core Subsystems
        </span>
        <div className="flex flex-wrap items-center gap-2.5">
          <StatusIndicator ok={true} label="Storage (SQLite)" />
          <StatusIndicator ok={summary?.crypto_ready ?? true} label="Crypto Engine (ECDSA / SHA-256)" />
          <StatusIndicator ok={summary?.model_ready ?? true} label="AI Vision Forensics" />
        </div>
      </div>

      {/* 4 Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          icon={FileSearch}
          label="Total Verifications"
          value={summary?.total_verifications}
          sub="All forensic inspections recorded"
          statusColor="purple"
        />
        <MetricCard
          icon={Lock}
          label="Genuine Provenance"
          value={summary?.provenance_matched}
          sub="Cryptographically signed & verified"
          statusColor="green"
        />
        <MetricCard
          icon={AlertTriangle}
          label="Integrity Tampered"
          value={summary?.integrity_mismatches}
          sub="Hash mismatch or signature failure"
          statusColor="red"
        />
        <MetricCard
          icon={HelpCircle}
          label="Unregistered / Inconclusive"
          value={summary?.unregistered_count}
          sub="No cryptographic publisher record"
          statusColor="neutral"
        />
      </div>

      {/* Analytics & Activity Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Verdict Distribution */}
        <div className="bg-dark-card border border-dark-border rounded-lg p-6 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <BarChart2 className="h-4 w-4 text-brand-purple-light" />
              <h3 className="text-text-main font-semibold text-sm">Verdict Distribution</h3>
            </div>
            <span className="text-[11px] font-mono text-text-muted">Aggregated Results</span>
          </div>

          {pieData.length > 0 ? (
            <div className="w-full h-64">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={55}
                    outerRadius={85}
                    dataKey="value"
                    paddingAngle={3}
                  >
                    {pieData.map((entry) => (
                      <Cell
                        key={entry.name}
                        fill={VERDICT_COLORS[entry.name] || '#94A3B8'}
                        stroke="#111827"
                        strokeWidth={2}
                      />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#18212F',
                      border: '1px solid #2B3645',
                      borderRadius: '0.375rem',
                      color: '#F8FAFC',
                      fontSize: '12px',
                    }}
                    itemStyle={{ color: '#F8FAFC' }}
                  />
                  <Legend
                    formatter={(v) => {
                      const item = pieData.find((d) => d.name === v);
                      return (
                        <span className="text-text-muted text-xs">
                          {item?.displayName || v.replace(/_/g, ' ')}
                        </span>
                      );
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-64 text-text-muted text-xs text-center border border-dashed border-dark-border rounded-lg p-4">
              <FileSearch className="h-8 w-8 mb-2 text-text-muted/50" />
              <span>No verification data recorded yet.</span>
              <span className="text-[11px] text-text-muted/70 mt-1">
                Upload media in Verify Media to generate telemetry.
              </span>
            </div>
          )}
        </div>

        {/* Recent Forensics Activity */}
        <div className="bg-dark-card border border-dark-border rounded-lg p-6 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Clock className="h-4 w-4 text-brand-purple-light" />
              <h3 className="text-text-main font-semibold text-sm">Recent Activity</h3>
            </div>
            <Link
              to="/history"
              className="text-xs text-brand-purple-light hover:underline inline-flex items-center gap-1"
            >
              <span>View all</span>
              <ArrowRight className="h-3 w-3" />
            </Link>
          </div>

          {summary?.recent_activity?.length > 0 ? (
            <div className="divide-y divide-dark-border overflow-y-auto max-h-64 pr-1">
              {summary.recent_activity.map((v) => (
                <div
                  key={v.id}
                  className="py-3 flex items-center justify-between gap-3 hover:bg-dark-elevated/40 px-2 rounded transition-colors"
                >
                  <div className="min-w-0 flex-1">
                    <p className="text-text-main text-xs font-medium truncate font-mono">
                      {v.filename}
                    </p>
                    <p className="text-text-muted text-[11px] mt-0.5">
                      {v.created_at ? new Date(v.created_at).toLocaleString() : 'Recent'}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <VerdictBadge verdict={v.overall_status} />
                    <Link
                      to={`/results/${v.id}`}
                      className="p-1 rounded text-text-muted hover:text-text-main hover:bg-dark-elevated transition-colors"
                      title="Examine Report"
                    >
                      <ExternalLink className="h-3.5 w-3.5" />
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-64 text-text-muted text-xs text-center border border-dashed border-dark-border rounded-lg p-4">
              <Clock className="h-8 w-8 mb-2 text-text-muted/50" />
              <span>No recent inspection history available.</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
