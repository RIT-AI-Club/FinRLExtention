import React, { useState, useEffect, useRef } from 'react';
import './App.css';

// ── constants ────────────────────────────────────────────────────────────────
const API_BASE = 'http://localhost:8000';

// Stocks shown as quick-pick chips; updated when tickers appear in conversation
const DEFAULT_SUGGESTIONS = ['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'TSLA'];
const KNOWN_TICKERS = ['AAPL','MSFT','GOOGL','NVDA','TSLA','AMZN','META','SPY','AMD','NFLX'];

function extractTickers(text) {
  const hits = (text.toUpperCase().match(/\b[A-Z]{1,5}\b/g) || []);
  return [...new Set(hits.filter(t => KNOWN_TICKERS.includes(t)))];
}

// ── tiny loading dots shown while generation is in progress ──────────────────
function LoadingDots() {
  return (
    <div style={{ display: 'flex', gap: 5, padding: '8px 4px', alignItems: 'center' }}>
      {[0, 1, 2].map(i => (
        <div key={i} style={{
          width: 7, height: 7, borderRadius: '50%',
          background: 'var(--color-text-secondary)',
          animation: `dot-pulse 1.2s ease-in-out ${i * 0.4}s infinite`,
        }} />
      ))}
    </div>
  );
}

function Frontend() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [inputValue, setInputValue] = useState('');
  const [pastReports, setPastReports] = useState([
    {id: 1, ticker: 'APPL', date: 'April 3', status: 'Pending'}
  ]);
  const [isDataLoading, setIsDataLoading] = useState(false);
  const [messages, setMessages] = useState([]);
  // FIX: was `const [newChat, setNewChat] = [{}]` — not valid React state syntax
  const [newChat, setNewChat] = useState([]);

  // ── additions ──────────────────────────────────────────────────────────────
  const [suggestedStocks, setSuggestedStocks] = useState(DEFAULT_SUGGESTIONS);
  const [errorMsg, setErrorMsg] = useState(null);
  const chatEndRef = useRef(null);

  // Fetch the list of past report PDFs from the server on mount
  useEffect(() => {
    fetchReports();
  }, []);

  // Auto-scroll to bottom whenever messages or loading state changes
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isDataLoading]);

  // Pull real PDF filenames from the server and merge into pastReports
  async function fetchReports() {
    try {
      const res = await fetch(`${API_BASE}/api/reports`);
      if (!res.ok) return;
      const data = await res.json();
      const serverReports = (data.reports || []).map((filename, i) => ({
        id: `server-${i}`,
        ticker: filename.replace(/\.pdf$/i, '').replace(/[_-]/g, ' '),
        date: '',
        status: 'Ready',
        filename,
      }));
      // Merge server reports in front, keeping any local placeholders
      setPastReports(prev => {
        const localOnly = prev.filter(r => !r.filename);
        return [...serverReports, ...localOnly];
      });
    } catch (e) {
      console.error('Could not load reports:', e);
    }
  }

  const handleSend = async () => {
    if (inputValue.trim() !== '' && !isDataLoading) {
      // Add the user's message to the chat
      setMessages((prevMessages) => [...prevMessages, { id: Date.now(), text: inputValue, sender: 'user' }]);

      // Build conversation history for the backend (all turns BEFORE this one)
      const history = messages.map(m => ({
        role: m.sender === 'user' ? 'user' : 'ai',
        content: m.text,
      }));

      const userText = inputValue;
      setInputValue('');
      setIsDataLoading(true);   // show the loading icon
      setErrorMsg(null);

      try {
        // Send request to the server
        const res = await fetch(`${API_BASE}/api/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: userText, history }),
        });

        if (!res.ok) {
          const err = await res.json();
          throw new Error(err.detail || 'Server error');
        }

        const data = await res.json();

        // Add the assistant reply bubble
        setMessages(prev => [...prev, { id: Date.now() + 1, text: data.reply, sender: 'assistant' }]);

        // If a new PDF was generated, prepend it to the sidebar
        if (data.pdf_filename) {
          const newReport = {
            id: Date.now() + 2,
            ticker: data.pdf_filename.replace(/\.pdf$/i, '').replace(/[_-]/g, ' '),
            date: new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric' }),
            status: 'Ready',
            filename: data.pdf_filename,
          };
          setPastReports(prev => [newReport, ...prev]);
        }

        // Update recommended stocks based on what appeared in this exchange
        const tickers = extractTickers(userText + ' ' + data.reply);
        if (tickers.length > 0) {
          setSuggestedStocks(prev => [...new Set([...tickers, ...prev])].slice(0, 6));
        }

      } catch (e) {
        setErrorMsg(e.message);
      } finally {
        setIsDataLoading(false);  // hide the loading icon
      }
    }
  }

  const toggleSidebar = () => {
    setIsSidebarOpen(!isSidebarOpen);
  };

  return (
    <div className="app-wrapper">

      <style>{`
        @keyframes dot-pulse {
          0%, 100% { opacity: 0.25; transform: scale(0.8); }
          50%       { opacity: 1;    transform: scale(1);   }
        }
      `}</style>
      
      {/* 1. The Sidebar */}
      <div className={`sidebar ${isSidebarOpen ? 'open' : 'closed'}`}>
        <div className="sidebar-header">
          <h2>History</h2>
          <button onClick={toggleSidebar}>✕</button>
        </div>
        <div className="sidebar-content">
          {/* Loop through the pastReports array */}
          {pastReports.map((report) => (
            <div key={report.id} className="report-item">
              <p><strong>{report.ticker}</strong>{report.date ? ` - ${report.date}` : ''}</p>
              <small>{report.status}</small>
              {/* If the report has a real PDF on the server, show a download link */}
              {report.filename && (
                <div>
                  <a
                    href={`${API_BASE}/api/report/download/${encodeURIComponent(report.filename)}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ fontSize: 12, color: '#185FA5' }}
                  >
                    ↓ Download PDF
                  </a>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* 2. The Main Chat Area */}
      <div className="main-chat-area">
        
        {/* Header with Hamburger and Title */}
        <div className="chat-header">
          <button className="hamburger-btn" onClick={toggleSidebar}>
            ☰
          </button>
          <h1>FinRL Assistant</h1>
          <div className="spacer"></div> {/* This empty div perfectly centers the title! */}
        </div>
        
        {/* The Big Chat Window */}
        <div className="chat-window" style={{overflowY: 'auto'}}>
          {messages.map((message) => (
            // FIX: was `{'chat-message ${message.sender}'}` (single quotes) — template literals need backticks
            <div key={message.id} className={`chat-message ${message.sender}`}>
              <p>{message.text}</p>
            </div>
          ))}

          {/* Show a loading icon that shows the user that the generation is taking place */}
          {isDataLoading && (
            <div className="chat-message assistant">
              <LoadingDots />
            </div>
          )}

          {/* Error banner if the server returns a failure */}
          {errorMsg && (
            <div style={{
              margin: '8px auto', padding: '8px 14px', borderRadius: 8,
              background: 'var(--color-background-danger)',
              color: 'var(--color-text-danger)',
              border: '0.5px solid var(--color-border-danger)',
              fontSize: 13, maxWidth: '80%', textAlign: 'center',
            }}>
              {errorMsg}
            </div>
          )}

          {/* Invisible anchor so auto-scroll always lands at the bottom */}
          <div ref={chatEndRef} />
        </div>

        {/* Shows recommended stocks based on past requests */}
        <div style={{ padding: '6px 16px 2px', display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
          <span style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>Suggested:</span>
          {suggestedStocks.map(ticker => (
            <button
              key={ticker}
              onClick={() => setInputValue(`Generate a report on ${ticker}`)}
              style={{
                padding: '4px 12px', borderRadius: 99, fontSize: 12, fontWeight: 500, cursor: 'pointer',
                background: 'transparent',
                border: '0.5px solid var(--color-border-secondary)',
                color: 'var(--color-text-primary)',
              }}
            >
              {ticker}
            </button>
          ))}
        </div>

        {/* The Input Field and Button */}
        <div className="input-container">
          <input 
            type="text" 
            placeholder="Type Your Message Here..." 
            className="chat-input"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={(e) => {
              if (e.key === 'Enter') {
                handleSend();
              }}}
            disabled={isDataLoading}
          />
          <button className="send-btn" onClick={handleSend} disabled={isDataLoading || !inputValue.trim()}>
            {isDataLoading ? '...' : 'Send'}
          </button>
        </div>
      </div>

    </div>
  );
}

export default Frontend;