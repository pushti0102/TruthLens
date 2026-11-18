import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import {
  Upload, Shield, CheckCircle2, AlertTriangle, XCircle,
  Cpu, Lock, FileImage, Loader2, Info, ArrowRight, Sparkles
} from 'lucide-react';

function Section({ title, icon: Icon, children, iconColor = 'text-cyan-400' }) {
  return (
    <div className="bg-slate-800/80 border border-slate-700 rounded-xl p-5 shadow-lg">
      <h4 className="flex items-center gap-2 text-white font-semibold mb-4 text-sm sm:text-base">
        <Icon className={`h-5 w-5 ${iconColor}`} />
        {title}
      </h4>
      {children}
    </div>
  );
}

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

export default function Verify() {
  const navigate = useNavigate();
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  const handleFile = (f) => {
    if (!f) return;
    setFile(f);
    setResult(null);
    setError('');
    const reader = new FileReader();
    reader.onload = (e) => setPreview(e.target.result);
    reader.readAsDataURL(f);
  };

  const onDrop = useCallback((e) => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  }, []);

  const handleVerify = async () => {
    if (!file) return;
    setLoading(true);
    setError('');
    setResult(null);
    const formData = new FormData();
    formData.append('file', file);
    try {
      const res = await api.post('/api/media/verify', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setResult(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Verification failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const vcfg = result ? (VERDICT_CONFIG[result.trust_assessment?.status] || VERDICT_CONFIG.INCONCLUSIVE) : null;

  // Format file size nicely
  const formatSize = (bytes) => {
    if (!bytes && bytes !== 0) return '—';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  // Extract raw AI scores safely
  const realScore = result?.ai?.raw_scores?.find((s) => s.label === 'REAL')?.score;
  const aiScore = result?.ai?.raw_scores?.find((s) => s.label === 'AI_GENERATED')?.score;

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <Shield className="h-7 w-7 text-cyan-400" /> Verify Media Authenticity
        </h1>
        <p className="text-slate-400 text-sm mt-1">
          Dual-engine analysis: Hugging Face Vision Transformer (AI Detection) + ECDSA & SHA-256 (Cryptographic Provenance)
        </p>
      </div>

      {/* Upload zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => document.getElementById('file-input').click()}
        className={`relative border-2 border-dashed rounded-2xl p-8 sm:p-10 text-center cursor-pointer transition-all ${
          dragging
            ? 'border-cyan-400 bg-cyan-400/5'
            : 'border-slate-600 hover:border-cyan-500 hover:bg-slate-800/50'
        }`}
      >
        <input
          id="file-input"
          type="file"
          accept="image/*"
          className="hidden"
          onChange={(e) => handleFile(e.target.files[0])}
        />
        {preview ? (
          <div className="space-y-3">
            <img src={preview} alt="preview" className="max-h-56 mx-auto rounded-lg object-contain shadow-md" />
            <p className="text-white text-sm font-semibold">{file.name}</p>
            <p className="text-slate-400 text-xs">{formatSize(file.size)} — Click or drop to replace</p>
          </div>
        ) : (
          <div className="space-y-3">
            <div className="p-3 bg-slate-800 rounded-full w-14 h-14 mx-auto flex items-center justify-center">
              <Upload className="h-7 w-7 text-cyan-400" />
            </div>
            <p className="text-white font-medium">Drop an image here or click to browse</p>
            <p className="text-slate-400 text-xs">Supports PNG, JPG, JPEG, WEBP</p>
          </div>
        )}
      </div>

      {error && (
        <div className="flex items-center gap-2 bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3 text-red-400 text-sm">
          <XCircle className="h-5 w-5 flex-shrink-0" /> {error}
        </div>
      )}

      <button
        onClick={handleVerify}
        disabled={!file || loading}
        className="w-full bg-cyan-500 hover:bg-cyan-400 disabled:opacity-50 disabled:cursor-not-allowed text-slate-900 font-semibold rounded-xl px-6 py-3.5 flex items-center justify-center gap-2 transition-all shadow-lg shadow-cyan-500/10"
      >
        {loading ? (
          <>
            <Loader2 className="h-5 w-5 animate-spin" /> Running Dual Forensic Analysis…
          </>
        ) : (
          <>
            <Sparkles className="h-5 w-5" /> Run Authenticity Verification
          </>
        )}
      </button>

      {/* Results Report */}
      {result && vcfg && (
        <div className="space-y-6 pt-4">
          {/* Overall verdict Banner */}
          <div className={`border rounded-2xl p-6 ${vcfg.bg} shadow-xl`}>
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-3">
              <div className="flex items-center gap-3">
                <vcfg.icon className={`h-8 w-8 ${vcfg.text} flex-shrink-0`} />
                <div>
                  <p className="text-xs text-slate-400 uppercase tracking-wider font-semibold">Trust Verdict</p>
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
            <p className="text-slate-200 text-sm leading-relaxed mt-2">{result.trust_assessment?.explanation}</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {/* File info */}
            <Section title="File & Metadata" icon={FileImage}>
              <Row label="Filename" value={result.filename} />
              <Row label="File Size" value={formatSize(result.file_size_bytes)} />
              <Row label="Dimensions" value={result.dimensions ? `${result.dimensions.width} × ${result.dimensions.height} px` : '—'} />
              <Row label="Format" value={result.detected_format || 'Image'} />
              <Row label="Verification ID" value={result.verification_id ? `${result.verification_id.slice(0, 12)}…` : '—'} mono />
              <Row label="Timestamp" value={result.timestamp ? new Date(result.timestamp).toLocaleString() : '—'} />
            </Section>

            {/* Cryptographic Integrity (Member 2) */}
            <Section
              title="Cryptographic Integrity (SHA-256)"
              icon={Shield}
              iconColor={result.integrity?.status === 'MATCH' ? 'text-green-400' : 'text-red-400'}
            >
              <div className="flex items-center justify-between pb-3 mb-2 border-b border-slate-700/60">
                <span className="text-xs text-slate-400">Integrity Status</span>
                <span className={`text-xs px-2.5 py-0.5 rounded-full font-semibold border ${
                  result.integrity?.status === 'MATCH' ? 'bg-green-500/20 text-green-400 border-green-500/30' :
                  result.integrity?.status === 'MISMATCH' ? 'bg-red-500/20 text-red-400 border-red-500/30' :
                  'bg-slate-700 text-slate-300 border-slate-600'
                }`}>
                  {result.integrity?.status || 'NO_REFERENCE'}
                </span>
              </div>
              <Row label="Computed Hash" value={result.sha256 ? `${result.sha256.slice(0, 24)}…` : '—'} mono />
              <Row label="Baseline Hash" value={result.integrity?.reference_sha256 ? `${result.integrity.reference_sha256.slice(0, 24)}…` : 'No prior registry'} mono />
              <p className="text-slate-400 text-xs mt-3 leading-relaxed">{result.integrity?.message}</p>
            </Section>

            {/* AI Forensic Detection (Member 1) */}
            <Section title="AI Visual Forensics (ViT Detector)" icon={Cpu} iconColor="text-purple-400">
              <div className="flex items-center justify-between pb-3 mb-2 border-b border-slate-700/60">
                <span className="text-xs text-slate-400">AI Prediction</span>
                <span className={`text-xs px-3 py-1 rounded-full font-bold border ${
                  result.ai?.label === 'AI_GENERATED' ? 'bg-amber-500/20 text-amber-400 border-amber-500/30' :
                  result.ai?.label === 'REAL' ? 'bg-green-500/20 text-green-400 border-green-500/30' :
                  'bg-slate-700 text-slate-300 border-slate-600'
                }`}>
                  {result.ai?.label ? (result.ai.label === 'AI_GENERATED' ? 'AI GENERATED' : 'AUTHENTIC REAL') : 'UNAVAILABLE'}
                </span>
              </div>

              {result.ai?.status === 'SUCCESS' ? (
                <div className="space-y-3">
                  <Row label="Confidence" value={`${((result.ai?.confidence || 0) * 100).toFixed(1)}%`} />
                  <Row label="AI Likelihood" value={result.ai?.ai_likelihood?.toUpperCase()} />
                  <Row label="Model Architecture" value="Vision Transformer (ViT-Base)" />
                  <Row label="Inference Time" value={result.ai?.inference_ms ? `${result.ai.inference_ms.toFixed(0)} ms` : '—'} />

                  {/* Confidence bar */}
                  {aiScore !== undefined && (
                    <div className="pt-2">
                      <div className="flex justify-between text-xs text-slate-400 mb-1">
                        <span>Real ({((realScore || 0) * 100).toFixed(1)}%)</span>
                        <span>AI Synthetic ({((aiScore || 0) * 100).toFixed(1)}%)</span>
                      </div>
                      <div className="w-full bg-slate-700 rounded-full h-2.5 overflow-hidden flex">
                        <div style={{ width: `${(realScore || 0) * 100}%` }} className="bg-green-500 h-full" />
                        <div style={{ width: `${(aiScore || 0) * 100}%` }} className="bg-amber-500 h-full" />
                      </div>
                    </div>
                  )}

                  {result.ai?.document_domain_warning && (
                    <p className="text-amber-400/90 bg-amber-500/10 border border-amber-500/20 rounded-lg p-2.5 text-xs mt-2">
                      ⚠️ {result.ai.document_domain_warning}
                    </p>
                  )}
                </div>
              ) : (
                <p className="text-slate-400 text-xs py-2">
                  AI service status: <span className="font-mono text-cyan-300">{result.ai?.status || 'UNAVAILABLE'}</span>
                </p>
              )}
            </Section>

            {/* Cryptographic Signature (Member 2) */}
            <Section title="Digital Provenance (ECDSA P-256)" icon={Lock} iconColor="text-cyan-400">
              <div className="flex items-center justify-between pb-3 mb-2 border-b border-slate-700/60">
                <span className="text-xs text-slate-400">Signature Status</span>
                <span className={`text-xs px-2.5 py-0.5 rounded-full font-semibold border ${
                  result.signature?.status === 'VALID' ? 'bg-green-500/20 text-green-400 border-green-500/30' :
                  result.signature?.status === 'INVALID' ? 'bg-red-500/20 text-red-400 border-red-500/30' :
                  'bg-slate-700 text-slate-300 border-slate-600'
                }`}>
                  {result.signature?.status || 'MISSING'}
                </span>
              </div>
              <Row label="Signing Key ID" value={result.signature?.key_id || 'Not registered'} mono />
              <Row label="Key Trust Status" value={result.signature?.key_trust_status || 'Unregistered'} />
              <Row label="Algorithm" value={result.signature?.algorithm || 'ECDSA-P256-SHA256'} />
              <p className="text-slate-400 text-xs mt-3 leading-relaxed">{result.signature?.message}</p>
            </Section>
          </div>

          <div className="flex justify-end pt-2">
            <button
              onClick={() => navigate(`/results/${result.verification_id}`)}
              className="inline-flex items-center gap-1.5 text-sm text-cyan-400 hover:text-cyan-300 font-medium transition-colors"
            >
              View detailed audit report <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
