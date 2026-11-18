import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../store/AuthContext';
import { ShieldCheck, AlertCircle, CheckCircle2, Loader2, ArrowRight } from 'lucide-react';

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: '', password: '', full_name: '', role: 'USER' });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setLoading(true);
    try {
      await register(form.email, form.password, form.full_name, form.role);
      setSuccess('Account created successfully. Redirecting to sign in...');
      setTimeout(() => navigate('/login'), 1500);
    } catch (err) {
      setError(err.response?.data?.detail || 'Account registration failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-dark-bg flex items-center justify-center p-4">
      <div className="w-full max-w-md space-y-6">
        {/* Brand Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center justify-center p-2 rounded-xl bg-brand-purple/10 border border-brand-purple/20 mb-1">
            <ShieldCheck className="h-8 w-8 text-brand-purple-light" />
          </div>
          <h1 className="text-2xl font-bold text-text-main tracking-tight">
            Create Forensics Account
          </h1>
          <p className="text-text-muted text-xs">
            Join the TruthLens media verification and provenance ecosystem
          </p>
        </div>

        {/* Card */}
        <div className="bg-dark-card border border-dark-border rounded-lg p-6 sm:p-8 shadow-xs space-y-5">
          {error && (
            <div className="flex items-center gap-2.5 bg-status-invalid/10 border border-status-invalid/20 rounded-lg p-3 text-status-invalid text-xs">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}
          {success && (
            <div className="flex items-center gap-2.5 bg-status-genuine/10 border border-status-genuine/20 rounded-lg p-3 text-status-genuine text-xs">
              <CheckCircle2 className="h-4 w-4 shrink-0" />
              <span>{success}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {[
              { key: 'full_name', label: 'Full Legal or Organization Name', type: 'text', placeholder: 'Dr. Jane Forensics' },
              { key: 'email', label: 'Work Email Address', type: 'email', placeholder: 'jane@media-lab.org' },
              { key: 'password', label: 'Password (min 8 characters)', type: 'password', placeholder: '••••••••••••' },
            ].map(({ key, label, type, placeholder }) => (
              <div key={key}>
                <label className="block text-xs font-semibold text-text-main uppercase tracking-wider mb-1.5">
                  {label}
                </label>
                <input
                  type={type}
                  required
                  value={form[key]}
                  onChange={(e) => setForm({ ...form, [key]: e.target.value })}
                  className="w-full bg-dark-sidebar border border-dark-border rounded-lg px-3.5 py-2.5 text-text-main placeholder-text-muted focus:outline-none focus:border-brand-purple text-xs sm:text-sm"
                  placeholder={placeholder}
                />
              </div>
            ))}

            <div>
              <label className="block text-xs font-semibold text-text-main uppercase tracking-wider mb-1.5">
                Organizational Role
              </label>
              <select
                value={form.role}
                onChange={(e) => setForm({ ...form, role: e.target.value })}
                className="w-full bg-dark-sidebar border border-dark-border rounded-lg px-3.5 py-2.5 text-text-main focus:outline-none focus:border-brand-purple text-xs sm:text-sm"
              >
                <option value="USER">Analyst — Verify &amp; audit media assets</option>
                <option value="PUBLISHER">Authorized Publisher — Sign &amp; register provenance</option>
              </select>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-brand-purple hover:bg-brand-purple-light disabled:opacity-40 disabled:cursor-not-allowed text-white font-medium rounded-lg px-4 py-2.5 flex items-center justify-center gap-2 transition-all shadow-xs text-xs sm:text-sm"
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Provisioning Account...</span>
                </>
              ) : (
                <>
                  <span>Create Account</span>
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </button>
          </form>

          <div className="pt-2 text-center border-t border-dark-border">
            <p className="text-xs text-text-muted">
              Already have an active credential?{' '}
              <Link to="/login" className="text-brand-purple-light hover:underline font-medium">
                Sign in
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
