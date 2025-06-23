// =========================================================
// File: src/components/UploadPanel.jsx
// =========================================================
import React, { useRef } from 'react';

export default function UploadPanel({ file, onUpload, options, setOptions, onExtract, progress, step }) {
  const inputRef = useRef();

  const handleFileChange = e => {
    if (e.target.files.length) {
      onUpload(e.target.files[0]);
    }
  };

  const handleDrop = e => {
    e.preventDefault();
    if (e.dataTransfer.files.length) {
      onUpload(e.dataTransfer.files[0]);
    }
  };

  const stopDefault = e => e.preventDefault();

  return (
    <div className="glass-effect rounded-2xl shadow-xl overflow-hidden">
      <div className="bg-gradient-to-r from-blue-600 to-purple-600 p-6 text-white">
        <h2 className="text-xl font-bold flex items-center">
          <i className="fas fa-cloud-upload-alt mr-3 text-2xl"></i>
          Upload & Configure
        </h2>
        <p className="text-blue-100 text-sm mt-1">Start by selecting your PDF file</p>
      </div>

      <div className="p-6 space-y-6">
        {/* Upload Zone */}
        <label
          onDragOver={stopDefault}
          onDragEnter={stopDefault}
          onDrop={handleDrop}
          className="flex flex-col items-center justify-center w-full h-64 border-3 border-dashed border-blue-300 rounded-xl cursor-pointer bg-gradient-to-br from-blue-50 to-purple-50 hover:from-blue-100 hover:to-purple-100 transition-all duration-300"
        >
          {!file ? (
            <>
              <div className="flex flex-col items-center justify-center py-8">
                <div className="mb-4 p-4 bg-white rounded-full shadow-lg">
                  <i className="fas fa-cloud-upload-alt text-4xl text-blue-500"></i>
                </div>
                <p className="mb-2 text-lg font-semibold text-gray-700">Drop your PDF here</p>
                <p className="text-sm text-gray-500 text-center">
                  or <span className="text-blue-600 font-medium">browse files</span>
                  <br /> Max size: 20MB
                </p>
              </div>
              <input ref={inputRef} type="file" className="hidden" accept=".pdf" onChange={handleFileChange} />
            </>
          ) : (
            <p className="text-lg font-semibold text-blue-600 flex items-center space-x-2">
              <i className="fas fa-file-pdf"></i>
              <span>{file.name}</span>
            </p>
          )}
        </label>

        {/* Extraction Options */}
        {file && (
          <div className="space-y-6">
            {[
              ['text', 'Extract Text', 'fa-font', 'blue'],
              ['tables', 'Extract Tables', 'fa-table', 'green'],
              ['images', 'Extract Images', 'fa-images', 'purple'],
            ].map(([key, label, icon, color]) => (
              <div
                key={key}
                className="flex items-center justify-between p-3 bg-white rounded-lg shadow-sm"
              >
                <div className="flex items-center space-x-3">
                  <i className={`fas ${icon} text-${color}-500`}></i>
                  <span className="font-medium">{label}</span>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={options[key]}
                    onChange={e => setOptions({ ...options, [key]: e.target.checked })}
                    className="sr-only"
                  />
                  <div className="w-11 h-6 bg-gray-200 rounded-full peer peer-checked:bg-blue-600 after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:after:translate-x-full"></div>
                </label>
              </div>
            ))}

            <div className="bg-gray-50 p-4 rounded-xl">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                <i className="fas fa-file-alt mr-2"></i>Page Range (Optional)
              </label>
              <input
                type="text"
                value={options.pageRange}
                onChange={e => setOptions({ ...options, pageRange: e.target.value })}
                placeholder="e.g., 1-5, 7, 9-10"
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
              />
              <p className="text-xs text-gray-500 mt-2">Leave empty to extract all pages</p>
            </div>

            <button
              type="button"
              onClick={onExtract}
              className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white font-bold py-4 px-6 rounded-xl transition-all duration-300 transform hover:scale-105 shadow-lg hover:shadow-xl flex items-center justify-center space-x-2"
            >
              <i className="fas fa-magic text-xl"></i>
              <span className="text-lg">Start Extraction</span>
            </button>
          </div>
        )}

        {/* Progress Display */}
        {progress.uploading && (
          <div className="text-center mb-6">
            {/* progress circle (simplified) */}
            <p className="text-2xl font-bold text-gray-700">{progress.percentage}%</p>
            <p className="text-lg font-medium text-gray-700">{progress.status}…</p>
          </div>
        )}
      </div>
    </div>
  );
}
