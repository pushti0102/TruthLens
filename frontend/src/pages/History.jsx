import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../services/api';
import {
  History as HistoryIcon,
  Search,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  ShieldCheck,
  AlertTriangle,
  XCircle,
  HelpCircle,
  FileText,
  Filter
} from 'lucide-react';

const VERDICT_STYLES = {
  VERIFIED_TRUSTED: 'text-status-genuine bg-status-genuine/10 border-status-genuine/20',
  INTEGRITY_MISMATCH: 'text-status-invalid bg-status-invalid/10 border-status-invalid/20',
  INVALID_SIGNATURE: 'text-status-invalid bg-status-invalid/10 border-status-invalid/20',
  SUSPICIOUS_AI: 'text-status-warning bg-status-warning/10 border-status-warning/20',
  INCONCLUSIVE: 'text-text-muted bg-dark-elevated border-dark-border',
  VERIFIED_TRUSTED_WITH_AI_CONFLICT: 'text-brand-purple-light bg-brand-purple/10 border-brand-purple/20',
};

export default function History() {
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [filterVerdict, setFilterVerdict] = useState('ALL');
  const [page, setPage] = useState(0);
  const PAGE_SIZE = 10;

  useEffect(() => {
    api.get('/api/media/history')
      .then((r) => setRecords(r.data))
      .catch((err) => console.error('Failed to load history', err))
      .finally(() => setLoading(false));
  }, []);

  const filtered = records.filter((r) => {
    const matchesSearch =
      r.filename?.toLowerCase().includes(search.toLowerCase()) ||
      r.overall_status?.toLowerCase().includes(search.toLowerCase()) ||
      r.ai_label?.toLowerCase().includes(search.toLowerCase()) ||
      r.sha256?.toLowerCase().includes(search.toLowerCase());

    const matchesFilter =
      filterVerdict === 'ALL' ||
      (filterVerdict === 'VERIFIED' && (r.overall_status === 'VERIFIED_TRUSTED' || r.overall_status === 'VERIFIED_TRUSTED_WITH_AI_CONFLICT')) ||
      (filterVerdict === 'TAMPERED' && (r.overall_status === 'INTEGRITY_MISMATCH' || r.overall_status === 'INVALID_SIGNATURE')) ||
      (filterVerdict === 'AI' && r.overall_status === 'SUSPICIOUS_AI') ||
      (filterVerdict === 'INCONCLUSIVE' && r.overall_status === 'INCONCLUSIVE');

    return matchesSearch && matchesFilter;
  });

  const paged = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);
  const totalPages = Math.ceil(filtered.length / PAGE_SIZE);

  return (
    <div className="max-w-6xl mx-auto p-6 md:p-8 lg:p-10 space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2">
          <HistoryIcon className="h-6 w-6 text-brand-purple-light" />
          <h1 className="text-xl md:text-2xl font-bold text-text-main tracking-tight">
            Verification History
          </h1>
        </div>
        <p className="text-text-muted text-xs sm:text-sm mt-1">
          Historical ledger of digital media forensic inspections and cryptographic integrity verifications.
        </p>
      </div>

      {/* Controls: Search & Filter Pills */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        {/* Search Input */}
        <div className="relative max-w-sm w-full">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-muted" />
          <input
            type="text"
            placeholder="Search by filename, hash, or verdict..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(0); }}
            className="w-full bg-dark-card border border-dark-border rounded-lg pl-9 pr-4 py-2 text-xs sm:text-sm text-text-main placeholder-text-muted focus:outline-none focus:border-brand-purple transition-colors"
          />
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-xs">
          {[
            { id: 'ALL', label: 'All Results' },
            { id: 'VERIFIED', label: 'Verified' },
            { id: 'AI', label: 'AI Flagged' },
            { id: 'TAMPERED', label: 'Tampered' },
            { id: 'INCONCLUSIVE', label: 'Inconclusive' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => { setFilterVerdict(tab.id); setPage(0); }}
              className={`px-3 py-1.5 rounded-md font-medium transition-colors whitespace-nowrap ${
                filterVerdict === tab.id
                  ? 'bg-dark-elevated text-brand-purple-light border border-dark-border font-semibold'
                  : 'text-text-muted hover:text-text-main hover:bg-dark-card'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Ledger Table */}
      <div className="bg-dark-card border border-dark-border rounded-lg overflow-hidden shadow-xs">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs sm:text-sm">
            <thead>
              <tr className="border-b border-dark-border bg-dark-sidebar/60 text-text-muted uppercase text-[11px] tracking-wider">
                <th className="px-4 py-3 font-semibold">Media Asset</th>
                <th className="px-4 py-3 font-semibold">Verdict</th>
                <th className="px-4 py-3 font-semibold">AI Cue Assessment</th>
                <th className="px-4 py-3 font-semibold">SHA-256 Digest</th>
                <th className="px-4 py-3 font-semibold">Verified Date</th>
                <th className="px-4 py-3 font-semibold text-right">Report</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-dark-border">
              {loading ? (
                <tr>
                  <td colSpan={6} className="text-center text-text-muted py-12 text-xs">
                    Loading verification history...
                  </td>
                </tr>
              ) : paged.length === 0 ? (
                <tr>
                  <td colSpan={6} className="text-center text-text-muted py-12 text-xs">
                    {search || filterVerdict !== 'ALL'
                      ? 'No verification records match your filters.'
                      : 'No media items verified yet.'}
                  </td>
                </tr>
              ) : (
                paged.map((r) => (
                  <tr
                    key={r.verification_id}
                    className="hover:bg-dark-elevated/40 transition-colors"
                  >
                    <td className="px-4 py-3 text-text-main max-w-[200px] truncate font-medium font-mono text-xs">
                      {r.filename}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className={`text-[11px] px-2.5 py-0.5 rounded border font-medium ${
                        VERDICT_STYLES[r.overall_status] || 'text-text-muted bg-dark-elevated border-dark-border'
                      }`}>
                        {r.overall_status?.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className={`text-[11px] px-2 py-0.5 rounded font-mono ${
                        r.ai_label === 'AI_GENERATED' ? 'bg-status-warning/10 text-status-warning border border-status-warning/20' :
                        r.ai_label === 'REAL' ? 'bg-status-genuine/10 text-status-genuine border border-status-genuine/20' :
                        'text-text-muted'
                      }`}>
                        {r.ai_label || r.ai_status}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-mono text-brand-purple-light text-xs whitespace-nowrap">
                      {r.sha256?.slice(0, 16)}…
                    </td>
                    <td className="px-4 py-3 text-text-muted text-xs whitespace-nowrap">
                      {r.created_at ? new Date(r.created_at).toLocaleDateString() : '—'}
                    </td>
                    <td className="px-4 py-3 text-right whitespace-nowrap">
                      <Link
                        to={`/results/${r.verification_id}`}
                        className="inline-flex items-center gap-1 text-xs text-brand-purple-light hover:underline font-medium"
                      >
                        <span>Audit</span>
                        <ExternalLink className="h-3 w-3" />
                      </Link>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination footer */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-dark-border bg-dark-sidebar/40 text-xs">
            <span className="text-text-muted">
              Showing {page * PAGE_SIZE + 1} to {Math.min((page + 1) * PAGE_SIZE, filtered.length)} of {filtered.length} entries
            </span>
            <div className="flex items-center gap-1">
              <button
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={page === 0}
                className="p-1 rounded text-text-muted hover:text-text-main disabled:opacity-30 disabled:cursor-not-allowed hover:bg-dark-elevated transition-colors"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <span className="px-2 text-text-main font-mono">
                {page + 1} / {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                disabled={page >= totalPages - 1}
                className="p-1 rounded text-text-muted hover:text-text-main disabled:opacity-30 disabled:cursor-not-allowed hover:bg-dark-elevated transition-colors"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
