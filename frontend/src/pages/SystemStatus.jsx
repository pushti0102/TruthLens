import { useEffect, useState } from 'react';
import api from '../services/api';
import { Server, Cpu, Lock, CheckCircle, XCircle, Loader2, RefreshCw } from 'lucide-react';

function StatusCard({ title, icon: Icon, status, details }) {
  const ok = status === 'ONLINE' || status === 'AVAILABLE' || status === 'HEALTHY';
  return (
    <div className={`border rounded-xl p-5 ${ok ? 'border-green-500/30 bg-green-500/5' : 'border-red-500/30 bg-red-500/5'}`}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Icon className={`h-6 w-6 ${ok ? 'text-green-400' : 'text-red-400'}`} />
          <span className="text-white font-semibold">{title}</span>
        </div>
        <span className={`flex items-center gap-1 text-sm font-medium ${ok ? 'text-green-400' : 'text-red-400'}`}>
          {ok ? <CheckCircle className="h-4 w-4" /> : <XCircle className="h-4 w-4" />}
          {status}
        </span>
      </div>
      {details && (
        <div className="space-y-1">
          {Object.entries(details).map(([k, v]) => (
            <div key={k} className="flex justify-between text-xs">
              <span className="text-slate-400">{k}</span>
              <span className="text-slate-300 font-mono">{String(v)}</span>
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
      .finally(() => setLoading(false));
  };

  useEffect(refresh, []);

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">System Status</h1>
          <p className="text-slate-400 text-sm mt-1">Real-time health of all TruthLens services</p>
        </div>
        <button
          onClick={refresh}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 rounded-lg text-sm transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {loading ? (
        <div className="flex justify-center py-16"><Loader2 className="h-8 w-8 text-cyan-400 animate-spin" /></div>
      ) : (
        <div className="space-y-4">
          {data.main && (
            <StatusCard
              title="Core API"
              icon={Server}
              status={data.main.status}
              details={{
                Version: data.main.version || '1.0.0',
                Database: data.main.database,
                Uptime: data.main.uptime || 'running',
              }}
            />
          )}
          {data.ai && (
            <StatusCard
              title="AI Detection Service"
              icon={Cpu}
              status={data.ai.status}
              details={{
                Model: data.ai.model || 'dima806/ai_vs_real_image_detection',
                'Transformers Installed': data.ai.transformers_available ? 'Yes' : 'No',
                'GPU Available': data.ai.gpu_available ? 'Yes' : 'No',
              }}
            />
          )}
          {data.crypto && (
            <StatusCard
              title="Cryptography Service"
              icon={Lock}
              status={data.crypto.status}
              details={{
                Algorithm: data.crypto.algorithm || 'ECDSA P-256',
                'Key ID': data.crypto.key_id || '—',
                'Registered Keys': data.crypto.registered_keys ?? '—',
              }}
            />
          )}
        </div>
      )}

      <div className="bg-slate-800 border border-slate-700 rounded-xl p-5">
        <h3 className="text-white font-semibold mb-3">Architecture Notes</h3>
        <div className="space-y-2 text-sm text-slate-400">
          <p>• <span className="text-slate-300">AI Model:</span> ViT-based detector (<code className="text-cyan-300 bg-slate-700 px-1 rounded">dima806/ai_vs_real_image_detection</code>). Install <code className="text-cyan-300 bg-slate-700 px-1 rounded">transformers</code> + <code className="text-cyan-300 bg-slate-700 px-1 rounded">torch</code> to enable.</p>
          <p>• <span className="text-slate-300">Cryptography:</span> ECDSA P-256 signing with SHA-256 hashing. Keys auto-generated in <code className="text-cyan-300 bg-slate-700 px-1 rounded">secrets/</code>.</p>
          <p>• <span className="text-slate-300">Database:</span> SQLite with SQLAlchemy ORM. Auto-migrates on startup.</p>
          <p>• <span className="text-slate-300">Auth:</span> JWT Bearer tokens (1h expiry) + Argon2id password hashing.</p>
        </div>
      </div>
    </div>
  );
}
