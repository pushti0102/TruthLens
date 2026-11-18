import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import api from '../services/api';
import {
  Shield, FileImage, Cpu, Lock, AlertTriangle, CheckCircle2,
  XCircle, Info, Loader2, ArrowLeft, Download
} from 'lucide-react';

const VERDICT_CONFIG = {
  VERIFIED_TRUSTED: {
    bg: 'bg-green-500/10 border-green-500/30',
    text: 'text-green-400',
    badgeBg: 'bg-green-500/20 text-green-300 border-green-500/40',
    icon: CheckCircle2,
    label: 'Verified Authentic & Trusted',
  },
  VERIFIED_TRUSTED_WITH_AI_CONFLICT: {
    bg: 'bg-purple-500/10 border-purple-500/30',
    text: 'text-purple-400',
    badgeBg: 'bg-purple-500/20 text-purple-300 border-purple-500/40',
    icon: AlertTriangle,
    label: 'Verified Publisher (AI Artifacts Flagged)',
  },
  SUSPICIOUS_AI: {
    bg: 'bg-amber-500/10 border-amber-500/30',
    text: 'text-amber-400',
    badgeBg: 'bg-amber-500/20 text-amber-300 border-amber-500/40',
    icon: AlertTriangle,
    label: 'AI-Generated Media Detected',
  },
  INTEGRITY_MISMATCH: {
    bg: 'bg-red-500/10 border-red-500/30',
    text: 'text-red-400',
    badgeBg: 'bg-red-500/20 text-red-300 border-red-500/40',
    icon: XCircle,
    label: 'Tampered Media (Integrity Mismatch)',
  },
  INVALID_SIGNATURE: {
    bg: 'bg-red-500/10 border-red-500/30',
    text: 'text-red-400',
    badgeBg: 'bg-red-500/20 text-red-300 border-red-500/40',
    icon: XCircle,
    label: 'Invalid Cryptographic Signature',
  },
  INCONCLUSIVE: {
    bg: 'bg-slate-500/10 border-slate-500/30',
    text: 'text-slate-300',
    badgeBg: 'bg-slate-500/20 text-slate-300 border-slate-500/40',
    icon: Info,
    label: 'Inconclusive (No Registered Provenance)',
  },
};

function Row({ label, value, mono = false }) {
  return (
    <div className="flex justify-between items-start py-2 border-b border-slate-700/60 last:border-0 gap-4 text-xs sm:text-sm">
      <span className="text-slate-400 flex-shrink-0">{label}</span>
      <span className={`text-right ${mono ? 'text-cyan-300 font-mono break-all text-xs' : 'text-slate-200'}`}>
        {value ?? '—'}
      </span>
    </div>
  );
}

