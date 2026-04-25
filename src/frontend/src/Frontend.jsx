import React, { useState, useEffect, useRef } from 'react';
import './App.css';

const API_BASE = 'http://localhost:8000';
const SUGGESTIONS = ['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'TSLA'];

function Spinner({ ticker }) {
  return (
    <div className="spinner-container">
      <div className="spinner" />
      <p className="spinner-label">
        Generating report for <strong>{ticker}</strong>…
      </p>
      <p className="spinner-sublabel">This may take a minute</p>
    </div>
  );
}

function Frontend() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isReportsCollapsed, setIsReportsCollapsed] = useState(false);
  const [inputValue, setInputValue] = useState('');
  const [pastReports, setPastReports] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [loadingTicker, setLoadingTicker] = useState('');
  const [currentPdfUrl, setCurrentPdfUrl] = useState(null);
  const [currentPdfTitle, setCurrentPdfTitle] = useState('');
  const [errorMsg, setErrorMsg] = useState(null);
  const inputRef = useRef(null);

  useEffect(() => { fetchReports(); }, []);

  async function fetchReports() {
    try {
      const res = await fetch(`${API_BASE}/api/reports`);
      if (!res.ok) return;
      const data = await res.json();
      setPastReports(
        (data.reports || []).map((filename, i) => ({
          id: `server-${i}`,
          ticker: filename.replace(/\.html$/i, '').split('_')[0],
          date: '',
          status: 'Ready',
          filename,
        }))
      );
    } catch (e) {
      console.error('Could not load reports:', e);
    }
  }

  const handleGenerate = async () => {
    const ticker = inputValue.trim().toUpperCase();
    if (!/^[A-Z]{1,5}$/.test(ticker)) {
      setErrorMsg('Please enter a valid ticker symbol (e.g. AAPL).');
      return;
    }
    setIsLoading(true);
    setLoadingTicker(ticker);
    setErrorMsg(null);
    setInputValue('');

    try {
      const res = await fetch(`${API_BASE}/api/report/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticker }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Server error');
      }
      const data = await res.json();
      if (data.pdf_filename) {
        setCurrentPdfUrl(`${API_BASE}/api/report/view/${encodeURIComponent(data.pdf_filename)}`);
        setCurrentPdfTitle(ticker);
      }
      setPastReports(prev => [{
        id: Date.now(),
        ticker,
        date: new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric' }),
        status: 'Ready',
        filename: data.html_filename,
        pdf_filename: data.pdf_filename,
      }, ...prev]);
    } catch (e) {
      setErrorMsg(e.message);
    } finally {
      setIsLoading(false);
      setLoadingTicker('');
    }
  };

  const openReport = (report) => {
    const pdfFn = report.pdf_filename || (report.filename && report.filename.replace(/\.html$/i, '.pdf'));
    if (pdfFn) {
      setCurrentPdfUrl(`${API_BASE}/api/report/view/${encodeURIComponent(pdfFn)}`);
      setCurrentPdfTitle(report.ticker);
    }
  };

  return (
    <div className="app-wrapper">
      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
      `}</style>

      {/* Sidebar */}
      <div className={`sidebar ${isSidebarOpen ? 'open' : 'collapsed'}`}>
        <div className="sidebar-toggle-area" style={{ display: 'flex', flexDirection: 'column', gap: '16px', padding: '16px' }}>
          <button
            className="hamburger-btn"
            onClick={() => setIsSidebarOpen(v => !v)}
            style={{ background: 'none', border: 'none', fontSize: '24px', cursor: 'pointer', color: 'var(--color-text-primary)' }}
          >
            ☰
          </button>
        </div>

        {isSidebarOpen && (
          <div className="sidebar-inner-content">
            <div
              className="sidebar-section-label sidebar-section-label-collapsible"
              style={{ paddingTop: '32px' }}
              onClick={() => setIsReportsCollapsed(v => !v)}
            >
              <span>Past Reports</span>
              <span className="section-collapse-arrow">{isReportsCollapsed ? '▶' : '▼'}</span>
            </div>

            {!isReportsCollapsed && (
              <div className="sidebar-content">
                {pastReports.length === 0 && (
                  <p style={{ fontSize: 13, color: '#666', padding: '4px 8px' }}>No reports yet.</p>
                )}
                {pastReports.map(report => (
                  <div
                    key={report.id}
                    className="report-item"
                    onClick={() => openReport(report)}
                    style={{ cursor: 'pointer' }}
                  >
                    <span className="report-item-icon">📄</span>
                    <span className="report-item-name">
                      <span>{report.ticker}{report.date ? ` · ${report.date}` : ''}</span>
                      <span className="report-item-status">{report.status}</span>
                    </span>
                    {report.filename && (
                      <a
                        className="report-download-btn"
                        href={`${API_BASE}/api/report/download/${encodeURIComponent(report.filename.replace(/\.html$/i, '.pdf'))}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        title="Download PDF"
                        onClick={e => e.stopPropagation()}
                      >
                        ↓
                      </a>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Main Area */}
      <div className={`main-chat-area${currentPdfUrl ? ' chat-area-narrow' : ''}`}>
        <div className="chat-header">
          <img src='/logo_rit_AI_transparent_white.png' style={{ height: '50px', width: 'auto' }} />
          <h1>FinRL Assistant</h1>
        </div>

        {isLoading ? (
          <Spinner ticker={loadingTicker} />
        ) : (
          <div className="ticker-form">
            <p className="ticker-form-label">Enter a stock ticker to generate a report</p>

            <div className="ticker-input-row">
              <input
                ref={inputRef}
                type="text"
                className="ticker-input"
                placeholder="e.g. AAPL"
                value={inputValue}
                onChange={e => { setInputValue(e.target.value.toUpperCase()); setErrorMsg(null); }}
                onKeyDown={e => { if (e.key === 'Enter') handleGenerate(); }}
                maxLength={5}
                autoFocus
              />
              <button
                className="send-btn"
                onClick={handleGenerate}
                disabled={!inputValue.trim()}
              >
                Generate
              </button>
            </div>

            {errorMsg && <p className="ticker-error">{errorMsg}</p>}

            <div className="ticker-suggestions">
              <span style={{ fontSize: 12, color: '#888' }}>Suggested:</span>
              {SUGGESTIONS.map(t => (
                <button
                  key={t}
                  className="suggested-ticker"
                  onClick={() => { setInputValue(t); setErrorMsg(null); inputRef.current?.focus(); }}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* PDF Viewer Panel */}
      {currentPdfUrl && (
        <div className="pdf-viewer-panel">
          <div className="pdf-viewer-header">
            <span className="pdf-viewer-title">{currentPdfTitle} Report</span>
            <div className="pdf-viewer-actions">
              <a
                href={currentPdfUrl}
                download={`${currentPdfTitle}_report.pdf`}
                className="pdf-download-link"
              >
                Download PDF
              </a>
              <button className="pdf-viewer-close" onClick={() => setCurrentPdfUrl(null)}>✕</button>
            </div>
          </div>
          <iframe
            src={currentPdfUrl}
            className="pdf-viewer-frame"
            title={`${currentPdfTitle} Report`}
          />
        </div>
      )}
    </div>
  );
}

export default Frontend;
