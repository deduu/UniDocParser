// =========================================================
// File: src/components/HelpPanel.jsx
// =========================================================
import React from 'react';

export default function HelpPanel({ show }) {
  if (!show) return null;
  return (
    <div className="glass-effect rounded-2xl shadow-xl overflow-hidden">
      <div className="bg-gradient-to-r from-indigo-600 to-purple-600 p-6 text-white">
        <h2 className="text-2xl font-bold flex items-center">
          <i className="fas fa-question-circle mr-3"></i>
          How to Use PDF Extraction Pro
        </h2>
        <p className="text-indigo-100 mt-2">Follow these simple steps to extract content from your PDFs</p>
      </div>
      <div className="p-8 space-y-6">
        {[
          [1, 'Upload Your PDF', 'Drag and drop your PDF or click to browse. Files up to 20MB are supported.'],
          [2, 'Configure Extraction Settings', 'Choose what content to extract and optionally set page ranges.'],
          [3, 'Review & Compare', 'Validate accuracy by viewing the original PDF alongside extracted content.'],
          [4, 'Download Results', 'Export in JSON or Markdown format for use in your apps or docs.'],
        ].map(([num, title, desc], idx) => (
          <div
            key={idx}
            className={`flex items-start space-x-4 p-4 rounded-xl border ${
              ['blue', 'green', 'purple', 'yellow'][idx]
            }-50 bg-${['blue', 'green', 'purple', 'yellow'][idx]}-50`}
          >
            <div className={`flex-shrink-0 w-12 h-12 rounded-full bg-gradient-to-r from-${
              ['blue', 'green', 'purple', 'yellow'][idx]
            }-600 to-${['purple', 'teal', 'pink', 'orange'][idx]}-600 text-white flex items-center justify-center font-bold text-lg`}> 
              {num}
            </div>
            <div>
              <h3 className="font-semibold text-gray-800 text-lg">{title}</h3>
              <p className="text-gray-600 mt-1">{desc}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
