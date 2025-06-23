// =========================================================
// File: src/components/FloatingHelpButton.jsx
// =========================================================
import React from 'react';

export default function FloatingHelpButton({ onClick }) {
  return (
    <div className="fixed bottom-8 right-8 z-50">
      <button
        onClick={onClick}
        className="w-14 h-14 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white rounded-full shadow-2xl transition-all duration-300 transform hover:scale-110 flex items-center justify-center animate-pulse"
      >
        <i className="fas fa-question text-xl"></i>
      </button>
    </div>
  );
}