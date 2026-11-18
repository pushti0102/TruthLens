import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import api from '../services/api';
import {
  ShieldCheck,
  FileImage,
  Cpu,
  Lock,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Info,
  Loader2,
  ArrowLeft,
  ChevronDown,
  ChevronUp,
  Copy,
  Check,
  FileText,
  Printer
} from 'lucide-react';

const VERDICT_CONFIG = {
  VERIFIED_TRUSTED: {
    bg: 'bg-status-genuine/10 border-status-genuine/30',
    text: 'text-status-genuine',
    badgeBg: 'bg-status-genuine/20 text-status-genuine border-status-genuine/30',
    icon: CheckCircle2,
    label: 'Verified Authentic & Trusted',
  },
  VERIFIED_TRUSTED_WITH_AI_CONFLICT: {
    bg: 'bg-brand-purple/10 border-brand-purple/30',
    text: 'text-brand-purple-light',
    badgeBg: 'bg-brand-purple/20 text-brand-purple-light border-brand-purple/30',
    icon: CheckCircle2,
    label: 'Verified Publisher (AI Artifacts Flagged)',
  },
  SUSPICIOUS_AI: {
    bg: 'bg-status-warning/10 border-status-warning/30',
    text: 'text-status-warning',
    badgeBg: 'bg-status-warning/20 text-status-warning border-status-warning/30',
    icon: AlertTriangle,
    label: 'AI-Generated Media Detected',
  },
  INTEGRITY_MISMATCH: {
    bg: 'bg-status-invalid/10 border-status-invalid/30',
    text: 'text-status-invalid',
    badgeBg: 'bg-status-invalid/20 text-status-invalid border-status-invalid/30',
    icon: XCircle,
    label: 'Tampered Media (Integrity Mismatch)',
  },
  INVALID_SIGNATURE: {
    bg: 'bg-status-invalid/10 border-status-invalid/30',
    text: 'text-status-invalid',
    badgeBg: 'bg-status-invalid/20 text-status-invalid border-status-invalid/30',
    icon: XCircle,
    label: 'Invalid Cryptographic Signature',
  },
  INCONCLUSIVE: {
    bg: 'bg-dark-elevated border-dark-border',
    text: 'text-text-main',
    badgeBg: 'bg-dark-card text-text-muted border-dark-border',
    icon: Info,
    label: 'Inconclusive (No Registered Provenance)',
  },
};

function Row({ label, value, mono = false, copyable = false }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    if (!value || value === '—') return;
    navigator.clipboard.writeText(value);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="flex justify-between items-start py-2 border-b border-dark-border/60 last:border-0 gap-4 text-xs">
      <span className="text-text-muted shrink-0">{label}</span>
      <div className="flex items-center gap-1.5 text-right min-w-0">
        <span className={`truncate ${mono ? 'text-brand-purple-light font-mono text-[11px]' : 'text-text-main'}`}>
          {value ?? '—'}
        </span>
        {copyable && value && value !== '—' && (
          <button
            onClick={handleCopy}
            className="p-1 rounded text-text-muted hover:text-text-main hover:bg-dark-elevated transition-colors"
            title="Copy value"
          >
            {copied ? <Check className="h-3 w-3 text-status-genuine" /> : <Copy className="h-3 w-3" />}
          </button>
        )}
      </div>
    </div>
  );
}

