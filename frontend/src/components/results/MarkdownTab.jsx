
// =========================================================
// File: src/components/results/MarkdownTab.jsx
// =========================================================
import React from 'react';
import hljs from 'highlight.js/lib/common';

export default function MarkdownTab({ markdown }) {
  const copy = () => navigator.clipboard.writeText(markdown || '');
  return (
    <div className="bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden p-6 space-y-4">
      <button
        onClick={copy}
        className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg inline-flex items-center space-x-2 font-medium"
      >
        <i className="far fa-copy"></i>
        <span>Copy</span>
      </button>
      <pre>
        <code
          dangerouslySetInnerHTML={{ __html: hljs.highlight(markdown || '', { language: 'markdown' }).value }}
          className="language-markdown text-sm"
        />
      </pre>
    </div>
  );
}