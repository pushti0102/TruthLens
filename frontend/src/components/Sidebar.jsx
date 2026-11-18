import { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../store/AuthContext';
import {
  ShieldCheck,
  LayoutDashboard,
  History,
  FileKey,
  ScrollText,
  Cpu,
  LogOut,
  Menu,
  X,
  User,
  ExternalLink
} from 'lucide-react';

export default function Sidebar({ children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const navItems = [
    { label: 'Overview', path: '/dashboard', icon: LayoutDashboard, roles: ['USER', 'PUBLISHER', 'ADMIN'] },
    { label: 'Verify Media', path: '/verify', icon: ShieldCheck, roles: ['USER', 'PUBLISHER', 'ADMIN'] },
    { label: 'Verification History', path: '/history', icon: History, roles: ['USER', 'PUBLISHER', 'ADMIN'] },
    { label: 'Publisher Portal', path: '/publisher', icon: FileKey, roles: ['PUBLISHER', 'ADMIN'] },
    { label: 'Audit Logs', path: '/admin', icon: ScrollText, roles: ['ADMIN'] },
    { label: 'System Status', path: '/status', icon: Cpu, roles: ['USER', 'PUBLISHER', 'ADMIN'] },
  ];

  const visibleItems = navItems.filter((item) => !user || item.roles.includes(user.role));

  const roleBadgeColor = {
    ADMIN: 'bg-red-500/10 text-red-400 border border-red-500/20',
    PUBLISHER: 'bg-brand-purple/10 text-brand-purple-light border border-brand-purple/20',
    USER: 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20',
  }[user?.role] || 'bg-slate-800 text-slate-300 border border-slate-700';

  const userInitial = (user?.full_name || user?.email || 'U').charAt(0).toUpperCase();

  return (
    <div className="min-h-screen bg-dark-bg text-text-main flex flex-col md:flex-row">
      {/* Mobile Top Header */}
      <header className="md:hidden bg-dark-sidebar border-b border-dark-border px-4 py-3 flex items-center justify-between sticky top-0 z-40">
        <div className="flex items-center gap-2.5">
          <ShieldCheck className="h-6 w-6 text-brand-purple-light" />
          <span className="font-semibold text-text-main tracking-tight text-lg">
            Truth<span className="text-brand-purple-light">Lens</span>
          </span>
          <span className="text-[10px] tracking-wider uppercase font-semibold text-text-muted bg-dark-elevated px-1.5 py-0.5 rounded border border-dark-border">
            Forensics
          </span>
        </div>
        <button
          onClick={() => setMobileOpen(!mobileOpen)}
          className="p-1.5 rounded-lg text-text-muted hover:text-text-main hover:bg-dark-elevated transition-colors"
          aria-label="Toggle navigation menu"
        >
          {mobileOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
        </button>
      </header>

      {/* Mobile Drawer Backdrop */}
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-xs z-40 md:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Sidebar Navigation (Desktop Fixed, Mobile Drawer) */}
      <aside
        className={`fixed md:sticky top-0 left-0 bottom-0 z-50 w-64 bg-dark-sidebar border-r border-dark-border flex flex-col transition-transform duration-200 ease-in-out md:translate-x-0 ${
          mobileOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
        } h-screen`}
      >
        {/* Brand Header */}
        <div className="h-16 px-5 flex items-center justify-between border-b border-dark-border shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="p-1.5 rounded-lg bg-brand-purple/10 border border-brand-purple/20">
              <ShieldCheck className="h-5 w-5 text-brand-purple-light" />
            </div>
            <div>
              <span className="font-semibold text-text-main tracking-tight text-lg block leading-none">
                Truth<span className="text-brand-purple-light">Lens</span>
              </span>
              <span className="text-[10px] uppercase font-medium tracking-widest text-text-muted">
                Forensics SaaS
              </span>
            </div>
          </div>
          <button
            onClick={() => setMobileOpen(false)}
            className="md:hidden text-text-muted hover:text-text-main p-1"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Navigation Links */}
        <div className="flex-1 py-4 px-3 overflow-y-auto space-y-1">
          <div className="px-2 pb-2 text-[11px] font-semibold uppercase tracking-wider text-text-muted/70">
            Platform Navigation
          </div>
          {visibleItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                onClick={() => setMobileOpen(false)}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150 ${
                    isActive
                      ? 'bg-dark-elevated text-text-main border-l-2 border-brand-purple pl-2.5 shadow-xs'
                      : 'text-text-muted hover:text-text-main hover:bg-dark-card/60'
                  }`
                }
              >
                {({ isActive }) => (
                  <>
                    <Icon
                      className={`h-4.5 w-4.5 shrink-0 ${
                        isActive ? 'text-brand-purple-light' : 'text-text-muted'
                      }`}
                    />
                    <span className="truncate">{item.label}</span>
                  </>
                )}
              </NavLink>
            );
          })}
        </div>

        {/* Security Info & User Profile */}
        <div className="border-t border-dark-border p-3 space-y-3 shrink-0 bg-dark-sidebar">
          {/* Active Security Standard */}
          <div className="px-2 py-1.5 rounded bg-dark-card border border-dark-border/80 flex items-center justify-between text-[11px]">
            <span className="text-text-muted flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-status-genuine animate-pulse"></span>
              FIPS 180-4 • ECDSA
            </span>
            <span className="text-text-muted/80 font-mono">v1.2.0</span>
          </div>

          {/* User Info Card */}
          {user && (
            <div className="p-2.5 rounded-lg bg-dark-card border border-dark-border flex items-center justify-between gap-2">
              <div className="flex items-center gap-2.5 min-w-0">
                <div className="h-8 w-8 rounded-lg bg-brand-purple/20 border border-brand-purple/30 flex items-center justify-center font-bold text-xs text-brand-purple-light shrink-0">
                  {userInitial}
                </div>
                <div className="min-w-0">
                  <p className="text-xs font-medium text-text-main truncate leading-tight">
                    {user.full_name || user.email.split('@')[0]}
                  </p>
                  <span className={`inline-block text-[10px] px-1.5 py-0.5 rounded font-mono font-medium mt-0.5 ${roleBadgeColor}`}>
                    {user.role}
                  </span>
                </div>
              </div>
              <button
                onClick={handleLogout}
                title="Sign out of TruthLens"
                className="p-1.5 rounded-md text-text-muted hover:text-status-invalid hover:bg-status-invalid/10 transition-colors shrink-0"
              >
                <LogOut className="h-4 w-4" />
              </button>
            </div>
          )}
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 min-w-0 min-h-screen overflow-x-hidden bg-dark-bg">
        {children}
      </main>
    </div>
  );
}