export default function Results() {
  const { id } = useParams();
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showTechnicalDetails, setShowTechnicalDetails] = useState(false);

  useEffect(() => {
    api.get(`/api/media/${id}`)
      .then((r) => setResult(r.data))
      .catch(() => setError('Could not load forensic inspection record.'))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-3">
        <Loader2 className="h-8 w-8 text-brand-purple animate-spin" />
        <span className="text-xs text-text-muted font-mono uppercase tracking-wider">
          Retrieving verification record...
        </span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto p-6 md:p-8">
        <div className="p-4 rounded-lg bg-status-invalid/10 border border-status-invalid/20 text-status-invalid flex items-center gap-3 text-xs">
          <AlertTriangle className="h-5 w-5 shrink-0" />
          <span>{error}</span>
        </div>
        <div className="mt-4">
          <Link
            to="/history"
            className="inline-flex items-center gap-1.5 text-xs text-brand-purple-light hover:underline"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            <span>Return to history</span>
          </Link>
        </div>
      </div>
    );
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
    <div className="max-w-4xl mx-auto p-6 md:p-8 lg:p-10 space-y-6">
      {/* Top action bar */}
      <div className="flex items-center justify-between">
        <Link
          to="/history"
          className="inline-flex items-center gap-1.5 text-xs font-medium text-text-muted hover:text-text-main transition-colors"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          <span>Verification History</span>
        </Link>
        <button
          onClick={() => window.print()}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-dark-card hover:bg-dark-elevated text-text-muted hover:text-text-main text-xs border border-dark-border transition-colors"
        >
          <Printer className="h-3.5 w-3.5" />
          <span>Print Audit Report</span>
        </button>
      </div>

      {/* Header */}
      <div>
        <div className="flex items-center gap-2">
          <ShieldCheck className="h-6 w-6 text-brand-purple-light" />
          <h1 className="text-xl md:text-2xl font-bold text-text-main tracking-tight">
            Forensic Inspection Report
          </h1>
        </div>
        <p className="text-text-muted text-xs font-mono mt-1">
          Verification UUID: {result.verification_id}
        </p>
      </div>

      {/* Overall verdict banner */}
      <div className={`border rounded-lg p-5 lg:p-6 ${vcfg.bg}`}>
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-2">
          <div className="flex items-center gap-3">
            <vcfg.icon className={`h-7 w-7 ${vcfg.text} shrink-0`} />
            <div>
              <p className="text-[11px] text-text-muted uppercase tracking-wider font-semibold">
                Overall Trust Verdict
              </p>
              <h2 className={`text-xl font-bold ${vcfg.text}`}>{vcfg.label}</h2>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className={`px-2.5 py-1 rounded text-xs font-semibold border ${vcfg.badgeBg}`}>
              {result.trust_assessment?.badge || result.trust_assessment?.status}
            </span>
            <span className="bg-dark-card text-brand-purple-light border border-dark-border px-2.5 py-1 rounded text-xs font-mono font-bold">
              Score: {result.trust_assessment?.score ?? 50}/100
            </span>
          </div>
        </div>
        <p className="text-text-main text-xs sm:text-sm mt-3 leading-relaxed">
          {result.trust_assessment?.explanation}
        </p>
      </div>

      {/* 4 Core Evidence Sections */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {/* Media File Metadata */}
        <div className="bg-dark-card border border-dark-border rounded-lg p-5 shadow-xs">
          <div className="flex items-center gap-2 mb-3 pb-2 border-b border-dark-border">
            <FileImage className="h-4 w-4 text-brand-purple-light" />
            <h3 className="text-text-main font-semibold text-sm">Media File Specifications</h3>
          </div>
          <Row label="Filename" value={result.filename} />
          <Row label="File Size" value={formatSize(result.file_size_bytes)} />
          <Row
            label="Dimensions"
            value={result.dimensions ? `${result.dimensions.width} × ${result.dimensions.height} px` : '—'}
          />
          <Row label="Format" value={result.detected_format || 'Image'} />
          <Row
            label="Verified At"
            value={result.timestamp ? new Date(result.timestamp).toLocaleString() : '—'}
          />
        </div>

        {/* Cryptographic Integrity */}
        <div className="bg-dark-card border border-dark-border rounded-lg p-5 shadow-xs">
          <div className="flex items-center justify-between mb-3 pb-2 border-b border-dark-border">
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-status-genuine" />
              <h3 className="text-text-main font-semibold text-sm">Cryptographic Integrity</h3>
            </div>
            <span className={`text-[11px] px-2 py-0.5 rounded font-medium border ${
              result.integrity?.status === 'MATCH' ? 'bg-status-genuine/10 text-status-genuine border-status-genuine/20' :
              result.integrity?.status === 'MISMATCH' ? 'bg-status-invalid/10 text-status-invalid border-status-invalid/20' :
              'bg-dark-elevated text-text-muted border-dark-border'
            }`}>
              {result.integrity?.status === 'MATCH' ? 'Verified Match' :
               result.integrity?.status === 'MISMATCH' ? 'Tamper Detected' : 'No Reference'}
            </span>
          </div>
          <Row label="Status" value={result.integrity?.status} />
          <Row label="Computed Hash" value={result.sha256 ? `${result.sha256.slice(0, 18)}...` : '—'} mono copyable />
          <p className="text-text-muted text-xs mt-3 leading-relaxed">
            {result.integrity?.message || 'Cryptographic integrity evaluated by bitwise SHA-256 analysis.'}
          </p>
        </div>

        {/* AI Detection Visual Forensics */}
        <div className="bg-dark-card border border-dark-border rounded-lg p-5 shadow-xs">
          <div className="flex items-center justify-between mb-3 pb-2 border-b border-dark-border">
            <div className="flex items-center gap-2">
              <Cpu className="h-4 w-4 text-brand-purple-light" />
              <h3 className="text-text-main font-semibold text-sm">
                AI Forensics ({result.ai?.model_name || 'AI Engine'})
              </h3>
            </div>
            <span className={`text-[11px] px-2 py-0.5 rounded font-medium border ${
              result.ai?.outcome === 'INCONCLUSIVE' || result.ai?.model_disagreement ? 'bg-dark-elevated text-text-muted border-dark-border' :
              result.ai?.label === 'AI_GENERATED' ? 'bg-status-warning/10 text-status-warning border-status-warning/20' :
              result.ai?.label === 'REAL' ? 'bg-status-genuine/10 text-status-genuine border-status-genuine/20' :
              'bg-dark-elevated text-text-muted border-dark-border'
            }`}>
              {result.ai?.outcome === 'INCONCLUSIVE' ? 'Inconclusive' :
               result.ai?.label === 'AI_GENERATED' ? 'AI Synthetic' : 'Authentic Cues'}
            </span>
          </div>

          <div className="space-y-1">
            <Row
              label="Decision"
              value={
                result.ai?.outcome === 'INCONCLUSIVE'
                  ? 'INCONCLUSIVE (Ambiguous Boundary)'
                  : result.ai?.outcome || (result.ai?.label === 'AI_GENERATED' ? 'AI Generated' : 'Authentic Real')
              }
            />
            <Row label="Model Likelihood" value={result.ai?.ai_likelihood ? result.ai.ai_likelihood.toUpperCase() : '—'} />
            <Row
              label="Model Confidence"
              value={`${((result.ai?.confidence || 0) * 100).toFixed(1)}% (Softmax score)`}
            />
            <Row label="Architecture" value={result.ai?.architecture || '—'} />
            <Row label="Inference Time" value={result.ai?.inference_ms ? `${result.ai.inference_ms.toFixed(0)} ms` : '—'} />

            {aiScore !== undefined && (
              <div className="pt-2">
                <div className="flex justify-between text-[11px] text-text-muted mb-1 font-mono">
                  <span>Real: {((realScore || 0) * 100).toFixed(1)}%</span>
                  <span>Synthetic: {((aiScore || 0) * 100).toFixed(1)}%</span>
                </div>
                <div className="w-full bg-dark-sidebar rounded-full h-2 overflow-hidden flex border border-dark-border">
                  <div style={{ width: `${(realScore || 0) * 100}%` }} className="bg-status-genuine h-full" />
                  <div style={{ width: `${(aiScore || 0) * 100}%` }} className="bg-status-warning h-full" />
                </div>
              </div>
            )}

            {result.ai?.model_disagreement && (
              <div className="p-2.5 rounded bg-status-warning/10 border border-status-warning/20 text-status-warning text-xs mt-2">
                <span className="font-semibold">⚠️ Model Disagreement: </span>
                {result.ai.disagreement_details}
              </div>
            )}

            {result.ai?.calibration_note && (
              <div className="p-2.5 rounded bg-dark-elevated border border-dark-border text-xs text-text-muted mt-2">
                <span className="font-medium text-text-main">Calibration Notice: </span>
                {result.ai.calibration_note}
              </div>
            )}

            {result.ai?.document_domain_warning && (
              <p className="text-status-warning bg-status-warning/10 border border-status-warning/20 rounded p-2 text-xs mt-2">
                ⚠️ {result.ai.document_domain_warning}
              </p>
            )}
          </div>
        </div>

        {/* Cryptographic Provenance */}
        <div className="bg-dark-card border border-dark-border rounded-lg p-5 shadow-xs">
          <div className="flex items-center justify-between mb-3 pb-2 border-b border-dark-border">
            <div className="flex items-center gap-2">
              <Lock className="h-4 w-4 text-brand-purple-light" />
              <h3 className="text-text-main font-semibold text-sm">Digital Provenance</h3>
            </div>
            <span className={`text-[11px] px-2 py-0.5 rounded font-medium border ${
              result.signature?.status === 'VALID' ? 'bg-status-genuine/10 text-status-genuine border-status-genuine/20' :
              result.signature?.status === 'INVALID' ? 'bg-status-invalid/10 text-status-invalid border-status-invalid/20' :
              'bg-dark-elevated text-text-muted border-dark-border'
            }`}>
              {result.signature?.status === 'VALID' ? 'Valid ECDSA' :
               result.signature?.status === 'INVALID' ? 'Signature Invalid' : 'No Record'}
            </span>
          </div>
          <Row label="Signature Status" value={result.signature?.status} />
          <Row label="Signing Key" value={result.signature?.key_id ? `${result.signature.key_id.slice(0, 16)}...` : 'Unregistered'} mono />
          <Row label="Key Trust Level" value={result.signature?.key_trust_status || 'Unregistered'} />
          <Row label="Algorithm" value={result.signature?.algorithm || 'ECDSA-P256-SHA256'} />
          <div className="bg-dark-elevated/70 border border-dark-border rounded p-2.5 text-[11px] text-text-muted mt-3 leading-relaxed">
            <Info className="h-3 w-3 inline mr-1 text-text-muted" />
            Provenance verification queries authoritative publisher records. Missing registration is reported as unavailable, not fraud.
          </div>
        </div>
      </div>

      {/* Collapsible Forensic Details Accordion */}
      <div className="bg-dark-card border border-dark-border rounded-lg overflow-hidden">
        <button
          onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
          className="w-full px-5 py-3.5 flex items-center justify-between text-xs font-semibold text-text-main hover:bg-dark-elevated transition-colors"
        >
          <div className="flex items-center gap-2">
            <FileText className="h-4 w-4 text-brand-purple-light" />
            <span>Forensic Cryptographic Details & Raw Hashes</span>
          </div>
          {showTechnicalDetails ? (
            <ChevronUp className="h-4 w-4 text-text-muted" />
          ) : (
            <ChevronDown className="h-4 w-4 text-text-muted" />
          )}
        </button>

        {showTechnicalDetails && (
          <div className="px-5 pb-5 pt-2 border-t border-dark-border space-y-3 bg-dark-sidebar/40">
            <Row label="Full Computed SHA-256" value={result.sha256} mono copyable />
            <Row label="Reference SHA-256 Baseline" value={result.integrity?.reference_sha256 || 'None'} mono copyable />
            <Row label="Verification ID" value={result.verification_id} mono copyable />
            <Row label="Forensic Model Identifier" value={result.ai?.model_id} mono />
            <Row label="Inference Timestamp" value={result.timestamp ? new Date(result.timestamp).toISOString() : '—'} mono />
          </div>
        )}
      </div>
    </div>
  );
}
