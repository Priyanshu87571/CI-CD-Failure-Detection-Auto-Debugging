import React, { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Layout } from './components/Layout';
import { Overview } from './pages/Overview';
import { Repositories } from './pages/Repositories';
import { Failures } from './pages/Failures';
import { FailureDetailView } from './pages/FailureDetail';
import { FixReview } from './pages/FixReview';
import { Analytics } from './pages/Analytics';
import { SettingsPage } from './pages/Settings';
import { AuthPage } from './pages/Auth';
import { api, clearStoredToken, getStoredToken } from './lib/api';

const queryClient = new QueryClient({ defaultOptions: { queries: { refetchOnWindowFocus: false, retry: 1 } } });
const ProtectedApp: React.FC = () => {
  const [state, setState] = useState<'loading'|'authenticated'|'guest'>(getStoredToken()?'loading':'guest');
  useEffect(() => {
    if (!getStoredToken()) { setState('guest'); return; }
    api.getMe().then(() => setState('authenticated')).catch(() => { clearStoredToken(); setState('guest'); });
  }, []);
  if (state === 'loading') return <div className="min-h-screen bg-[#080d17] flex items-center justify-center text-slate-400"><div className="animate-pulse">Loading your secure workspace…</div></div>;
  if (state === 'guest') return <AuthPage />;
  return <Routes><Route path="/" element={<Layout />}><Route index element={<Overview />} /><Route path="repositories" element={<Repositories />} /><Route path="failures" element={<Failures />} /><Route path="failures/:id" element={<FailureDetailView />} /><Route path="fixes" element={<FixReview />} /><Route path="fixes/:id" element={<FixReview />} /><Route path="analytics" element={<Analytics />} /><Route path="settings" element={<SettingsPage />} /><Route path="*" element={<Navigate to="/" replace />} /></Route></Routes>;
};
export const App: React.FC = () => <QueryClientProvider client={queryClient}><BrowserRouter><ProtectedApp /></BrowserRouter></QueryClientProvider>;
export default App;
