"use client";

import React from 'react';
import Link from 'next/link';

interface BreadcrumbItem {
  label: string;
  href?: string;
  isActive?: boolean;
}

interface BreadcrumbProps {
  items: BreadcrumbItem[];
  className?: string;
}

export const Breadcrumb: React.FC<BreadcrumbProps> = ({ items, className = '' }) => {
  return (
    <nav className={`flex items-center text-sm ${className}`} aria-label="Breadcrumb">
      <ol className="flex items-center space-x-2">
        {items.map((item, index) => {
          const isLast = index === items.length - 1;
          
          return (
            <li key={index} className="flex items-center">
              {item.href && !item.isActive ? (
                <Link 
                  href={item.href}
                  className="text-gray-500 hover:text-blue-600 transition-colors"
                >
                  {item.label}
                </Link>
              ) : (
                <span className={`font-medium ${isLast ? 'text-gray-900' : 'text-gray-500'}`}>
                  {item.label}
                </span>
              )}
              
              {!isLast && (
                <svg 
                  className="mx-2 h-4 w-4 text-gray-400" 
                  fill="currentColor" 
                  viewBox="0 0 20 20"
                >
                  <path 
                    fillRule="evenodd" 
                    d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" 
                    clipRule="evenodd" 
                  />
                </svg>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
};

// Predefined breadcrumb configurations for SETTLE routes
export const SETTLE_BREADCRUMBS = {
  dashboard: [
    { label: 'Home', href: '/' },
    { label: 'SETTLE', href: '/settle' },
    { label: 'Dashboard', isActive: true }
  ],
  query: [
    { label: 'Home', href: '/' },
    { label: 'SETTLE', href: '/settle' },
    { label: 'Query', isActive: true }
  ],
  contribute: [
    { label: 'Home', href: '/' },
    { label: 'SETTLE', href: '/settle' },
    { label: 'Contribute', isActive: true }
  ],
  reports: [
    { label: 'Home', href: '/' },
    { label: 'SETTLE', href: '/settle' },
    { label: 'Reports', isActive: true }
  ]
};