export default function Results() {
  const { id } = useParams();
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    api.get(`/api/media/${id}`)
      .then((r) => setResult(r.data))
      .catch(() => setError('Could not load verification record.'))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-80">
        <Loader2 className="h-8 w-8 text-cyan-400 animate-spin" />
      </div>
    );
  }

  if (error) {
    return <div className="text-center text-red-400 py-20">{error}</div>;
  }

  if (!result) return null;

  const vcfg = VERDICT_CONFIG[result.trust_assessment?.status] || VERDICT_CONFIG.INCONCLUSIVE;

  const formatSize = (bytes) => {
    if (!bytes && bytes !== 0) return '—';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const realScore = result.ai?.raw_scores?.find((s) => s.label === 'REAL')?.score;
  const aiScore = result.ai?.raw_scores?.find((s) => s.label === 'AI_GENERATED')?.score;

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Forensic Verification Report</h1>
          <p className="text-slate-400 text-xs font-mono mt-1">ID: {result.verification_id}</p>
        </div>
        <Link to="/history" className="inline-flex items-center gap-1 text-sm text-cyan-400 hover:text-cyan-300">
          <ArrowLeft className="h-4 w-4" /> Back to History
        </Link>
      </div>

      {/* Verdict banner */}
      <div className={`border rounded-2xl p-6 ${vcfg.bg} shadow-xl`}>
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-2">
          <div className="flex items-center gap-3">
            <vcfg.icon className={`h-8 w-8 ${vcfg.text} flex-shrink-0`} />
            <div>
              <p className="text-xs text-slate-400 uppercase tracking-wider font-semibold">Trust Assessment</p>
              <p className={`text-xl sm:text-2xl font-bold ${vcfg.text}`}>{vcfg.label}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className={`px-3 py-1 rounded-full text-xs font-semibold border ${vcfg.badgeBg}`}>
              {result.trust_assessment?.badge || result.trust_assessment?.status}
            </span>
            <span className="bg-slate-800 text-cyan-300 border border-slate-700 px-3 py-1 rounded-full text-xs font-mono font-bold">
              Score: {result.trust_assessment?.score ?? 50}/100
            </span>
          </div>
        </div>
        <p className="text-slate-200 text-sm mt-3 leading-relaxed">{result.trust_assessment?.explanation}</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {/* File info */}
        <div className="bg-slate-800/90 border border-slate-700 rounded-xl p-5 shadow-lg space-y-1">
          <h4 className="text-white font-semibold flex items-center gap-2 mb-3">
            <FileImage className="h-5 w-5 text-cyan-400" /> File Info
          </h4>
          <Row label="Filename" value={result.filename} />
          <Row label="Size" value={formatSize(result.file_size_bytes)} />
          <Row label="Dimensions" value={result.dimensions ? `${result.dimensions.width} × ${result.dimensions.height} px` : '—'} />
          <Row label="Format" value={result.detected_format || 'Image'} />
          <Row label="Verified At" value={result.timestamp ? new Date(result.timestamp).toLocaleString() : '—'} />
        </div>

        {/* Cryptographic Integrity */}
        <div className="bg-slate-800/90 border border-slate-700 rounded-xl p-5 shadow-lg space-y-1">
          <h4 className="text-white font-semibold flex items-center gap-2 mb-3">
            <Shield className="h-5 w-5 text-green-400" /> Cryptographic Integrity (Member 2)
          </h4>
          <Row label="Integrity Status" value={result.integrity?.status} />
          <Row label="Computed SHA-256" value={result.sha256} mono />
          <Row label="Reference SHA-256" value={result.integrity?.reference_sha256 || 'None (Unregistered)'} mono />
        </div>

        {/* AI Detection */}
        <div className="bg-slate-800/90 border border-slate-700 rounded-xl p-5 shadow-lg space-y-2">
          <h4 className="text-white font-semibold flex items-center gap-2 mb-2">
            <Cpu className="h-5 w-5 text-purple-400" /> AI Detection (Member 1)
          </h4>
          <Row label="Service Status" value={result.ai?.status} />
          {result.ai?.status === 'SUCCESS' && (
            <>
              <Row label="Predicted Class" value={result.ai?.label === 'AI_GENERATED' ? 'AI GENERATED ⚠️' : 'AUTHENTIC REAL ✓'} />
              <Row label="Confidence" value={`${((result.ai?.confidence || 0) * 100).toFixed(1)}%`} />
              <Row label="AI Likelihood" value={result.ai?.ai_likelihood?.toUpperCase()} />
              <Row label="Model Architecture" value="Vision Transformer (ViT-Base)" />
              <Row label="Inference Time" value={result.ai?.inference_ms ? `${result.ai.inference_ms.toFixed(0)} ms` : '—'} />

              {aiScore !== undefined && (
                <div className="pt-2">
                  <div className="flex justify-between text-xs text-slate-400 mb-1">
                    <span>Real ({((realScore || 0) * 100).toFixed(1)}%)</span>
                    <span>AI Synthetic ({((aiScore || 0) * 100).toFixed(1)}%)</span>
                  </div>
                  <div className="w-full bg-slate-700 rounded-full h-2 overflow-hidden flex">
                    <div style={{ width: `${(realScore || 0) * 100}%` }} className="bg-green-500 h-full" />
                    <div style={{ width: `${(aiScore || 0) * 100}%` }} className="bg-amber-500 h-full" />
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Cryptographic Signature */}
        <div className="bg-slate-800/90 border border-slate-700 rounded-xl p-5 shadow-lg space-y-1">
          <h4 className="text-white font-semibold flex items-center gap-2 mb-3">
            <Lock className="h-5 w-5 text-cyan-400" /> Digital Provenance (Member 2)
          </h4>
          <Row label="Signature Status" value={result.signature?.status} />
          <Row label="Signing Key ID" value={result.signature?.key_id || 'Not registered'} mono />
          <Row label="Key Trust Status" value={result.signature?.key_trust_status || 'Unregistered'} />
          <Row label="Algorithm" value={result.signature?.algorithm || 'ECDSA-P256-SHA256'} />
        </div>
      </div>
    </div>
  );
}
