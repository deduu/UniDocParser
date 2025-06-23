
// =========================================================
// File: src/components/results/ComparisonTab.jsx
// =========================================================
import React, { useState, useRef, useEffect } from 'react';
import pdfjsLib from 'pdfjs-dist';
import marked from 'marked';
import DOMPurify from 'dompurify';

export default function ComparisonTab({ pages }) {
  const [pageIdx, setPageIdx] = useState(0);
  const canvasRef = useRef();

  // Render PDF page (dummy because backend not integrated)
  useEffect(() => {
    if (!pages.length) return;
    // TODO: implement real PDF rendering with pdfjs
  }, [pageIdx, pages]);

  if (!pages.length) return <p className="text-gray-500 italic">No pages yet.</p>;

  const page = pages[pageIdx];
  return (
    <>
      {/* Pager controls */}
      <div className="bg-white p-4 rounded-xl shadow-md mb-6 border border-gray-100 flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <button
            onClick={() => setPageIdx(i => Math.max(i - 1, 0))}
            className="px-4 py-2 bg-gray-100 rounded-lg flex items-center space-x-2 font-medium"
            disabled={pageIdx === 0}
          >
            <i className="fas fa-chevron-left"></i>
            <span>Previous</span>
          </button>
          <span className="px-4 py-2 bg-blue-50 text-blue-800 rounded-lg font-medium">
            Page {pageIdx + 1} of {pages.length}
          </span>
          <button
            onClick={() => setPageIdx(i => Math.min(i + 1, pages.length - 1))}
            className="px-4 py-2 bg-gray-100 rounded-lg flex items-center space-x-2 font-medium"
            disabled={pageIdx === pages.length - 1}
          >
            <span>Next</span>
            <i className="fas fa-chevron-right"></i>
          </button>
        </div>
      </div>

      {/* Two‑column comparison */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="bg-white p-6 rounded-2xl shadow-lg border border-gray-100">
          <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center">
            <i className="fas fa-file-pdf text-red-500 mr-3"></i>
            Original PDF Page
          </h3>
          <canvas ref={canvasRef} className="w-full rounded-lg shadow"></canvas>
        </div>

        <div className="bg-white p-6 rounded-2xl shadow-lg border border-gray-100">
          <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center">
            <i className="fas fa-file-alt text-green-500 mr-3"></i>
            Extracted Content
          </h3>
          <div
            className="markdown-content prose max-w-none"
            dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(marked.parse(page.text || '')) }}
          />
        </div>
      </div>
    </>
  );
}
