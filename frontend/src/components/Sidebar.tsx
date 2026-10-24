import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, GitBranch, AlertOctagon, CheckCircle2, BarChart3, Settings, Shield, Activity } from 'lucide-react';

export const Sidebar: React.FC = () => {
  const navItems = [
    { name: 'Overview', to: '/', icon: LayoutDashboard },
    { name: 'Repositories', to: '/repositories', icon: GitBranch },
    { name: 'CI/CD Failures', to: '/failures', icon: AlertOctagon },
    { name: 'Fix Verification', to: '/fixes', icon: CheckCircle2 },
    { name: 'Analytics', to: '/analytics', icon: BarChart3 },
    { name: 'Settings', to: '/settings', icon: Settings },
  ];
  return <><aside className="hidden md:flex w-64 bg-card border-r border-border flex-col h-screen fixed left-0 top-0 z-30 select-none">
    <div className="h-16 border-b border-border flex items-center px-5">
      <div className="flex items-center space-x-2.5">
        <div className="w-8 h-8 rounded-lg bg-primary/20 border border-primary/40 flex items-center justify-center text-primary-light"><Shield className="w-5 h-5" /></div>
        <div><h1 className="text-sm font-bold tracking-tight text-white">DeployGuard</h1><p className="text-[10px] text-slate-400 font-mono">CI/CD OBSERVABILITY</p></div>
      </div>
    </div>
    <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
      {navItems.map(item => { const Icon = item.icon; return <NavLink key={item.name} to={item.to} end={item.to === '/'} className={({ isActive }) => `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${isActive ? 'bg-primary/10 text-primary-light border border-primary/20' : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/50 border border-transparent'}`}><Icon className="w-4 h-4"/><span>{item.name}</span></NavLink>; })}
    </nav>
    <div className="p-4 border-t border-border bg-slate-950/60"><div className="flex items-center justify-between text-xs text-slate-400"><div className="flex items-center space-x-2"><Activity className="w-3.5 h-3.5 text-emerald-400"/><span className="text-[11px]">Live GitHub integration</span></div><span className="text-[10px] text-slate-500">v1.0</span></div></div>
  </aside>
  <nav aria-label="Mobile navigation" className="md:hidden fixed bottom-0 inset-x-0 z-40 border-t border-border bg-card/95 backdrop-blur-lg px-1 py-2 grid grid-cols-6 gap-1">{navItems.map(item => { const Icon = item.icon; return <NavLink key={item.name} to={item.to} end={item.to === '/'} aria-label={item.name} className={({ isActive }) => `flex flex-col items-center justify-center gap-1 rounded-lg py-1.5 text-[9px] leading-tight ${isActive ? 'text-emerald-300 bg-emerald-400/10' : 'text-slate-400'}`}><Icon className="w-4 h-4"/><span>{item.name === 'CI/CD Failures' ? 'Failures' : item.name === 'Fix Verification' ? 'Verify' : item.name}</span></NavLink>; })}</nav></>;
};
