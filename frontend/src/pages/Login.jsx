import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../store/AuthContext';
import { ShieldCheck, Eye, EyeOff, AlertCircle, Loader2, ArrowRight } from 'lucide-react';

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: '', password: '' });
  const [showPass, setShowPass] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(form.email, form.password);
      navigate('/dashboard');
    } catch (err) {
      const detail = err.response?.data?.detail;
      const msg = typeof detail === 'string'
        ? detail
        : Array.isArray(detail)
          ? (detail[0]?.msg || 'Validation error')
          : 'Authentication failed. Please verify credentials.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const fillDemo = (email, pass) => setForm({ email, password: pass });

  return (
    <div className="min-h-screen bg-dark-bg flex items-center justify-center p-4">
      <div className="w-full max-w-md space-y-6">
        {/* Brand Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center justify-center p-2 rounded-xl bg-brand-purple/10 border border-brand-purple/20 mb-1">
            <ShieldCheck className="h-8 w-8 text-brand-purple-light" />
          </div>
          <h1 className="text-2xl font-bold text-text-main tracking-tight">
            Truth<span className="text-brand-purple-light">Lens</span> Forensics
          </h1>
          <p className="text-text-muted text-xs">
            Digital media authenticity verification &amp; cryptographic provenance platform
          </p>
        </div>

        {/* Card */}
        <div className="bg-dark-card border border-dark-border rounded-lg p-6 sm:p-8 shadow-xs space-y-5">
          <div>
            <h2 className="text-base font-semibold text-text-main">Sign In</h2>
            <p className="text-xs text-text-muted mt-0.5">Enter your credentials to access the forensics workspace</p>
          </div>

          {error && (
            <div className="flex items-center gap-2.5 bg-status-invalid/10 border border-status-invalid/20 rounded-lg p-3 text-status-invalid text-xs">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-text-main uppercase tracking-wider mb-1.5">
                Email Address
              </label>
              <input
                type="email"
                required
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                className="w-full bg-dark-sidebar border border-dark-border rounded-lg px-3.5 py-2.5 text-text-main placeholder-text-muted focus:outline-none focus:border-brand-purple text-xs sm:text-sm"
                placeholder="analyst@organization.com"
              />
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="block text-xs font-semibold text-text-main uppercase tracking-wider">
                  Password
                </label>
              </div>
              <div className="relative">
                <input
                  type={showPass ? 'text' : 'password'}
                  required
                  value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                  className="w-full bg-dark-sidebar border border-dark-border rounded-lg px-3.5 py-2.5 pr-10 text-text-main placeholder-text-muted focus:outline-none focus:border-brand-purple text-xs sm:text-sm"
                  placeholder="••••••••••••"
                />
                <button
                  type="button"
                  onClick={() => setShowPass(!showPass)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-main"
                  tabIndex={-1}
                >
                  {showPass ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-brand-purple hover:bg-brand-purple-light disabled:opacity-40 disabled:cursor-not-allowed text-white font-medium rounded-lg px-4 py-2.5 flex items-center justify-center gap-2 transition-all shadow-xs text-xs sm:text-sm"
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Authenticating...</span>
                </>
              ) : (
                <>
                  <span>Sign In to Platform</span>
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </button>
          </form>

          {/* Quick Demo Credentials */}
          <div className="pt-4 border-t border-dark-border space-y-2">
            <span className="text-[11px] uppercase tracking-wider font-semibold text-text-muted block">
              Quick Test Accounts
            </span>
            <div className="grid grid-cols-3 gap-2">
              {[
                { label: 'Admin', email: 'admin@truthlens.local', pass: 'AdminPass123!' },
                { label: 'Publisher', email: 'publisher@truthlens.local', pass: 'PublisherPass123!' },
                { label: 'Analyst', email: 'user@truthlens.local', pass: 'UserPass123!' },
              ].map((d) => (
                <button
                  key={d.label}
                  type="button"
                  onClick={() => fillDemo(d.email, d.pass)}
                  className="text-xs bg-dark-elevated hover:bg-dark-border text-text-muted hover:text-text-main rounded px-2 py-1.5 border border-dark-border transition-colors font-medium"
                >
                  {d.label}
                </button>
              ))}
            </div>
          </div>

          <div className="pt-1 text-center">
            <p className="text-xs text-text-muted">
              Don't have an authorized account?{' '}
              <Link to="/register" className="text-brand-purple-light hover:underline font-medium">
                Create Account
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
