import React, { useState } from 'react';
import { Navigate } from 'react-router-dom';
import { Activity, ArrowRight, Eye, EyeOff, ShieldCheck, Sparkles } from 'lucide-react';
import { api, getStoredToken } from '../lib/api';

export const AuthPage: React.FC = () => {
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  if (getStoredToken()) return <Navigate to="/" replace />;

  const submit = async (event: React.FormEvent) => {
    event.preventDefault(); setLoading(true); setError('');
    try {
      if (mode === 'register') await api.register(name.trim(), email.trim(), password);
      else await api.login(email.trim(), password);
      window.location.assign('/');
    } catch (err) { setError(err instanceof Error ? err.message : 'Unable to authenticate. Please try again.'); }
    finally { setLoading(false); }
  };

  return <div className="min-h-screen bg-[#080d17] text-slate-100 grid lg:grid-cols-2">
    <section className="hidden lg:flex flex-col justify-between p-12 border-r border-white/5 relative overflow-hidden">
      <div className="absolute -top-32 -left-24 w-[30rem] h-[30rem] rounded-full bg-emerald-500/10 blur-3xl" />
      <div className="absolute bottom-0 right-0 w-96 h-96 rounded-full bg-cyan-500/10 blur-3xl" />
      <div className="relative flex items-center gap-3"><div className="w-11 h-11 rounded-xl bg-emerald-400/10 border border-emerald-300/20 flex items-center justify-center"><Activity className="text-emerald-300" /></div><div><div className="text-xl font-bold tracking-tight">DeployGuard</div><div className="text-xs text-slate-500">CI/CD intelligence platform</div></div></div>
      <div className="relative max-w-xl"><div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-emerald-400/20 bg-emerald-400/5 text-emerald-300 text-xs mb-6"><Sparkles size={14}/> Evidence-first failure analysis</div><h1 className="text-5xl font-semibold leading-tight tracking-tight">Ship with confidence.<br/><span className="text-emerald-300">Debug with clarity.</span></h1><p className="text-slate-400 mt-6 text-lg leading-8">Turn noisy CI/CD failures into actionable evidence, root-cause hypotheses, and reviewable fix proposals.</p>
        <div className="grid grid-cols-2 gap-3 mt-10"><div className="rounded-xl border border-white/10 bg-white/[0.03] p-4"><ShieldCheck className="text-emerald-300 mb-3" size={20}/><p className="font-medium">Secure by design</p><p className="text-sm text-slate-500 mt-1">Protected workspace access</p></div><div className="rounded-xl border border-white/10 bg-white/[0.03] p-4"><Activity className="text-cyan-300 mb-3" size={20}/><p className="font-medium">Explainable analysis</p><p className="text-sm text-slate-500 mt-1">Evidence before assumptions</p></div></div>
      </div><p className="relative text-xs text-slate-600">DeployGuard · Final-year engineering project</p>
    </section>
    <section className="flex items-center justify-center p-6 sm:p-10"><div className="w-full max-w-md">
      <div className="lg:hidden flex items-center gap-3 mb-10"><div className="w-10 h-10 rounded-xl bg-emerald-400/10 flex items-center justify-center"><Activity className="text-emerald-300"/></div><span className="text-xl font-bold">DeployGuard</span></div>
      <div className="mb-8"><p className="text-sm text-emerald-300 font-medium mb-3">WELCOME TO DEPLOYGUARD</p><h2 className="text-3xl font-semibold tracking-tight">{mode === 'login' ? 'Sign in to your workspace' : 'Create your account'}</h2><p className="text-slate-400 mt-3">{mode === 'login' ? 'Continue investigating your pipeline failures.' : 'Start analyzing CI/CD failures in your own workspace.'}</p></div>
      <form onSubmit={submit} className="space-y-5">
        {mode === 'register' && <label className="block text-sm text-slate-300">Full name<input required minLength={2} maxLength={100} value={name} onChange={e=>setName(e.target.value)} className="mt-2 w-full rounded-xl bg-[#101827] border border-slate-700/80 px-4 py-3 outline-none focus:border-emerald-400 focus:ring-2 focus:ring-emerald-400/10" placeholder="Your name" /></label>}
        <label className="block text-sm text-slate-300">Email address<input type="email" required value={email} onChange={e=>setEmail(e.target.value)} className="mt-2 w-full rounded-xl bg-[#101827] border border-slate-700/80 px-4 py-3 outline-none focus:border-emerald-400 focus:ring-2 focus:ring-emerald-400/10" placeholder="you@example.com" autoComplete="email" /></label>
        <label className="block text-sm text-slate-300">Password<div className="relative mt-2"><input type={showPassword?'text':'password'} required minLength={mode==='register'?8:1} maxLength={128} value={password} onChange={e=>setPassword(e.target.value)} className="w-full rounded-xl bg-[#101827] border border-slate-700/80 px-4 py-3 pr-12 outline-none focus:border-emerald-400 focus:ring-2 focus:ring-emerald-400/10" placeholder="Enter your password" autoComplete={mode==='login'?'current-password':'new-password'}/><button type="button" onClick={()=>setShowPassword(!showPassword)} className="absolute right-3 top-3.5 text-slate-500 hover:text-slate-200" aria-label={showPassword?'Hide password':'Show password'}>{showPassword?<EyeOff size={18}/>:<Eye size={18}/>}</button></div>{mode==='register'&&<span className="block text-xs text-slate-500 mt-2">Use at least 8 characters.</span>}</label>
        {error && <div role="alert" className="rounded-lg border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-300">{error}</div>}
        <button disabled={loading} className="w-full flex items-center justify-center gap-2 rounded-xl bg-emerald-400 hover:bg-emerald-300 disabled:opacity-60 text-slate-950 font-semibold py-3.5 transition-colors">{loading?'Please wait…':mode==='login'?'Sign in':'Create account'}{!loading&&<ArrowRight size={17}/>}</button>
      </form>
      <p className="text-sm text-center text-slate-400 mt-7">{mode==='login'?"Don't have an account?":"Already have an account?"} <button onClick={()=>{setMode(mode==='login'?'register':'login');setError('')}} className="text-emerald-300 hover:text-emerald-200 font-medium">{mode==='login'?'Create one':'Sign in'}</button></p>
      <p className="text-xs text-slate-600 text-center mt-8">Your account is protected by server-side authentication.</p>
    </div></section>
  </div>;
};
