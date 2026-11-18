import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../services/api';
import { Clock, Search, ChevronLeft, ChevronRight, ExternalLink } from 'lucide-react';

const VERDICT_STYLES = {
  VERIFIED_TRUSTED: 'text-cyan-400 bg-cyan-400/10 border-cyan-400/20',
  INTEGRITY_MISMATCH: 'text-red-400 bg-red-400/10 border-red-400/20',
  INVALID_SIGNATURE: 'text-red-400 bg-red-400/10 border-red-400/20',
  SUSPICIOUS_AI: 'text-amber-400 bg-amber-400/10 border-amber-400/20',
  INCONCLUSIVE: 'text-slate-400 bg-slate-400/10 border-slate-400/20',
  VERIFIED_TRUSTED_WITH_AI_CONFLICT: 'text-purple-400 bg-purple-400/10 border-purple-400/20',
};

export default function History() {
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(0);
  const PAGE_SIZE = 10;

  useEffect(() => {
    api.get('/api/media/history')
      .then((r) => setRecords(r.data))
      .finally(() => setLoading(false));
  }, []);

  const filtered = records.filter((r) =>
    r.filename?.toLowerCase().includes(search.toLowerCase()) ||
    r.overall_status?.toLowerCase().includes(search.toLowerCase()) ||
    r.ai_label?.toLowerCase().includes(search.toLowerCase())
  );
  const paged = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);
  const totalPages = Math.ceil(filtered.length / PAGE_SIZE);

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Verification History</h1>
        <p className="text-slate-400 text-sm mt-1">Audit log of all verified media assets</p>
      </div>

      {/* Search */}
      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
        <input
          type="text"
          placeholder="Search by filename or verdict…"
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(0); }}
          className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-9 pr-4 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500"
        />
      </div>

      {/* Table */}
      <div className="bg-slate-800 border border-slate-700 rounded-xl overflow-hidden shadow-xl">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-700 bg-slate-800/80">
              {['Filename', 'Trust Verdict', 'AI Detection', 'SHA-256 Digest', 'Date', ''].map((h) => (
                <th key={h} className="text-left text-xs text-slate-400 font-medium px-4 py-3">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={6} className="text-center text-slate-500 py-12">Loading verification history…</td></tr>
            ) : paged.length === 0 ? (
              <tr><td colSpan={6} className="text-center text-slate-500 py-12">
                {search ? 'No results match your search query.' : 'No media verified yet.'}
              </td></tr>
            ) : (
              paged.map((r) => (
                <tr key={r.verification_id} className="border-b border-slate-700 hover:bg-slate-700/40 transition-colors">
                  <td className="px-4 py-3 text-white max-w-[200px] truncate font-medium">{r.filename}</td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2.5 py-0.5 rounded-full border font-semibold ${VERDICT_STYLES[r.overall_status] || 'text-slate-400 bg-slate-700'}`}>
                      {r.overall_status?.replace(/_/g, ' ')}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded font-mono ${
                      r.ai_label === 'AI_GENERATED' ? 'bg-amber-500/20 text-amber-300' :
                      r.ai_label === 'REAL' ? 'bg-green-500/20 text-green-300' :
                      'text-slate-400'
                    }`}>
                      {r.ai_label || r.ai_status}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-mono text-cyan-300 text-xs">{r.sha256?.slice(0, 16)}…</td>
                  <td className="px-4 py-3 text-slate-400 text-xs">{r.created_at}</td>
                  <td className="px-4 py-3">
                    <Link to={`/results/${r.verification_id}`} className="text-cyan-400 hover:text-cyan-300">
                      <ExternalLink className="h-4 w-4" />
                    </Link>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between text-sm text-slate-400">
          <span>{filtered.length} total records</span>
          <div className="flex items-center gap-2">
            <button onClick={() => setPage((p) => Math.max(0, p - 1))} disabled={page === 0}
              className="p-1.5 rounded hover:bg-slate-700 disabled:opacity-40"><ChevronLeft className="h-4 w-4" /></button>
            <span>{page + 1} / {totalPages}</span>
            <button onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))} disabled={page >= totalPages - 1}
              className="p-1.5 rounded hover:bg-slate-700 disabled:opacity-40"><ChevronRight className="h-4 w-4" /></button>
          </div>
        </div>
      )}
    </div>
  );
}
