// =========================================================
// File: src/components/results/ResultsPanel.jsx
// =========================================================
import React, { useState } from 'react';
import SummaryTab from './SummaryTab.jsx';
import ComparisonTab from './ComparisonTab.jsx';
import JsonTab from './JsonTab.jsx';
import MarkdownTab from './MarkdownTab.jsx';
import PreviewTab from './PreviewTab.jsx';

export default function ResultsPanel({ step, file, results, progress }) {
  const [tab, setTab] = useState('summary');

  if (step < 4) return null; // hide until extraction complete

  const tabs = [
    ['summary', 'Summary', 'fa-chart-pie'],
    ['comparison', 'Compare', 'fa-columns'],
    ['json', 'JSON', 'fa-code'],
    ['markdown', 'Markdown', 'fa-file-alt'],
    ['preview', 'Preview', 'fa-eye'],
  ];

  return (
    <div className="glass-effect rounded-2xl shadow-xl overflow-hidden">
      <div className="bg-white border-b border-gray-200 flex flex-wrap" aria-label="Tabs">
        {tabs.map(([key, label, icon]) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`tab-button flex-1 py-4 px-6 font-semibold text-center transition-all ${
              tab === key ? 'text-blue-600 bg-blue-50' : 'text-gray-600 hover:text-blue-600 hover:bg-gray-50'
            }`}
          >
            <i className={`fas ${icon} mr-2`}></i>
            <span className="hidden sm:inline">{label}</span>
          </button>
        ))}
      </div>

      <div className="p-8">
        {tab === 'summary' && <SummaryTab file={file} summary={results.summary} />}
        {tab === 'comparison' && <ComparisonTab pages={results.pages} />}
        {tab === 'json' && <JsonTab json={results.json} />}
        {tab === 'markdown' && <MarkdownTab markdown={results.markdown} />}
        {tab === 'preview' && <PreviewTab markdown={results.markdown} />}
      </div>
    </div>
  );
}
