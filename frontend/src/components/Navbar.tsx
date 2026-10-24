import React from 'react';
import { User, RefreshCw, LogOut } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { api } from '../lib/api';

interface NavbarProps {
  onRefresh?: () => void;
  isRefreshing?: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({ onRefresh, isRefreshing = false }) => {
  const navigate = useNavigate();
  const [profile, setProfile] = React.useState<{display_name:string;email:string}|null>(null);
  React.useEffect(() => { api.getMe().then(setProfile).catch(() => setProfile(null)); }, []);
  const signOut = async () => { await api.logout(); navigate('/login', { replace: true }); window.location.reload(); };
  return (
    <header className="h-16 border-b border-border bg-card/80 backdrop-blur-md sticky top-0 z-20 flex items-center justify-between px-4 md:px-8">
      <div className="flex items-center gap-3 min-w-0">
        <span className="inline-flex h-2 w-2 rounded-full bg-emerald-400" aria-hidden="true" />
        <div className="min-w-0">
          <p className="text-sm font-semibold text-white leading-tight">Your workspace</p>
          <p className="text-xs text-slate-400 mt-0.5">Live GitHub Actions monitoring</p>
        </div>
      </div>

      <div className="flex items-center space-x-4">
        {onRefresh && (
          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            className="flex items-center space-x-1.5 px-3 py-1.5 text-xs text-slate-300 hover:text-white bg-slate-900 border border-border rounded-md hover:border-slate-700 transition-colors"
            title="Refresh metrics"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
            <span>Sync</span>
          </button>
        )}

        <div className="flex items-center space-x-3 border-l border-border pl-4">
          <div className="w-7 h-7 rounded-full bg-indigo-950 border border-indigo-700/60 flex items-center justify-center text-indigo-300">
            <User className="w-3.5 h-3.5" />
          </div>
          <div className="text-left hidden sm:block">
            <p className="text-xs font-medium text-white leading-none">{profile?.display_name ?? 'DeployGuard User'}</p>
            <p className="text-[10px] text-slate-500 font-mono mt-0.5">{profile?.email ?? ''}</p>
          </div>
        </div>
        <button onClick={signOut} title="Sign out" aria-label="Sign out" className="p-2 rounded-lg text-slate-400 hover:text-rose-300 hover:bg-rose-400/10 transition-colors"><LogOut className="w-4 h-4" /></button>
      </div>
    </header>
  );
};
