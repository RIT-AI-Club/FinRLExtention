import React, { useState, useEffect } from 'react';

const API_BASE = 'http://localhost:8000';

function PdfPreviewOverlay({ filepath, onClose }) {
  const [blobUrl, setBlobUrl] = useState(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/report/download/${encodeURIComponent(filepath)}`)
      .then(res => res.blob())
      .then(blob => {
        const url = URL.createObjectURL(blob);
        setBlobUrl(url);
      });
    return () => { if (blobUrl) URL.revokeObjectURL(blobUrl); };
  }, [filepath]);

  return (
    <div className="pdf-modal-overlay" onClick={onClose}>
      <div className="pdf-modal" onClick={e => e.stopPropagation()}>
        <div className="pdf-modal-header">
          <span>{filepath}</span>
          <button className="pdf-modal-close" onClick={onClose}>✕</button>
        </div>
        {blobUrl
          ? <iframe src={blobUrl} className="pdf-modal-iframe" title="PDF Preview" />
          : <p style={{ color: '#ccc', padding: '20px' }}>Loading...</p>
        }
      </div>
    </div>
  );
}

export default PdfPreviewOverlay;
