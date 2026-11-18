import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import {
  UploadCloud,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Cpu,
  Lock,
  FileImage,
  Loader2,
  Info,
  ArrowRight,
  Sparkles,
  ChevronDown,
  ChevronUp,
  Copy,
  Check,
  RotateCcw,
  HelpCircle,
  FileText
} from 'lucide-react';

function Section({ title, icon: Icon, children, statusBadge, iconColor = 'text-brand-purple-light' }) {
  return (
    <div className="bg-dark-card border border-dark-border rounded-lg p-5 shadow-xs">
      <div className="flex items-center justify-between mb-4 pb-2 border-b border-dark-border">
        <h4 className="flex items-center gap-2 text-text-main font-semibold text-sm">
          <Icon className={`h-4 w-4 ${iconColor}`} />
          {title}
        </h4>
        {statusBadge}
      </div>
      {children}
    </div>
  );
}

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

export default function Verify() {
  const navigate = useNavigate();
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [selectedModel, setSelectedModel] = useState('current');
  const [availableModels, setAvailableModels] = useState([]);
  const [showTechnicalDetails, setShowTechnicalDetails] = useState(false);

  useEffect(() => {
    api.get('/api/media/models')
      .then((res) => {
        if (Array.isArray(res.data) && res.data.length > 0) {
          setAvailableModels(res.data);
        }
      })
      .catch(() => {});
  }, []);

  const handleModelChange = (model) => {
    setSelectedModel(model);
    setResult(null); // Clear previous result immediately to ensure old results are not reused
    setError('');
  };

  const handleFile = (f) => {
    if (!f) return;
    if (f.size > 25 * 1024 * 1024) {
      setError('File size exceeds the 25 MB platform limit.');
      return;
    }
    setFile(f);
    setResult(null);
    setError('');
    const reader = new FileReader();
    reader.onload = (e) => setPreview(e.target.result);
    reader.readAsDataURL(f);
  };

  const clearFile = (e) => {
    e.stopPropagation();
    setFile(null);
    setPreview(null);
    setResult(null);
    setError('');
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
    formData.append('model', selectedModel);
    try {
      const res = await api.post('/api/media/verify', formData);
      setResult(res.data);
    } catch (err) {
      console.error('Verification request error:', err);
      let errMsg = 'Verification failed. Please try again.';
      if (err.response?.data?.detail) {
        const detail = err.response.data.detail;
        if (typeof detail === 'string') {
          errMsg = detail;
        } else if (typeof detail === 'object') {
          errMsg = detail.message || detail.error_code || JSON.stringify(detail);
        }
      } else if (err.code === 'ECONNABORTED' || err.message?.includes('timeout')) {
        errMsg = 'Analysis timed out on CPU. High-resolution photos evaluated with deep forensic models may take longer; please retry.';
      } else if (err.message) {
        errMsg = `${err.message}. Ensure backend is running at http://127.0.0.1:8000.`;
      }
      setError(errMsg);
    } finally {
      setLoading(false);
    }
  };

  const vcfg = result ? (VERDICT_CONFIG[result.trust_assessment?.status] || VERDICT_CONFIG.INCONCLUSIVE) : null;

  const formatSize = (bytes) => {
    if (!bytes && bytes !== 0) return '—';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const realScore = result?.ai?.raw_scores?.find((s) => s.label === 'REAL')?.score;
  const aiScore = result?.ai?.raw_scores?.find((s) => s.label === 'AI_GENERATED')?.score;

  return (
    <div className="max-w-4xl mx-auto p-6 md:p-8 lg:p-10 space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2">
          <ShieldCheck className="h-6 w-6 text-brand-purple-light" />
          <h1 className="text-xl md:text-2xl font-bold text-text-main tracking-tight">
            Verify Media Authenticity
          </h1>
        </div>
        <p className="text-text-muted text-sm mt-1">
          Perform dual-layer forensic analysis: deep learning visual cues + cryptographic integrity and provenance verification.
        </p>
      </div>

      {/* Drag & Drop Upload Zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => document.getElementById('file-input').click()}
        className={`relative border border-dashed rounded-lg p-6 sm:p-8 text-center cursor-pointer transition-all ${
          dragging
            ? 'border-brand-purple bg-brand-purple/5'
            : 'border-dark-border bg-dark-card hover:border-brand-purple/60 hover:bg-dark-elevated/40'
        }`}
      >
        <input
          id="file-input"
          type="file"
          accept="image/png, image/jpeg, image/jpg, image/webp"
          className="hidden"
          onChange={(e) => handleFile(e.target.files[0])}
        />

        {preview ? (
          <div className="space-y-4">
            <div className="relative inline-block max-w-full">
              <img
                src={preview}
                alt="Upload preview"
                className="max-h-60 mx-auto rounded-md object-contain border border-dark-border bg-dark-sidebar shadow-xs"
              />
              <button
                onClick={clearFile}
                className="absolute top-2 right-2 p-1.5 rounded-full bg-dark-sidebar/90 text-text-muted hover:text-status-invalid hover:bg-dark-card border border-dark-border transition-colors"
                title="Remove image"
              >
                <XCircle className="h-4 w-4" />
              </button>
            </div>
            <div>
              <p className="text-text-main text-sm font-medium font-mono truncate">{file.name}</p>
              <p className="text-text-muted text-xs mt-0.5">
                {formatSize(file.size)} • Click or drop new file to replace
              </p>
            </div>
          </div>
        ) : (
          <div className="space-y-3 py-4">
            <div className="p-3 bg-dark-elevated rounded-lg w-12 h-12 mx-auto flex items-center justify-center border border-dark-border">
              <UploadCloud className="h-6 w-6 text-brand-purple-light" />
            </div>
            <div>
              <p className="text-text-main text-sm font-medium">
                Drag and drop image here, or <span className="text-brand-purple-light underline">browse files</span>
              </p>
              <p className="text-text-muted text-xs mt-1">
                Supported formats: PNG, JPG, JPEG, WEBP (Maximum size: 25 MB)
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Model Selection (Experimental testing option) */}
      <div className="bg-dark-card border border-dark-border rounded-lg p-4 space-y-2.5">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1">
          <label className="text-xs font-semibold text-text-main uppercase tracking-wider flex items-center gap-1.5">
            <Cpu className="h-3.5 w-3.5 text-brand-purple-light" />
            Forensic AI Model Engine
          </label>
          <span className="text-[11px] text-text-muted font-mono">
            Active: {availableModels.find((m) => m.key === selectedModel)?.name || (selectedModel === 'smaug' ? 'Smaug Detector' : 'Standard ViT Detector')}
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
          {(availableModels.length > 0 ? availableModels : [
            { key: 'current', name: 'Standard Detector (ViT-Base)', description: 'Vision Transformer trained on synthetic & real artifacts', badge: 'Standard' },
            { key: 'smaug', name: 'Advanced Detector (Smaug)', description: 'Multi-crop forensic embedding architecture', badge: 'Experimental' },
          ]).map((m) => {
            const isSelected = selectedModel === m.key;
            return (
              <button
                key={m.key}
                type="button"
                onClick={() => handleModelChange(m.key)}
                className={`p-3 rounded-lg border text-left transition-all ${
                  isSelected
                    ? 'bg-dark-elevated border-brand-purple text-text-main shadow-xs'
                    : 'bg-dark-sidebar/60 border-dark-border text-text-muted hover:border-dark-border/90'
                }`}
              >
                <div className="font-medium text-xs text-text-main flex items-center justify-between gap-2">
                  <span>{m.name}</span>
                  {m.badge && (
                    <span className="bg-dark-card border border-dark-border text-brand-purple-light text-[10px] px-1.5 py-0.5 rounded font-mono">
                      {m.badge}
                    </span>
                  )}
                </div>
                <div className="text-[11px] text-text-muted mt-1 leading-snug">{m.description}</div>
              </button>
            );
          })}
        </div>

        <p className="text-[11px] text-text-muted/80 pt-1 leading-relaxed">
          <Info className="h-3 w-3 inline mr-1 text-text-muted" />
          Note: AI visual detection is probabilistic and experimental. It evaluates statistical artifact patterns and does not constitute absolute proof of digital authenticity or manipulation.
        </p>
      </div>

      {error && (
        <div className="flex items-center gap-2.5 bg-status-invalid/10 border border-status-invalid/20 rounded-lg p-3.5 text-status-invalid text-xs">
          <XCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Verify CTA */}
      <button
        onClick={handleVerify}
        disabled={!file || loading}
        className="w-full bg-brand-purple hover:bg-brand-purple-light disabled:opacity-40 disabled:cursor-not-allowed text-white font-medium rounded-lg px-6 py-3 flex items-center justify-center gap-2 transition-all shadow-xs"
      >
        {loading ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            <span>Executing Forensics & Cryptographic Verification...</span>
          </>
        ) : (
          <>
            <ShieldCheck className="h-4 w-4" />
            <span>Verify Media</span>
          </>
        )}
      </button>

      {/* Four-Section Result Report */}
      {result && vcfg && (
        <div className="space-y-6 pt-2">
          {/* Section A: Overall Assessment */}
          <div className={`border rounded-lg p-5 lg:p-6 ${vcfg.bg}`}>
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-3">
              <div className="flex items-center gap-3">
                <vcfg.icon className={`h-7 w-7 ${vcfg.text} shrink-0`} />
                <div>
                  <span className="text-[11px] text-text-muted uppercase tracking-wider font-semibold">
                    Trust Verdict
                  </span>
                  <h3 className={`text-xl font-bold ${vcfg.text}`}>{vcfg.label}</h3>
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
            <p className="text-text-main text-xs sm:text-sm leading-relaxed mt-2">
              {result.trust_assessment?.explanation}
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {/* Section B: AI Visual Forensics */}
            <Section
              title={`AI Visual Forensics (${result.ai?.model_name || 'Standard Model'})`}
              icon={Cpu}
              iconColor="text-brand-purple-light"
              statusBadge={
                <span className={`text-[11px] px-2 py-0.5 rounded font-medium border ${
                  result.ai?.outcome === 'INCONCLUSIVE' || result.ai?.model_disagreement ? 'bg-dark-elevated text-text-muted border-dark-border' :
                  result.ai?.label === 'AI_GENERATED' ? 'bg-status-warning/10 text-status-warning border-status-warning/20' :
                  result.ai?.label === 'REAL' ? 'bg-status-genuine/10 text-status-genuine border-status-genuine/20' :
                  'bg-dark-elevated text-text-muted border-dark-border'
                }`}>
                  {result.ai?.outcome === 'INCONCLUSIVE'
                    ? 'Inconclusive'
                    : result.ai?.label === 'AI_GENERATED'
                    ? 'AI Synthetic'
                    : result.ai?.label === 'REAL'
                    ? 'Authentic Visual Cues'
                    : 'Unavailable'}
                </span>
              }
            >
              {result.ai?.status === 'SUCCESS' ? (
                <div className="space-y-2">
                  <Row
                    label="Prediction Outcome"
                    value={
                      result.ai?.outcome === 'INCONCLUSIVE'
                        ? 'INCONCLUSIVE (Ambiguous Cues)'
                        : result.ai?.outcome || (result.ai?.label === 'AI_GENERATED' ? 'AI Generated' : 'Authentic Real')
                    }
                  />
                  <Row label="Model Likelihood" value={result.ai?.ai_likelihood ? result.ai.ai_likelihood.toUpperCase() : '—'} />
                  <Row
                    label="Confidence Heuristic"
                    value={`${((result.ai?.confidence || 0) * 100).toFixed(1)}% (Softmax score)`}
                  />
                  <Row label="Architecture" value={result.ai?.architecture || '—'} />
                  <Row label="Inference Duration" value={result.ai?.inference_ms ? `${result.ai.inference_ms.toFixed(0)} ms` : '—'} />

                  {/* Horizontal Bar Visualization */}
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

                  {/* Model Disagreement Alert */}
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
              ) : (
                <p className="text-text-muted text-xs py-2">
                  AI inference service status: <span className="font-mono text-brand-purple-light">{result.ai?.status || 'UNAVAILABLE'}</span>
                </p>
              )}
            </Section>

            {/* Section C: Cryptographic Integrity */}
            <Section
              title="Cryptographic Integrity"
              icon={ShieldCheck}
              iconColor={result.integrity?.status === 'MATCH' ? 'text-status-genuine' : 'text-status-invalid'}
              statusBadge={
                <span className={`text-[11px] px-2 py-0.5 rounded font-medium border ${
                  result.integrity?.status === 'MATCH' ? 'bg-status-genuine/10 text-status-genuine border-status-genuine/20' :
                  result.integrity?.status === 'MISMATCH' ? 'bg-status-invalid/10 text-status-invalid border-status-invalid/20' :
                  'bg-dark-elevated text-text-muted border-dark-border'
                }`}>
                  {result.integrity?.status === 'MATCH' ? 'Verified Match' :
                   result.integrity?.status === 'MISMATCH' ? 'Tamper Detected' : 'Unregistered'}
                </span>
              }
            >
              <div className="space-y-2">
                <Row label="Integrity Check" value={result.integrity?.status === 'MATCH' ? 'Exact bitstream match confirmed' : result.integrity?.status === 'MISMATCH' ? 'Byte sequence modified from baseline' : 'No prior baseline hash'} />
                <Row label="SHA-256 Digest" value={result.sha256 ? `${result.sha256.slice(0, 16)}...` : '—'} mono copyable />
                <p className="text-text-muted text-xs mt-2 leading-relaxed">
                  {result.integrity?.message || 'Cryptographic verification independent of AI predictions.'}
                </p>
              </div>
            </Section>

            {/* Section D: Digital Provenance */}
            <Section
              title="Digital Provenance & Signature"
              icon={Lock}
              iconColor="text-brand-purple-light"
              statusBadge={
                <span className={`text-[11px] px-2 py-0.5 rounded font-medium border ${
                  result.signature?.status === 'VALID' ? 'bg-status-genuine/10 text-status-genuine border-status-genuine/20' :
                  result.signature?.status === 'INVALID' ? 'bg-status-invalid/10 text-status-invalid border-status-invalid/20' :
                  'bg-dark-elevated text-text-muted border-dark-border'
                }`}>
                  {result.signature?.status === 'VALID' ? 'ECDSA Valid' :
                   result.signature?.status === 'INVALID' ? 'Signature Invalid' : 'No Provenance'}
                </span>
              }
            >
              <div className="space-y-2">
                <Row label="Publisher Status" value={result.signature?.status === 'VALID' ? 'Registered Authorized Publisher' : 'Unregistered Source'} />
                <Row label="Signing Key" value={result.signature?.key_id ? `${result.signature.key_id.slice(0, 16)}...` : 'None'} mono />
                <Row label="Algorithm" value={result.signature?.algorithm || 'ECDSA-P256-SHA256'} />
                <div className="bg-dark-elevated/70 border border-dark-border rounded p-2.5 text-[11px] text-text-muted mt-2 leading-relaxed">
                  <Info className="h-3 w-3 inline mr-1 text-text-muted" />
                  Missing provenance indicates this file was not pre-registered in the publisher registry; it does not indicate fraud.
                </div>
              </div>
            </Section>

            {/* File & Metadata */}
            <Section title="Media File Specs" icon={FileImage}>
              <div className="space-y-2">
                <Row label="File Name" value={result.filename} />
                <Row label="File Size" value={formatSize(result.file_size_bytes)} />
                <Row label="Dimensions" value={result.dimensions ? `${result.dimensions.width} × ${result.dimensions.height} px` : '—'} />
                <Row label="Format" value={result.detected_format || 'Image'} />
              </div>
            </Section>
          </div>

          {/* Collapsible Technical Details Accordion */}
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
                <Row label="Full SHA-256 Digest" value={result.sha256} mono copyable />
                <Row label="Reference SHA-256" value={result.integrity?.reference_sha256 || 'None'} mono copyable />
                <Row label="Verification UUID" value={result.verification_id} mono copyable />
                <Row label="Selected Model ID" value={result.ai?.model_id} mono />
                <Row label="Key Trust Level" value={result.signature?.key_trust_status || 'Unverified'} />
                <Row label="Analysis Timestamp" value={result.timestamp ? new Date(result.timestamp).toISOString() : '—'} mono />
              </div>
            )}
          </div>

          {/* Action buttons */}
          <div className="flex justify-end gap-3 pt-2">
            <button
              onClick={() => navigate(`/results/${result.verification_id}`)}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-dark-elevated hover:bg-dark-border text-xs font-medium text-text-main border border-dark-border transition-colors"
            >
              <span>Detailed Inspection Audit Page</span>
              <ArrowRight className="h-3.5 w-3.5 text-brand-purple-light" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
