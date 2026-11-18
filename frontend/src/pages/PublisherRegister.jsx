import { useState, useCallback } from 'react';
import api from '../services/api';
import {
  UploadCloud,
  Lock,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Copy,
  Check,
  FileKey,
  ShieldCheck,
  XCircle
} from 'lucide-react';

export default function PublisherRegister() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [title, setTitle] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [copiedKey, setCopiedKey] = useState('');
  const [dragging, setDragging] = useState(false);

  const handleFile = (f) => {
    if (!f) return;
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
  };

  const onDrop = useCallback((e) => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  }, []);

  const handleRegister = async () => {
    if (!file) return;
    setLoading(true);
    setError('');
    setResult(null);
    const formData = new FormData();
    formData.append('file', file);
    if (title) formData.append('title', title);
    try {
      const res = await api.post('/api/publishers/register-media', formData);
      setResult(res.data);
    } catch (err) {
      console.error('Registration error:', err);
      let errMsg = 'Registration failed.';
      if (err.response?.data?.detail) {
        const detail = err.response.data.detail;
        errMsg = typeof detail === 'string' ? detail : (detail.message || JSON.stringify(detail));
      } else if (err.message) {
        errMsg = err.message;
      }
      setError(errMsg);
    } finally {
      setLoading(false);
    }
  };

  const copy = (text, key) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(''), 2000);
  };

  return (
    <div className="max-w-3xl mx-auto p-6 md:p-8 lg:p-10 space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2">
          <FileKey className="h-6 w-6 text-brand-purple-light" />
          <h1 className="text-xl md:text-2xl font-bold text-text-main tracking-tight">
            Publisher Registry & Signing
          </h1>
        </div>
        <p className="text-text-muted text-xs sm:text-sm mt-1">
          Cryptographically sign digital media assets with your organization's ECDSA private key and record provenance on TruthLens.
        </p>
      </div>

      <div className="bg-dark-card border border-dark-border rounded-lg p-6 space-y-5 shadow-xs">
        {/* Drag & Drop Upload */}
        <div
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          onClick={() => document.getElementById('pub-file').click()}
          className={`border border-dashed rounded-lg p-6 sm:p-8 text-center cursor-pointer transition-all ${
            dragging
              ? 'border-brand-purple bg-brand-purple/5'
              : 'border-dark-border bg-dark-sidebar/40 hover:border-brand-purple/60 hover:bg-dark-elevated/40'
          }`}
        >
          <input
            id="pub-file"
            type="file"
            accept="image/png, image/jpeg, image/jpg, image/webp"
            className="hidden"
            onChange={(e) => handleFile(e.target.files[0])}
          />
          {preview ? (
            <div className="space-y-3">
              <div className="relative inline-block">
                <img src={preview} alt="preview" className="max-h-48 mx-auto rounded border border-dark-border" />
                <button
                  onClick={clearFile}
                  className="absolute top-1 right-1 p-1 rounded-full bg-dark-sidebar text-text-muted hover:text-status-invalid border border-dark-border"
                >
                  <XCircle className="h-4 w-4" />
                </button>
              </div>
              <p className="text-text-main text-xs font-mono font-medium">{file.name}</p>
            </div>
          ) : (
            <div className="space-y-2 py-4">
              <UploadCloud className="h-8 w-8 text-brand-purple-light mx-auto" />
              <p className="text-text-main text-sm font-medium">Click to select or drop authoritative media</p>
              <p className="text-text-muted text-xs">Supports PNG, JPG, JPEG, WEBP</p>
            </div>
          )}
        </div>

        {/* Title / Reference Label */}
        <div>
          <label className="block text-xs font-semibold text-text-main uppercase tracking-wider mb-1.5">
            Asset Title or Reference Label
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Official Executive Portrait — Nov 2026"
            className="w-full bg-dark-sidebar border border-dark-border rounded-lg px-3.5 py-2.5 text-text-main placeholder-text-muted focus:outline-none focus:border-brand-purple text-xs sm:text-sm"
          />
        </div>

        {error && (
          <div className="flex items-center gap-2 bg-status-invalid/10 border border-status-invalid/20 rounded-lg p-3 text-status-invalid text-xs">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <button
          onClick={handleRegister}
          disabled={!file || loading}
          className="w-full bg-brand-purple hover:bg-brand-purple-light disabled:opacity-40 disabled:cursor-not-allowed text-white font-medium rounded-lg py-2.5 flex items-center justify-center gap-2 transition-all shadow-xs text-xs sm:text-sm"
        >
          {loading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>Generating ECDSA Digital Signature & Registering...</span>
            </>
          ) : (
            <>
              <Lock className="h-4 w-4" />
              <span>Register &amp; Cryptographically Sign Asset</span>
            </>
          )}
        </button>
      </div>

      {/* Success Result Card */}
      {result && (
        <div className="bg-status-genuine/10 border border-status-genuine/20 rounded-lg p-5 space-y-4 shadow-xs">
          <div className="flex items-center gap-2 text-status-genuine">
            <CheckCircle2 className="h-5 w-5 shrink-0" />
            <span className="font-semibold text-sm">Media Asset Authenticated & Registered</span>
          </div>

          <div className="space-y-3">
            {[
              { key: 'asset_id', label: 'Canonical Asset ID', value: result.asset_id },
              { key: 'sha256', label: 'FIPS 180-4 SHA-256 Digest', value: result.sha256_hash },
              { key: 'sig', label: 'ECDSA SECP256R1 Signature', value: result.signature },
            ].map(({ key, label, value }) => value && (
              <div key={key} className="bg-dark-card border border-dark-border rounded p-3">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[11px] text-text-muted font-medium uppercase tracking-wider">{label}</span>
                  <button
                    onClick={() => copy(value, key)}
                    className="text-xs text-brand-purple-light hover:underline inline-flex items-center gap-1"
                  >
                    {copiedKey === key ? <Check className="h-3 w-3 text-status-genuine" /> : <Copy className="h-3 w-3" />}
                    <span>{copiedKey === key ? 'Copied' : 'Copy'}</span>
                  </button>
                </div>
                <p className="text-xs text-brand-purple-light font-mono break-all">{value}</p>
              </div>
            ))}
          </div>

          <p className="text-text-muted text-[11px]">
            Registered at {result.registered_at ? new Date(result.registered_at).toLocaleString() : 'Just now'}
          </p>
        </div>
      )}
    </div>
  );
}
