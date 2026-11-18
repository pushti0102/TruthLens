import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../store/AuthContext';
import { Shield, LogOut, Menu, X } from 'lucide-react';
import { useState } from 'react';

const NAV_ITEMS = [
  { label: 'Dashboard', path: '/dashboard', roles: ['USER', 'PUBLISHER', 'ADMIN'] },
  { label: 'Verify Media', path: '/verify', roles: ['USER', 'PUBLISHER', 'ADMIN'] },
  { label: 'History', path: '/history', roles: ['USER', 'PUBLISHER', 'ADMIN'] },
  { label: 'Register Media', path: '/publisher', roles: ['PUBLISHER', 'ADMIN'] },
  { label: 'Admin Panel', path: '/admin', roles: ['ADMIN'] },
  { label: 'System Status', path: '/status', roles: ['USER', 'PUBLISHER', 'ADMIN'] },
];

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [open, setOpen] = useState(false);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const visible = NAV_ITEMS.filter((item) => !user || item.roles.includes(user.role));

  const roleBadge = {
    ADMIN: 'bg-red-500/20 text-red-400 border border-red-500/30',
    PUBLISHER: 'bg-purple-500/20 text-purple-400 border border-purple-500/30',
    USER: 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30',
  }[user?.role] || '';

  return (
    <nav className="bg-slate-900 border-b border-slate-700 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/dashboard" className="flex items-center gap-2 group">
            <Shield className="h-7 w-7 text-cyan-400 group-hover:text-cyan-300 transition-colors" />
            <span className="text-xl font-bold text-white tracking-tight">
              Truth<span className="text-cyan-400">Lens</span>
            </span>
          </Link>

          {/* Desktop nav */}
          <div className="hidden md:flex items-center gap-1">
            {visible.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  location.pathname === item.path
                    ? 'bg-cyan-500/20 text-cyan-400'
                    : 'text-slate-400 hover:text-white hover:bg-slate-800'
                }`}
              >
                {item.label}
              </Link>
            ))}
          </div>

          {/* User info + logout */}
          <div className="hidden md:flex items-center gap-3">
            {user && (
              <div className="flex items-center gap-2">
                <span className="text-slate-400 text-sm">{user.email}</span>
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${roleBadge}`}>
                  {user.role}
                </span>
              </div>
            )}
            <button
              onClick={handleLogout}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            >
              <LogOut className="h-4 w-4" />
              Logout
            </button>
          </div>

          {/* Mobile menu toggle */}
          <button
            className="md:hidden text-slate-400 hover:text-white"
            onClick={() => setOpen(!open)}
          >
            {open ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      {open && (
        <div className="md:hidden bg-slate-900 border-t border-slate-700 px-4 py-3 space-y-1">
          {visible.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              onClick={() => setOpen(false)}
              className={`block px-3 py-2 rounded-lg text-sm font-medium ${
                location.pathname === item.path
                  ? 'bg-cyan-500/20 text-cyan-400'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800'
              }`}
            >
              {item.label}
            </Link>
          ))}
          <button
            onClick={handleLogout}
            className="w-full text-left px-3 py-2 rounded-lg text-sm text-red-400 hover:bg-slate-800"
          >
            Logout
          </button>
        </div>
      )}
    </nav>
  );
}
