
// =========================================================
// File: src/components/results/JsonTab.jsx
// =========================================================
import React, { useRef, useEffect } from 'react';
import JSONEditor from 'jsoneditor';
import 'jsoneditor/dist/jsoneditor.css';

export default function JsonTab({ json }) {
  const container = useRef();
  useEffect(() => {
    if (!container.current) return;
    const editor = new JSONEditor(container.current, {
      mode: 'view',
      mainMenuBar: false,
    });
    editor.update(json || {});
    return () => editor.destroy();
  }, [json]);

  return <div ref={container} style={{ height: '600px' }} />;
}
