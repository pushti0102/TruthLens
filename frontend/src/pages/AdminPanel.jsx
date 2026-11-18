import { useEffect, useState } from 'react';
import api from '../services/api';
import { Users, FileText, Shield, Loader2, AlertCircle } from 'lucide-react';

function TabBtn({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
        active ? 'bg-cyan-500/20 text-cyan-400' : 'text-slate-400 hover:text-white hover:bg-slate-800'
      }`}
    >
      {children}
    </button>
  );
}

export default function AdminPanel() {
  const [tab, setTab] = useState('users');
  const [users, setUsers] = useState([]);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [updating, setUpdating] = useState(null);

  const fetchUsers = () => {
    setLoading(true);
    api.get('/api/admin/users')
      .then((r) => setUsers(r.data))
      .catch(() => setError('Failed to load users'))
      .finally(() => setLoading(false));
  };

  const fetchLogs = () => {
    setLoading(true);
    api.get('/api/admin/audit-logs?limit=50')
      .then((r) => setLogs(r.data))
      .catch(() => setError('Failed to load audit logs'))
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
      setUsers((u) => u.map((x) => x.id === userId ? { ...x, role: newRole } : x));
    } catch {
      setError('Failed to update role');
    } finally {
      setUpdating(null);
    }
  };

  const roleBadge = (role) => ({
    ADMIN: 'bg-red-500/20 text-red-400 border border-red-500/30',
    PUBLISHER: 'bg-purple-500/20 text-purple-400 border border-purple-500/30',
    USER: 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30',
  }[role] || 'bg-slate-700 text-slate-400');

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <Shield className="h-7 w-7 text-red-400" /> Admin Panel
        </h1>
        <p className="text-slate-400 text-sm mt-1">Manage users and view audit logs</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-slate-700 pb-2">
        <TabBtn active={tab === 'users'} onClick={() => setTab('users')}>
          <span className="flex items-center gap-1.5"><Users className="h-4 w-4" /> Users</span>
        </TabBtn>
        <TabBtn active={tab === 'logs'} onClick={() => setTab('logs')}>
          <span className="flex items-center gap-1.5"><FileText className="h-4 w-4" /> Audit Logs</span>
        </TabBtn>
      </div>

      {error && (
        <div className="flex items-center gap-2 bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3 text-red-400 text-sm">
          <AlertCircle className="h-4 w-4" /> {error}
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-16"><Loader2 className="h-8 w-8 text-cyan-400 animate-spin" /></div>
      ) : tab === 'users' ? (
        <div className="bg-slate-800 border border-slate-700 rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-700">
                {['Name', 'Email', 'Role', 'Status', 'Actions'].map((h) => (
                  <th key={h} className="text-left text-xs text-slate-400 font-medium px-4 py-3">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-b border-slate-700 last:border-0 hover:bg-slate-700/40">
                  <td className="px-4 py-3 text-white">{u.full_name || '—'}</td>
                  <td className="px-4 py-3 text-slate-300">{u.email}</td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${roleBadge(u.role)}`}>{u.role}</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${u.is_active ? 'text-green-400 bg-green-400/10' : 'text-red-400 bg-red-400/10'}`}>
                      {u.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <select
                      value={u.role}
                      onChange={(e) => changeRole(u.id, e.target.value)}
                      disabled={updating === u.id}
                      className="bg-slate-700 border border-slate-600 text-white text-xs rounded-lg px-2 py-1 focus:outline-none focus:ring-1 focus:ring-cyan-500"
                    >
                      {['USER', 'PUBLISHER', 'ADMIN'].map((r) => (
                        <option key={r} value={r}>{r}</option>
                      ))}
                    </select>
                    {updating === u.id && <Loader2 className="h-3 w-3 text-cyan-400 animate-spin inline ml-2" />}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="bg-slate-800 border border-slate-700 rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-700">
                {['Event', 'Actor', 'IP', 'Timestamp', 'Success'].map((h) => (
                  <th key={h} className="text-left text-xs text-slate-400 font-medium px-4 py-3">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {logs.length === 0 ? (
                <tr><td colSpan={5} className="text-center text-slate-500 py-12">No audit logs yet.</td></tr>
              ) : logs.map((l) => (
                <tr key={l.id} className="border-b border-slate-700 last:border-0 hover:bg-slate-700/30">
                  <td className="px-4 py-3 text-white font-mono text-xs">{l.event_type}</td>
                  <td className="px-4 py-3 text-slate-300 text-xs truncate max-w-[140px]">{l.actor_email || l.actor_id || '—'}</td>
                  <td className="px-4 py-3 text-slate-400 text-xs">{l.ip_address || '—'}</td>
                  <td className="px-4 py-3 text-slate-400 text-xs">{new Date(l.created_at).toLocaleString()}</td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded-full ${l.success ? 'text-green-400 bg-green-400/10' : 'text-red-400 bg-red-400/10'}`}>
                      {l.success ? '✓' : '✗'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
