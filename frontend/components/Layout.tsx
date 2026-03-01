"use client";

import React, { useState } from 'react';
import { ToastProvider, useToast } from './ToastProvider';
import { Breadcrumb, SETTLE_BREADCRUMBS } from './Breadcrumb';
import { Sidebar } from './Sidebar';

interface LayoutProps {
  children: React.ReactNode;
  currentPage: 'dashboard' | 'query' | 'contribute' | 'reports';
}

export const EnterpriseLayout: React.FC<LayoutProps> = ({ children, currentPage }) => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { showToast } = useToast();

  const handleAction = (action: string) => {
    showToast(`${action} completed successfully!`, 'success');
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Mobile menu button */}
      <div className="lg:hidden fixed top-4 left-4 z-50">
        <button
          onClick={() => setSidebarOpen(true)}
          className="p-2 rounded-md bg-white shadow-md text-gray-600 hover:text-gray-900"
          aria-label="Open navigation"
        >
          ☰
        </button>
      </div>

      {/* Sidebar */}
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      {/* Main content */}
      <div className="lg:pl-80">
        {/* Header */}
        <header className="bg-white border-b sticky top-0 z-40">
          <div className="px-6 py-4">
            <div className="flex items-center justify-between">
              <div>
                <Breadcrumb items={SETTLE_BREADCRUMBS[currentPage]} />
                <h1 className="text-2xl font-bold text-gray-900 mt-1 capitalize">
                  {currentPage === 'dashboard' ? 'SETTLE Dashboard' : currentPage}
                </h1>
              </div>
              <div className="flex items-center space-x-4">
                <button
                  onClick={() => handleAction('Refresh')}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
                >
                  ↻ Refresh
                </button>
                <button
                  onClick={() => showToast('Help documentation opened', 'info')}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
                >
                  ?
                </button>
              </div>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="p-6">
          {children}
        </main>
      </div>
    </div>
  );
};

// Wrapper component that includes the ToastProvider
export const EnterpriseApp: React.FC<{ children: React.ReactNode; currentPage: LayoutProps['currentPage'] }> = ({ 
  children, 
  currentPage 
}) => {
  return (
    <ToastProvider>
      <EnterpriseLayout currentPage={currentPage}>
        {children}
      </EnterpriseLayout>
    </ToastProvider>
  );
};