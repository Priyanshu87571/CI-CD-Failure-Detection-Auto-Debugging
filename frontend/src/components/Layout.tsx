import React from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Navbar } from './Navbar';

export const Layout: React.FC = () => {
  return (
    <div className="min-h-screen bg-background flex text-slate-100">
      <Sidebar />
      <div className="flex-1 md:ml-64 flex flex-col min-h-screen min-w-0">
        <Navbar />
        <main className="flex-1 p-4 pb-24 md:p-8 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
