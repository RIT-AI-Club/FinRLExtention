import React, { useState } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url,
).toString();

const API_BASE = 'http://localhost:8000';

function PdfPreviewOverlay({ filepath, onClose }) {
  const [numPages, setNumPages] = useState(null);
  const [zoom, setZoom] = useState(1);

  return (
    <div className="pdf-modal-overlay" onClick={onClose}>
      <div className="pdf-modal" onClick={e => e.stopPropagation()}>

      <div className="pdf-modal-header">
        <span>{filepath}</span>
        <div className="pdf-modal-controls">
          <button onClick={() => setZoom(z => Math.max(0.5, z - 0.25))}>−</button>
          <span>{Math.round(zoom * 100)}%</span>
          <button onClick={() => setZoom(z => Math.min(3, z + 0.25))}>+</button>
        </div>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <a
            href={`${API_BASE}/api/report/download/${encodeURIComponent(filepath)}`}
            download={filepath}
            className="download-button"
          >
            ↓
          </a>
          <button className="pdf-modal-close" onClick={onClose}>✕</button>
        </div>
      </div>



        <div className="pdf-modal-body">
          <Document
            file={`${API_BASE}/api/report/download/${encodeURIComponent(filepath)}`}
            onLoadSuccess={({ numPages }) => setNumPages(numPages)}
            loading={<p style={{ color: '#ccc', padding: '20px' }}>Loading...</p>}
            error={<p style={{ color: '#f88', padding: '20px' }}>Failed to load PDF.</p>}
          >
            {Array.from({ length: numPages || 0 }, (_, i) => (
              <Page
                key={i + 1}
                pageNumber={i + 1}
                width={600 * zoom}
                renderTextLayer={true}
                renderAnnotationLayer={true}
              />
            ))}
          </Document>
        </div>

      </div>
    </div>
  );
}

export default PdfPreviewOverlay;
