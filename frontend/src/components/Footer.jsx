
// =========================================================
// File: src/components/Footer.jsx
// =========================================================
import React from 'react';

export default function Footer() {
  return (
    <footer className="bg-gray-900 text-white mt-16">
      <div className="container mx-auto px-4 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          <div className="md:col-span-2">
            <div className="flex items-center space-x-3 mb-4">
              <div className="p-2 bg-blue-600 rounded-lg">
                <i className="fas fa-file-pdf text-xl"></i>
              </div>
              <h3 className="text-2xl font-bold">PDF Extraction Pro</h3>
            </div>
            <p className="text-gray-300 text-lg leading-relaxed">
              Transform your documents with AI‑powered extraction technology.
            </p>
            <div className="flex space-x-4 mt-6">
              {['twitter', 'linkedin', 'github'].map(net => (
                <a key={net} href="#" className="w-10 h-10 bg-blue-600 hover:bg-blue-700 rounded-lg flex items-center justify-center transition-colors">
                  <i className={`fab fa-${net}`}></i>
                </a>
              ))}
            </div>
          </div>

          <div>
            <h3 className="text-lg font-semibold mb-4">Quick Links</h3>
            <ul className="space-y-3">
              {[
                ['Home', 'fa-home'],
                ['Documentation', 'fa-book'],
                ['API Reference', 'fa-code'],
                ['Contact Us', 'fa-envelope'],
              ].map(([label, icon]) => (
                <li key={label}>
                  <a href="#" className="text-gray-300 hover:text-white transition-colors flex items-center space-x-2">
                    <i className={`fas ${icon} text-sm`}></i>
                    <span>{label}</span>
                  </a>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h3 className="text-lg font-semibold mb-4">Support</h3>
            <div className="space-y-3 text-gray-300">
              <p>Need help? We're here for you.</p>
              <a href="mailto:support@vidavox.ai" className="text-blue-400 hover:text-blue-300 transition-colors flex items-center space-x-2">
                <i className="fas fa-envelope"></i>
                <span>support@vidavox.ai</span>
              </a>
              <div className="flex items-center space-x-2">
                <i className="fas fa-clock"></i>
                <span>24/7 Support</span>
              </div>
            </div>
          </div>
        </div>
        <div className="border-t border-gray-800 mt-8 pt-8 text-center">
          <p className="text-gray-400">© 2024 Vidavox Doc AI. All rights reserved.</p>
        </div>
      </div>
    </footer>
  );
}
