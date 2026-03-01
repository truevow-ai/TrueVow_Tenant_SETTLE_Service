"use client";

import React from 'react';
import { EnterpriseApp } from '../components/Layout';
import { useToast } from '../components/ToastProvider';

const DashboardPage = () => {
  const { showToast } = useToast();

  const handleMockAction = (action: string) => {
    showToast(`${action} initiated`, 'info');
    setTimeout(() => {
      showToast(`${action} completed successfully!`, 'success');
    }, 1500);
  };

  return (
    <EnterpriseApp currentPage="dashboard">
      <div className="space-y-6">
        {/* Welcome Section */}
        <div className="bg-gradient-to-r from-blue-600 to-indigo-700 rounded-xl p-6 text-white">
          <h2 className="text-2xl font-bold mb-2">Welcome to SETTLE</h2>
          <p className="text-blue-100">
            Access the world's largest bar-compliant settlement database for plaintiff attorneys.
          </p>
        </div>

        {/* Quick Actions */}
        <div>
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { title: 'Query Database', description: 'Get settlement range estimates', icon: '🔍', action: 'Query' },
              { title: 'Contribute Data', description: 'Submit settlement information', icon: '📤', action: 'Contribute' },
              { title: 'View Reports', description: 'Access generated reports', icon: '📋', action: 'Generate Report' },
              { title: 'My Profile', description: 'Manage account settings', icon: '👤', action: 'Profile Update' }
            ].map((card, index) => (
              <div 
                key={index}
                className="bg-white rounded-lg border p-6 hover:shadow-md transition-shadow cursor-pointer"
                onClick={() => handleMockAction(card.action)}
              >
                <div className="text-3xl mb-3">{card.icon}</div>
                <h4 className="font-semibold text-gray-900 mb-1">{card.title}</h4>
                <p className="text-sm text-gray-600">{card.description}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Recent Activity */}
        <div>
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Recent Activity</h3>
          <div className="bg-white rounded-lg border">
            <div className="p-6">
              <div className="space-y-4">
                {[
                  { action: 'Query submitted', time: '2 hours ago', status: 'completed' },
                  { action: 'Report generated', time: '1 day ago', status: 'completed' },
                  { action: 'Data contribution pending review', time: '3 days ago', status: 'pending' },
                  { action: 'Account created', time: '1 week ago', status: 'completed' }
                ].map((activity, index) => (
                  <div key={index} className="flex items-center justify-between py-3 border-b last:border-b-0">
                    <div className="flex items-center">
                      <div className={`w-3 h-3 rounded-full mr-3 ${
                        activity.status === 'completed' ? 'bg-green-500' : 'bg-yellow-500'
                      }`}></div>
                      <span className="text-gray-900">{activity.action}</span>
                    </div>
                    <span className="text-sm text-gray-500">{activity.time}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Sample Toast Triggers */}
        <div>
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Try Toast Notifications</h3>
          <div className="bg-white rounded-lg border p-6">
            <div className="flex flex-wrap gap-3">
              <button
                onClick={() => showToast('Success! Your action was completed.', 'success')}
                className="px-4 py-2 bg-green-500 text-white rounded-md hover:bg-green-600"
              >
                Success Toast
              </button>
              <button
                onClick={() => showToast('Warning: Please check your input.', 'warning')}
                className="px-4 py-2 bg-yellow-500 text-gray-900 rounded-md hover:bg-yellow-600"
              >
                Warning Toast
              </button>
              <button
                onClick={() => showToast('Error: Something went wrong.', 'error')}
                className="px-4 py-2 bg-red-500 text-white rounded-md hover:bg-red-600"
              >
                Error Toast
              </button>
              <button
                onClick={() => showToast('Info: New update available.', 'info')}
                className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600"
              >
                Info Toast
              </button>
            </div>
          </div>
        </div>
      </div>
    </EnterpriseApp>
  );
};

export default DashboardPage;