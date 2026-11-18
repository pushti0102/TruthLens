import { useState } from 'react';
import api from '../services/api';
import { Upload, Lock, CheckCircle, AlertCircle, Loader2, Copy } from 'lucide-react';

export default function PublisherRegister() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [title, setTitle] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [copied, setCopied] = useState('');

  const handleFile = (f) => {
    setFile(f);
    setResult(null);
    setError('');
    const reader = new FileReader();
    reader.onload = (e) => setPreview(e.target.result);
    reader.readAsDataURL(f);
  };

  const handleRegister = async () => {
    if (!file) return;
    setLoading(true);
    setError('');
    setResult(null);
    const formData = new FormData();
    formData.append('file', file);
    if (title) formData.append('title', title);
    try {
      const res = await api.post('/api/publishers/register-media', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setResult(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Registration failed.');
    } finally {
      setLoading(false);
    }
  };

  const copy = (text, key) => {
    navigator.clipboard.writeText(text);
    setCopied(key);
    setTimeout(() => setCopied(''), 2000);
  };

  return (
    <div className="max-w-3xl mx-auto px-4 py-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Register Media</h1>
        <p className="text-slate-400 text-sm mt-1">Cryptographically sign and register your media for provenance tracking</p>
      </div>

      <div className="bg-slate-800 border border-slate-700 rounded-xl p-6 space-y-4">
        {/* File upload */}
        <div
          onClick={() => document.getElementById('pub-file').click()}
          className="border-2 border-dashed border-slate-600 hover:border-cyan-500 rounded-xl p-8 text-center cursor-pointer transition-colors"
        >
          <input
            id="pub-file"
            type="file"
            accept="image/*"
            className="hidden"
            onChange={(e) => handleFile(e.target.files[0])}
          />
          {preview ? (
            <div className="space-y-2">
              <img src={preview} alt="preview" className="max-h-32 mx-auto rounded-lg" />
              <p className="text-slate-300 text-sm">{file.name}</p>
            </div>
          ) : (
            <div className="space-y-2">
              <Upload className="h-10 w-10 text-slate-500 mx-auto" />
              <p className="text-slate-400 text-sm">Click to select media file</p>
            </div>
          )}
        </div>

        {/* Title field */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-1.5">Title (optional)</label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Press Release Photo — Nov 2026"
            className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500 text-sm"
          />
        </div>

        {error && (
          <div className="flex items-center gap-2 bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3 text-red-400 text-sm">
            <AlertCircle className="h-4 w-4" /> {error}
          </div>
        )}

        <button
          onClick={handleRegister}
          disabled={!file || loading}
          className="w-full bg-cyan-500 hover:bg-cyan-400 disabled:opacity-50 text-slate-900 font-semibold rounded-xl py-3 flex items-center justify-center gap-2 transition-colors"
        >
          {loading ? <><Loader2 className="h-5 w-5 animate-spin" /> Registering…</> : <><Lock className="h-5 w-5" /> Register &amp; Sign</>}
        </button>
      </div>

      {/* Success result */}
      {result && (
        <div className="bg-green-500/10 border border-green-500/30 rounded-xl p-6 space-y-4">
          <div className="flex items-center gap-2 text-green-400">
            <CheckCircle className="h-6 w-6" />
            <span className="font-semibold">Media Successfully Registered</span>
          </div>

          {[
            { key: 'asset_id', label: 'Asset ID', value: result.asset_id },
            { key: 'sha256', label: 'SHA-256 Hash', value: result.sha256_hash },
            { key: 'sig', label: 'ECDSA Signature', value: result.signature },
          ].map(({ key, label, value }) => value && (
            <div key={key} className="bg-slate-800/70 rounded-lg p-3">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-slate-400 font-medium">{label}</span>
                <button onClick={() => copy(value, key)} className="text-xs text-cyan-400 hover:text-cyan-300 flex items-center gap-1">
                  <Copy className="h-3 w-3" />{copied === key ? 'Copied!' : 'Copy'}
                </button>
              </div>
              <p className="text-xs text-cyan-300 font-mono break-all">{value}</p>
            </div>
          ))}

          <p className="text-slate-500 text-xs">
            Registered at {result.registered_at ? new Date(result.registered_at).toLocaleString() : 'now'}
          </p>
        </div>
      )}
    </div>
  );
}
