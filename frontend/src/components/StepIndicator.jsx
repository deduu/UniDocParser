// =========================================================
// File: src/components/StepIndicator.jsx
// =========================================================
import React from 'react';

export default function StepIndicator({ current }) {
  const steps = ['Upload PDF', 'Configure', 'Extract', 'Review'];
  return (
    <div className="container mx-auto px-4 py-6">
      <div className="flex justify-center items-center space-x-8 mb-8">
        {steps.map((label, idx) => {
          const num = idx + 1;
          const active = num === current;
          const done = num < current;
          const base = done ? 'bg-blue-600 text-white' : active ? 'bg-blue-600 text-white' : 'bg-gray-300 text-gray-600';
          return (
            <div key={label} className="flex items-center space-x-3 step-indicator">
              <div className={`w-10 h-10 rounded-full flex items-center justify-center font-semibold ${base}`}>
                {num}
              </div>
              <span className={`text-sm font-medium ${done || active ? 'text-gray-700' : 'text-gray-500'}`}>{label}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}