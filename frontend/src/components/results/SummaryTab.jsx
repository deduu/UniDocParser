
// =========================================================
// File: src/components/results/SummaryTab.jsx
// =========================================================
import React from 'react';

export default function SummaryTab({ file, summary }) {
  if (!summary) return <p>No summary yet.</p>;
  return (
    <div className="space-y-8">
      {/* File Info Card */}
      <div className="bg-white rounded-2xl shadow-lg p-4 flex items-center space-x-4">
        <div className="flex-shrink-0">
          <i className="fas fa-file-pdf text-4xl text-red-500"></i>
        </div>
        <div className="flex-grow">
          <h3 className="text-xl font-bold text-gray-800">{file.name}</h3>
          <p className="text-sm text-gray-600">
            {summary.pages} pages • {summary.size}
          </p>
          <div className="mt-2 text-sm font-semibold px-3 py-1 rounded-full inline-flex items-center space-x-2 bg-green-100 text-green-700">
            <i className="fas fa-check-circle"></i>
            <span>Completed</span>
          </div>
        </div>
      </div>

      {/* Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        {[
          ['PAGES', summary.pages, 'fa-file-alt', 'blue'],
          ['TEXT', summary.textBlocks, 'fa-paragraph', 'green'],
          ['TABLES', summary.tables, 'fa-table', 'purple'],
          ['TIME', summary.time, 'fa-clock', 'yellow'],
        ].map(([label, val, icon, color]) => (
          <div key={label} className="bg-white p-6 rounded-2xl shadow-lg border border-gray-100 feature-card">
            <div className="flex items-center justify-between mb-3">
              <div className={`p-3 bg-${color}-100 rounded-xl`}>
                <i className={`fas ${icon} text-${color}-600 text-xl`}></i>
              </div>
              <span className="text-xs text-gray-500 font-medium">{label}</span>
            </div>
            <div className="text-3xl font-bold text-gray-800">{val}</div>
          </div>
        ))}
      </div>

      {/* Download buttons (dummy) */}
      <div className="bg-white p-6 rounded-2xl shadow-lg border border-gray-100">
        <h4 className="text-lg font-semibold text-gray-800 mb-4 flex items-center">
          <i className="fas fa-download mr-3 text-blue-600"></i>
          Download Results
        </h4>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <a
            href="#"
            className="flex items-center justify-center space-x-3 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white font-semibold py-4 px-6 rounded-xl transition-all duration-300 transform hover:scale-105 shadow-lg hover:shadow-xl"
          >
            <i className="fas fa-code text-xl"></i>
            <span>JSON Format</span>
          </a>
          <a
            href="#"
            className="flex items-center justify-center space-x-3 bg-gradient-to-r from-green-600 to-green-700 hover:from-green-700 hover:to-green-800 text-white font-semibold py-4 px-6 rounded-xl transition-all duration-300 transform hover:scale-105 shadow-lg hover:shadow-xl"
          >
            <i className="fas fa-file-alt text-xl"></i>
            <span>Markdown</span>
          </a>
        </div>
      </div>
    </div>
  );
}