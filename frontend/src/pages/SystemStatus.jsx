import { useEffect, useState } from 'react';
import api from '../services/api';
import {
  Server,
  Cpu,
  Lock,
  CheckCircle2,
  XCircle,
  Loader2,
  RefreshCw,
  ShieldCheck,
  Database,
  Key
} from 'lucide-react';

function StatusCard({ title, icon: Icon, status, details }) {
  const ok = status === 'ONLINE' || status === 'AVAILABLE' || status === 'HEALTHY' || status === 'READY';
  return (
    <div className={`border rounded-lg p-5 shadow-xs transition-all ${
      ok
        ? 'border-status-genuine/30 bg-dark-card'
        : 'border-status-invalid/30 bg-dark-card'
    }`}>
      <div className="flex items-center justify-between mb-4 pb-2 border-b border-dark-border">
        <div className="flex items-center gap-2.5">
          <div className={`p-1.5 rounded-lg border ${
            ok ? 'text-status-genuine bg-status-genuine/10 border-status-genuine/20' : 'text-status-invalid bg-status-invalid/10 border-status-invalid/20'
          }`}>
            <Icon className="h-4 w-4" />
          </div>
          <span className="text-text-main font-semibold text-sm">{title}</span>
        </div>
        <span className={`inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-0.5 rounded border ${
          ok
            ? 'text-status-genuine bg-status-genuine/10 border-status-genuine/20'
            : 'text-status-invalid bg-status-invalid/10 border-status-invalid/20'
        }`}>
          {ok ? <CheckCircle2 className="h-3 w-3" /> : <XCircle className="h-3 w-3" />}
          {status}
        </span>
      </div>

      {details && (
        <div className="space-y-2">
          {Object.entries(details).map(([k, v]) => (
            <div key={k} className="flex justify-between items-center text-xs py-1 border-b border-dark-border/40 last:border-0">
              <span className="text-text-muted">{k}</span>
              <span className="text-text-main font-mono text-[11px] truncate max-w-[240px]">{String(v)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function SystemStatus() {
  const [data, setData] = useState({ main: null, ai: null, crypto: null });
  const [loading, setLoading] = useState(true);

  const refresh = () => {
    setLoading(true);
    Promise.all([
      api.get('/api/health').then((r) => r.data),
      api.get('/api/health/ai').then((r) => r.data),
      api.get('/api/health/crypto').then((r) => r.data),
    ])
      .then(([main, ai, crypto]) => setData({ main, ai, crypto }))
      .catch((err) => console.error('Status check error:', err))
      .finally(() => setLoading(false));
  };

  useEffect(refresh, []);

  return (
    <div className="max-w-4xl mx-auto p-6 md:p-8 lg:p-10 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Cpu className="h-6 w-6 text-brand-purple-light" />
            <h1 className="text-xl md:text-2xl font-bold text-text-main tracking-tight">
              System Telemetry & Health
            </h1>
          </div>
          <p className="text-text-muted text-xs sm:text-sm mt-1">
            Real-time status of cryptographic accelerators, neural inference engines, and core services.
          </p>
        </div>
        <button
          onClick={refresh}
          disabled={loading}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-dark-card hover:bg-dark-elevated border border-dark-border text-text-muted hover:text-text-main rounded-lg text-xs font-medium transition-colors disabled:opacity-40"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {loading ? (
        <div className="flex flex-col items-center justify-center py-20 space-y-2">
          <Loader2 className="h-8 w-8 text-brand-purple animate-spin" />
          <span className="text-xs text-text-muted font-mono uppercase tracking-wider">
            Polling subsystem health checks...
          </span>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {data.main && (
            <StatusCard
              title="Core API Subsystem"
              icon={Server}
              status={data.main.status}
              details={{
                Version: data.main.version || '1.2.0',
                Database: data.main.database || 'Active (SQLite)',
                State: data.main.uptime || 'Operational',
              }}
            />
          )}
          {data.ai && (
            <StatusCard
              title="AI Forensic Pipeline"
              icon={Cpu}
              status={data.ai.status}
              details={{
                Model: data.ai.model || data.ai.model_id || 'Dynamic Model Registry',
                Framework: data.ai.transformers_available ? 'HuggingFace PyTorch' : 'Fallback Engine',
                Hardware: data.ai.gpu_available ? 'Hardware GPU Accel' : 'Optimized CPU Threads',
              }}
            />
          )}
          {data.crypto && (
            <StatusCard
              title="Cryptography Engine"
              icon={Lock}
              status={data.crypto.status}
              details={{
                Primitive: data.crypto.algorithm || 'ECDSA SECP256R1',
                Hashing: 'FIPS 180-4 SHA-256',
                'Key Status': data.crypto.key_id ? 'Loaded & Valid' : 'Ready',
              }}
            />
          )}
        </div>
      )}

      {/* Security Architecture Reference */}
      <div className="bg-dark-card border border-dark-border rounded-lg p-5 space-y-3 shadow-xs">
        <h3 className="text-text-main font-semibold text-sm flex items-center gap-2">
          <ShieldCheck className="h-4 w-4 text-brand-purple-light" />
          Forensic Architecture Specifications
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs text-text-muted">
          <div className="space-y-2">
            <p>
              <strong className="text-text-main">AI Visual Forensics:</strong> Multi-model inference architecture (Standard ViT &amp; Smaug) detecting latent synthesis artifacts, high-frequency boundary patterns, and generative inconsistencies.
            </p>
            <p>
              <strong className="text-text-main">Cryptographic Provenance:</strong> SECP256R1 ECDSA signatures paired with SHA-256 bitwise digests to mathematically verify authenticity and trace origin.
            </p>
          </div>
          <div className="space-y-2">
            <p>
              <strong className="text-text-main">Security Audit Trail:</strong> Immutable security event ledger logging actor IDs, timestamps, origin IPs, and role transitions for full compliance.
            </p>
            <p>
              <strong className="text-text-main">Cryptographic Isolation:</strong> AI heuristic predictions and cryptographic evidence are decoupled so probabilistic models cannot invalidate authentic digital signatures.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
