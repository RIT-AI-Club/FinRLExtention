/* 
This is the main file for the User interface
- Create a chatbox/user_input for a user to type their request in
- Prompt the user to type something like "I want you to generate a report on this stock"
- Create a send button that the user presses/clicks to confirm and send the request to the client
- Show a loading icon that shows the user that the generation is taking place
- Have a sidebar that stores and displays the past report PDFs that the user made
- Display the title in big letter above the chatbox/user_input 
- Shows recommended stocks based on past requests
- Create a toggle button that pulls up the side bar
- Create a way for the UI to access data collected or generated from servers to produce output
- Preview option for PDF generation
 */

// FIX: Removed unused `act` import from your HEAD version; kept collaborator's useEffect + useRef
import React, { useState, useEffect, useRef, useCallback } from 'react';
import './App.css';
import PdfPreviewOverlay from './PdfPreviewOverlay';

// ── constants ────────────────────────────────────────────────────────────────
const API_BASE = 'http://localhost:8000';

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
  const [isChatsCollapsed, setIsChatsCollapsed] = useState(false);
  const [isReportsCollapsed, setIsReportsCollapsed] = useState(false);
  const [inputValue, setInputValue] = useState('');
  const [pastReports, setPastReports] = useState([]);
  const [isDataLoading, setIsDataLoading] = useState(false);
  //For pdf preview
  const [previewPdf, setPreviewPdf] = useState(null);
  // ── Conversation state ────────────────────────────────────────────────────
  const [conversations, setConversations] = useState([
    { id: 1, messages: [] } 
  ]);
  const [activeConvoID, setActiveConvoID] = useState(1);

  // Derive the active conversation's messages
  // FIX: was misspelled as `activeMesssages` (triple-s) in HEAD version
  const activeMessages = conversations.find(c => c.id === activeConvoID)?.messages || [];

  // Start a new conversation and switch to it immediately
  const handleNewChat = useCallback(() => {
    const newConvo = { id: Date.now(), messages: [] };
    // FIX: was `pre => [...prev, newConvo]` — `pre` typo caused a ReferenceError
    setConversations(prev => [...prev, newConvo]);
    setActiveConvoID(newConvo.id);
    // Clear the input so the new chat starts fresh
    setInputValue('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
  }, []);

  // Switch to an existing conversation
  const handleSelectConvo = (id) => {
    setActiveConvoID(id);
  };

  // Delete a conversation; if it was active, fall back to the most recent remaining one
  const handleDeleteConvo = useCallback((e, id) => {
    // Stop the click from also triggering handleSelectConvo on the parent div
    e.stopPropagation();
    setConversations(prev => {
      const remaining = prev.filter(c => c.id !== id);
      // Always keep at least one conversation so the UI is never empty
      if (remaining.length === 0) {
        const fresh = { id: Date.now(), messages: [] };
        setActiveConvoID(fresh.id);
        return [fresh];
      }
      // If the deleted convo was active, activate the first remaining one
      setActiveConvoID(cur => cur === id ? remaining[0].id : cur);
      return remaining;
    });
  }, []);

  // ── Collaborator additions ────────────────────────────────────────────────
  const [suggestedStocks, setSuggestedStocks] = useState(DEFAULT_SUGGESTIONS);
  const [errorMsg, setErrorMsg] = useState(null);
  const chatEndRef = useRef(null);
  const textareaRef = useRef(null);

  const autoResize = (el) => {
    el.style.height = 'auto';
    el.style.height = el.scrollHeight + 'px';
  };

  // Fetch the list of past report PDFs from the server on mount
  useEffect(() => {
    fetchReports();
  }, []);

  // Auto-scroll to bottom whenever active messages or loading state changes
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [activeMessages, isDataLoading]);
  //Function to get the reports
  async function fetchReports() {
    try {
      const res = await fetch(`${API_BASE}/api/reports`);
      if (!res.ok) return;
      const data = await res.json();
      const serverReports = (data.reports || []).map((filename, i) => ({
        id: `server-${i}`,
        ticker: filename.replace(/\.pdf$/i, '').split('_')[0],
        date: '',
        status: 'Ready',
        filename,
      }));
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
      const userText = inputValue;

      // Add user message to the active conversation
      setConversations(prev =>
        prev.map(c =>
          c.id === activeConvoID
            ? { ...c, messages: [...c.messages, { id: Date.now(), text: userText, sender: 'user' }] }
            : c
        )
      );

      // Build conversation history for the backend (all turns before this one)
      const history = activeMessages.map(m => ({
        role: m.sender === 'user' ? 'user' : 'ai',
        content: m.text,
      }));

      setInputValue('');
      if (textareaRef.current) textareaRef.current.style.height = 'auto';
      setIsDataLoading(true);
      setErrorMsg(null);

      try {
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

        // Add assistant reply to the active conversation.
        // If the backend generated a PDF, attach the filename to the message so the
        // chat window can render a download button inline alongside the reply text.
        setConversations(prev =>
          prev.map(c =>
            c.id === activeConvoID
              ? {
                  ...c,
                  messages: [
                    ...c.messages,
                    {
                      id: Date.now() + 1,
                      text: data.reply,
                      sender: 'assistant',
                      pdf_filename: data.pdf_filename || null,  // ← attached here
                    },
                  ],
                }
              : c
          )
        );

        // If a new PDF was generated, prepend it to the sidebar
        if (data.pdf_filename) {
          const newReport = {
            id: Date.now() + 2,
            ticker: data.pdf_filename.replace(/\.pdf$/i, '').split('_')[0],
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
        setIsDataLoading(false);
      }
    }
  };

  const toggleSidebar = () => {
    setIsSidebarOpen(!isSidebarOpen);
  };

  // Get a display title for each conversation (first message, truncated)
  const getConvoTitle = (convo) => {
    if (convo.messages.length === 0) return 'New Conversation';
    return convo.messages[0].text.length > 28
      ? convo.messages[0].text.slice(0, 28) + '...'
      : convo.messages[0].text;
  };

  return (
    <div className="app-wrapper">

      <style>{`
        @keyframes dot-pulse {
          0%, 100% { opacity: 0.25; transform: scale(0.8); }
          50%       { opacity: 1;    transform: scale(1);   }
        }

        /* Show the delete button only when hovering the conversation row */
        .convo-item .convo-delete-btn {
          opacity: 0;
          transition: opacity 0.15s ease;
        }
        .convo-item:hover .convo-delete-btn {
          opacity: 1;
        }
      `}</style>

      {/* 1. The Sidebar */}
      <div className={`sidebar ${isSidebarOpen ? 'open' : 'collapsed'}`}>
        
        {/* Toggle Area - Always visible whether sidebar is open or closed */}
        <div className="sidebar-toggle-area" style={{ display: 'flex', flexDirection: 'column', gap: '16px', padding: '16px' }}>
          <button className="hamburger-btn" onClick={toggleSidebar} style={{ background: 'none', border: 'none', fontSize: '24px', cursor: 'pointer', textAlign: 'left', color: 'var(--color-text-primary)' }}>
            ☰
          </button>
          
          {/* Show a simple "New Chat" icon when closed, like Gemini */}
          {!isSidebarOpen && (
             <button onClick={handleNewChat} title="New Chat" style={{ background: 'none', border: 'none', fontSize: '20px', cursor: 'pointer', textAlign: 'center' }}>
               ✏️
             </button>
          )}
        </div>

        {/* Sidebar Content - Only visible when expanded */}
        {isSidebarOpen && (
          <div className="sidebar-inner-content">
            <div className="sidebar-header">
              <div className="sidebar-header-actions">
                <button className="new-chat-btn" onClick={handleNewChat} title="New Chat">
                  ✏️ New Chat
                </button>
                {/* Note: The '✕' close button was removed because the hamburger button handles toggling now */}
              </div>
            </div>

            {/* Conversation list */}
            <div className="sidebar-section-label sidebar-section-label-collapsible" style={{ paddingTop: "32px" }} onClick={() => setIsChatsCollapsed(v => !v)}>
              <span>Recent Chats</span>
              <span className="section-collapse-arrow">{isChatsCollapsed ? '▶' : '▼'}</span>
            </div>
            {!isChatsCollapsed && (
              <div className="sidebar-content">
                {conversations.map((convo) => (
                  <div
                    key={convo.id}
                    className={`convo-item ${convo.id === activeConvoID ? 'active-convo' : ''}`}
                    onClick={() => handleSelectConvo(convo.id)}
                  >
                    <span className="convo-icon">💬</span>
                    <span className="convo-title" style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {getConvoTitle(convo)}
                    </span>
                    {/* Delete button — only appears on hover via the CSS rule above */}
                    <button
                      className="convo-delete-btn"
                      onClick={(e) => handleDeleteConvo(e, convo.id)}
                      title="Delete conversation"
                    >
                      ✕
                    </button>
                  </div>
                ))}
              </div>
            )}

            {/* Past Reports */}
            <div className="sidebar-section-label sidebar-section-label-collapsible" onClick={() => setIsReportsCollapsed(v => !v)}>
              <span>Past Reports</span>
              <span className="section-collapse-arrow">{isReportsCollapsed ? '▶' : '▼'}</span>
            </div>
            {!isReportsCollapsed && (
              <div className="sidebar-content">
                {pastReports.map((report) => (
                  <div key={report.id} className="report-item" onClick={() => report.filename && setPreviewPdf(report.filename)} style={{ cursor: report.filename ? 'pointer' : 'default' }}>
                    <span className="report-item-icon">📄</span>
                    <span className="report-item-name">
                      <span>{report.ticker}{report.date ? ` · ${report.date}` : ''}</span>
                      <span className="report-item-status">{report.status}</span>
                    </span>
                    {report.filename && (
                      <a
                        className="report-download-btn"
                        href={`${API_BASE}/api/report/download/${encodeURIComponent(report.filename)}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        title="Download PDF"
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

      {/* 2. The Main Chat Area */}
      <div className="main-chat-area">

        {/* Header */}
        <div className="chat-header">
          {/*<button className="hamburger-btn" onClick={toggleSidebar}>☰</button>*/}
          <img src='/logo_rit_AI_transparent_white.png' style = {{height: '50px', width: 'auto'}} />
          <h1>FinRL Assistant</h1>
          {/*<button className="new-chat-header-btn" onClick={handleNewChat} title="New Chat">
            ✏️
                  </button>*/}
        </div>

        {/* Chat Window */}
        <div className="chat-window" style={{ overflowY: 'auto' }}>
          {/* FIX: was `ClassName` (capital C) — React prop names are case-sensitive */}
          {activeMessages.length === 0 && (
            <div className="empty-chat-hint">
              <p>Start a new conversation by typing below.</p>
            </div>
          )}
          {activeMessages.map((message) => (
            <div key={message.id} className={`chat-message ${message.sender}`}>
              <p>{message.text}</p>
              {/* If the backend generated a PDF for this message, show an inline download button */}
              
              {message.pdf_filename && (
                <div style ={{textAlign: 'center'}}>
                <button onClick={() => setPreviewPdf(message.pdf_filename)} className='download-button'> {message.pdf_filename} </button>
                </div>
              )}
            </div>
          ))}

          {isDataLoading && (
            <div className="chat-message assistant">
              <LoadingDots />
            </div>
          )}

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

          <div ref={chatEndRef} />
        </div>

        {/* Suggested Stocks */}
        <div style={{ padding: '6px 16px 2px', display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
          <span style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>Suggested:</span>
          {suggestedStocks.map(ticker => (
            <button
              key={ticker}
              onClick={() => setInputValue(`Generate a report on ${ticker}`)}
              className='suggested-ticker'
            >
              {ticker}
            </button>
          ))}
        </div>

        {/* Input */}
        <div className="input-container">
          <textarea
            ref={textareaRef}
            placeholder="Type Your Message Here..."
            className="chat-input"
            value={inputValue}
            onChange={(e) => { setInputValue(e.target.value); autoResize(e.target); }}
            onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
            disabled={isDataLoading}
          />
          <button
            className="send-btn"
            onClick={handleSend}
            disabled={isDataLoading || !inputValue.trim()}
          >
            {isDataLoading ? '...' : 'Send'}
          </button>
        </div>
      </div>
      {previewPdf && <PdfPreviewOverlay filepath={previewPdf} onClose={() => setPreviewPdf(null)} />}
    </div>
  );
}

export default Frontend;