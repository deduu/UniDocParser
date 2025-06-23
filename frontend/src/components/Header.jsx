// =========================================================
// File: src/components/Header.jsx
// =========================================================
import React from 'react';

export default function Header() {
  return (
    <header className="gradient-bg text-white shadow-2xl relative overflow-hidden">
      <div className="absolute inset-0 bg-white/10"></div>
      <div className="container mx-auto px-4 py-6 relative z-10">
        <div className="flex justify-between items-center">
          <div className="flex items-center space-x-4">
            <div className="p-3 bg-white/20 rounded-xl">
              <i className="fas fa-file-pdf text-3xl"></i>
            </div>
            <div>
              <h1 className="text-3xl font-bold">PDF Extraction Pro</h1>
              <p className="text-blue-100 text-sm">Transform your documents with AI‑powered extraction</p>
            </div>
          </div>
          <nav className="hidden md:block">
            <ul className="flex space-x-8">
              {[
                ['Home', 'fa-home'],
                ['Docs', 'fa-book'],
                ['Contact', 'fa-envelope'],
              ].map(([label, icon]) => (
                <li key={label}>
                  <a
                    href="#"
                    className="hover:text-blue-200 transition-colors duration-200 flex items-center space-x-1"
                  >
                    <i className={`fas ${icon} text-sm`}></i>
                    <span>{label}</span>
                  </a>
                </li>
              ))}
            </ul>
          </nav>
        </div>
      </div>
    </header>
  );
}