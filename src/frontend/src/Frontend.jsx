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

import React, { useState } from 'react';
import './App.css';

function Frontend() {
    const [isSidebarOpen, setIsSidebarOpen] = useState(false);
    // const [isDataLoading, setIsDataLoading] = useState(false);
  
    // NEW: A list of past reports
    const [pastReports, setPastReports] = useState([
      { id: 1, ticker: 'AAPL', date: 'March 15', status: 'Completed' },
      { id: 2, ticker: 'TSLA', date: 'March 18', status: 'Completed' },
      { id: 3, ticker: 'NVDA', date: 'March 20', status: 'Failed' }
    ]);

  const toggleSidebar = () => {
    setIsSidebarOpen(!isSidebarOpen);
  };

  return (
    <div className="app-wrapper">
      
      {/* 1. The Sidebar */}
      <div className={`sidebar ${isSidebarOpen ? 'open' : 'closed'}`}>
        <div className="sidebar-header">
          <h2>Past Reports</h2>
          <button onClick={toggleSidebar}>✕</button>
        </div>
        <div className="sidebar-content">
          {/* Loop through the pastReports array */}
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
          <div className="spacer"></div> {/* This empty div perfectly centers the title! */}
        </div>
        
        {/* The Big Chat Window */}
        <div className="chat-window">
          {/* Chat messages will appear here later */}
        </div>

        {/* The Input Field and Button */}
        <div className="input-container">
          <input 
            type="text" 
            placeholder="Ask about your FinRL model..." 
            className="chat-input"
          />
          <button className="send-btn">Send</button>
        </div>

      </div>

    </div>
  );
}

export default Frontend;
