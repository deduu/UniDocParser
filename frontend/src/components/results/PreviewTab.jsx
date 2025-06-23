// =========================================================
// File: src/components/results/PreviewTab.jsx
// =========================================================
import React from 'react';
import marked from 'marked';
import DOMPurify from 'dompurify';

export default function PreviewTab({ markdown }) {
  return (
    <div
      className="markdown-content prose prose-lg max-w-none bg-white rounded-2xl shadow-lg border border-gray-100 p-8"
      dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(marked.parse(markdown || '')) }}
    />
  );
}
