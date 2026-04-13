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
 */

import React, { act, useState } from 'react';
import './App.css';

function Frontend() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [inputValue, setInputValue] = useState('');
  const [pastReports, setPastReports] = useState([
    {id: 1, ticker: 'AAPL', date: 'April 3', status: 'Pending'}
  ]);
  const [isDataLoading, setIsDataLoading] = useState(false);

  // ---- NEW: Conversation states ---

  const [conversations, setConversations] = useState([
    { id: 1, messages: [] }
  ]);
  const [activeConvoID, setActiveConvoID] = useState(1);

  // Derive the active conversations messages 

  const activeMesssages = conversations.find(c => c.id === activeConvoID)?.messages || [];

  // ----)

  // start a new convo

  const handleNewChat = () => {
    const newConvo = { id: Date.now(), messages: [] };
    setConversations(pre => [...prev, newConvo]);
    setActiveConvoID(newConvo.id)
  }

  // switch to an existing conversation

  const handleSelectConvo = (id) => {
    setActiveConvoID(id);
  }

  


  const [messages, setMessages] = useState([]);
  const [newChat, setNewChat] = [{}];

  const handleSend = () => {
    if (inputValue.trim() !== '') {
      setConversations(prev => prev.map(c => c.id === activeConvoID ? { ...c, messages: [...c.messages, {id: Date.now(), text: inputValue, sender: 'user'}] }
        : c
        )
      );
      setInputValue('');
    }
  }

  const toggleSidebar = () => {
    setIsSidebarOpen(!isSidebarOpen);
  };

  // Get a display title for each conversation (first message, truncated)
  const getConvoTitle = (convo) => {
    if (convo.messages.length === 0) return 'New Conversation';
    return convo.messages[0].text.length > 28
      ? convo.messages[0].text.slice(0, 28) + '...'
      : convo.messages[0].text;
  }

  return (
    <div className="app-wrapper">
      
      {/* 1. The Sidebar */}
      <div className={`sidebar ${isSidebarOpen ? 'open' : 'closed'}`}>
        <div className="sidebar-header">
          <h2>History</h2>
          <div className="sidebar-header-actions">
            <button className="new-chat-btn" onClick={handleNewChat}>
              New Chat
            </button>
            <button onClick={toggleSidebar}>✕</button>
          </div>
        </div>
        {/* Conversation list */}
        <div className='sidebar-section-label'>Chats</div>
        <div className="sidebar-content">
          {conversations.map((convo) => (
            <div 
              key={convo.id}
              className={`convo-item ${convo.id === activeConvoID ? 'active convo' : ''}`}
              onClick={() => handleSelectConvo(convo.id)}
            >
              <span className="convo-icon">💬</span>
              <span className="convo-title">{getConvoTitle(convo)}</span>
            </div>
          ))}
        </div>

        {/* Past Reports Part*/}
        <div className="sidebar-section-label">Past Reports</div>
        <div className="sidebar-content">
          {pastReports.map((report) => (
            <div key={report.id} className="report-item">
              <p><strong>{report.ticker}</strong> - {report.date}</p>
              <small>{report.status}</small>
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
          <button className="new-chat-header-btn" onClick={handleNewChat} title="New Chat">
            New Chat
          </button>
          <div className="spacer"></div> {/* This empty div perfectly centers the title! */}
        </div>
        
        {/* The Big Chat Window */}
        <div className="chat-window" style={{overflowY: 'auto'}}>
          {activeMesssages.length === 0  && (
            <div ClassName="empty-chat-hint">
              <p>Start a new conversation by typing below.</p>
            </div>
          )}
          {activeMesssages.map((message) => (
            <div key={message.id} className={`chat-message ${message.sender}`}>
              <p>{message.text}</p>
            </div>
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
          />
          <button className="send-btn" onClick={handleSend}>Send</button>
        </div>
      </div>

    </div>
  );
}

export default Frontend;
