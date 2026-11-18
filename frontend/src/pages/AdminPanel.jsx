import { useEffect, useState } from 'react';
import api from '../services/api';
import {
  Users,
  ScrollText,
  Shield,
  Loader2,
  AlertCircle,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Search,
  Filter
} from 'lucide-react';

export default function AdminPanel() {
  const [tab, setTab] = useState('users');
  const [users, setUsers] = useState([]);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [updating, setUpdating] = useState(null);
  const [logFilter, setLogFilter] = useState('');

  const fetchUsers = () => {
    setLoading(true);
    api.get('/api/admin/users')
      .then((r) => setUsers(r.data))
      .catch(() => setError('Failed to retrieve user registry.'))
      .finally(() => setLoading(false));
  };

  const fetchLogs = () => {
    setLoading(true);
    api.get('/api/admin/audit-logs?limit=100')
      .then((r) => setLogs(r.data))
      .catch(() => setError('Failed to retrieve security audit logs.'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    if (tab === 'users') fetchUsers();
    else fetchLogs();
    setError('');
  }, [tab]);

  const changeRole = async (userId, newRole) => {
    setUpdating(userId);
    try {
      await api.patch(`/api/admin/users/${userId}/role`, { role: newRole });
      setUsers((u) => u.map((x) => (x.id === userId ? { ...x, role: newRole } : x)));
    } catch {
      setError('Role update failed. Verify administrative permissions.');
    } finally {
      setUpdating(null);
    }
  };

  const roleBadge = (role) => ({
    ADMIN: 'bg-status-invalid/10 text-status-invalid border border-status-invalid/20',
    PUBLISHER: 'bg-brand-purple/10 text-brand-purple-light border border-brand-purple/20',
    USER: 'bg-status-genuine/10 text-status-genuine border border-status-genuine/20',
  }[role] || 'bg-dark-elevated text-text-muted border border-dark-border');

  const filteredLogs = logs.filter((l) =>
    !logFilter ||
    l.event_type?.toLowerCase().includes(logFilter.toLowerCase()) ||
    l.actor_email?.toLowerCase().includes(logFilter.toLowerCase()) ||
    l.ip_address?.toLowerCase().includes(logFilter.toLowerCase())
  );

  return (
    <div className="max-w-6xl mx-auto p-6 md:p-8 lg:p-10 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Shield className="h-6 w-6 text-brand-purple-light" />
            <h1 className="text-xl md:text-2xl font-bold text-text-main tracking-tight">
              Security & Administration
            </h1>
          </div>
          <p className="text-text-muted text-xs sm:text-sm mt-1">
            Access-controlled RBAC management and immutable security audit logging.
          </p>
        </div>
        <button
          onClick={tab === 'users' ? fetchUsers : fetchLogs}
          disabled={loading}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-dark-card hover:bg-dark-elevated text-xs font-medium text-text-muted hover:text-text-main border border-dark-border transition-colors self-start sm:self-auto"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Navigation Tabs */}
      <div className="flex gap-2 border-b border-dark-border pb-2">
        <button
          onClick={() => setTab('users')}
          className={`flex items-center gap-2 px-4 py-2 text-xs font-medium rounded-lg transition-colors ${
            tab === 'users'
              ? 'bg-dark-elevated text-brand-purple-light border border-dark-border'
              : 'text-text-muted hover:text-text-main hover:bg-dark-card'
          }`}
        >
          <Users className="h-4 w-4" />
          <span>User Registry & RBAC</span>
        </button>
        <button
          onClick={() => setTab('logs')}
          className={`flex items-center gap-2 px-4 py-2 text-xs font-medium rounded-lg transition-colors ${
            tab === 'logs'
              ? 'bg-dark-elevated text-brand-purple-light border border-dark-border'
              : 'text-text-muted hover:text-text-main hover:bg-dark-card'
          }`}
        >
          <ScrollText className="h-4 w-4" />
          <span>Security Audit Logs</span>
        </button>
      </div>

      {error && (
        <div className="flex items-center gap-2.5 bg-status-invalid/10 border border-status-invalid/20 rounded-lg p-3 text-status-invalid text-xs">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {loading ? (
        <div className="flex flex-col items-center justify-center py-20 space-y-2">
          <Loader2 className="h-8 w-8 text-brand-purple animate-spin" />
          <span className="text-xs text-text-muted font-mono uppercase tracking-wider">
            Querying administrative registry...
          </span>
        </div>
      ) : tab === 'users' ? (
        <div className="bg-dark-card border border-dark-border rounded-lg overflow-hidden shadow-xs">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs sm:text-sm">
              <thead>
                <tr className="border-b border-dark-border bg-dark-sidebar/60 text-text-muted uppercase text-[11px] tracking-wider">
                  <th className="px-4 py-3 font-semibold">User</th>
                  <th className="px-4 py-3 font-semibold">Email</th>
                  <th className="px-4 py-3 font-semibold">Role</th>
                  <th className="px-4 py-3 font-semibold">Account State</th>
                  <th className="px-4 py-3 font-semibold text-right">Assign Role</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-dark-border">
                {users.map((u) => (
                  <tr key={u.id} className="hover:bg-dark-elevated/40 transition-colors">
                    <td className="px-4 py-3 text-text-main font-medium">{u.full_name || '—'}</td>
                    <td className="px-4 py-3 text-text-muted font-mono text-xs">{u.email}</td>
                    <td className="px-4 py-3">
                      <span className={`text-[11px] px-2.5 py-0.5 rounded font-mono font-medium ${roleBadge(u.role)}`}>
                        {u.role}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center gap-1.5 text-xs ${
                        u.is_active ? 'text-status-genuine' : 'text-status-invalid'
                      }`}>
                        <span className={`h-1.5 w-1.5 rounded-full ${u.is_active ? 'bg-status-genuine' : 'bg-status-invalid'}`} />
                        {u.is_active ? 'Active' : 'Suspended'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="inline-flex items-center gap-2">
                        <select
                          value={u.role}
                          onChange={(e) => changeRole(u.id, e.target.value)}
                          disabled={updating === u.id}
                          className="bg-dark-sidebar border border-dark-border text-text-main text-xs rounded px-2.5 py-1 focus:outline-none focus:border-brand-purple"
                        >
                          {['USER', 'PUBLISHER', 'ADMIN'].map((r) => (
                            <option key={r} value={r}>{r}</option>
                          ))}
                        </select>
                        {updating === u.id && (
                          <Loader2 className="h-3.5 w-3.5 text-brand-purple animate-spin" />
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Search audit logs */}
          <div className="relative max-w-sm">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-muted" />
            <input
              type="text"
              placeholder="Filter by event type, email, or IP..."
              value={logFilter}
              onChange={(e) => setLogFilter(e.target.value)}
              className="w-full bg-dark-card border border-dark-border rounded-lg pl-9 pr-4 py-2 text-xs sm:text-sm text-text-main placeholder-text-muted focus:outline-none focus:border-brand-purple transition-colors"
            />
          </div>

          <div className="bg-dark-card border border-dark-border rounded-lg overflow-hidden shadow-xs">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs sm:text-sm">
                <thead>
                  <tr className="border-b border-dark-border bg-dark-sidebar/60 text-text-muted uppercase text-[11px] tracking-wider">
                    <th className="px-4 py-3 font-semibold">Event Type</th>
                    <th className="px-4 py-3 font-semibold">Subject / Actor</th>
                    <th className="px-4 py-3 font-semibold">Origin IP</th>
                    <th className="px-4 py-3 font-semibold">Timestamp</th>
                    <th className="px-4 py-3 font-semibold text-right">Outcome</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-dark-border">
                  {filteredLogs.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="text-center text-text-muted py-12 text-xs">
                        No audit events recorded.
                      </td>
                    </tr>
                  ) : (
                    filteredLogs.map((l) => (
                      <tr key={l.id} className="hover:bg-dark-elevated/40 transition-colors">
                        <td className="px-4 py-3 font-mono text-brand-purple-light text-xs font-medium">
                          {l.event_type}
                        </td>
                        <td className="px-4 py-3 text-text-muted text-xs truncate max-w-[160px]">
                          {l.actor_email || l.actor_id || 'System Anonymous'}
                        </td>
                        <td className="px-4 py-3 text-text-muted font-mono text-xs">{l.ip_address || '127.0.0.1'}</td>
                        <td className="px-4 py-3 text-text-muted text-xs">
                          {new Date(l.created_at).toLocaleString()}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <span className={`inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded font-medium ${
                            l.success
                              ? 'text-status-genuine bg-status-genuine/10 border border-status-genuine/20'
                              : 'text-status-invalid bg-status-invalid/10 border border-status-invalid/20'
                          }`}>
                            {l.success ? <CheckCircle2 className="h-3 w-3" /> : <XCircle className="h-3 w-3" />}
                            <span>{l.success ? 'Success' : 'Denied'}</span>
                          </span>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
