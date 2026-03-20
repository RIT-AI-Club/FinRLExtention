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

import React, {useState} from 'react';

const Frontend = () => {
    // State setup
    const [inputText, setInputText] = useState('');
    const [messages, setMessages] = useState([]);
    const [isLoading, setIsLoading] = useState(false);

    // the function that runs when you click "Send"
    const handleSendMessage = async () => {
        if (!inputText.trim()) return; // Prevent sending empty blank spaces
        
        // Save the user's message to the chat history immediately
        const userMessage = {role : 'user', content: inputText};
        const updatedMessages = [...messages, userMessage];
        

        setMessages(updatedMessages);
        setInputText(''); // Clears the input box
        setIsLoading(true);// Turns the loading spinner on

        try {
            const response = await fetch('https://localhost:5000/api/chat', {
                method: 'POST',
                headers: {'Content-type': 'application/json'},
                body: JSON.stringify({message: inputText}),
            });

            const data = await response.json();

            setMessages([...updatedMessages, {role: 'ai', content: data.reply}]);

        } catch (error) {
            console.error("Error connecting to backend:", error);
            setMessages([...updatedMessages, {role: 'system', content: "Connection failed. Is the backend running?"}])
        } finally {
            setIsLoading(false);
        }

    }; 

    return (
        <div style={{maxWidth: '600px', margin: '0 auto', padding: '20px', fontFamily: 'sans-serif'}}>
            <h2>FinRL Assistant</h2>
            {/* Chat History Window */}
            <div style={{height: '400px', border: '1px solid #ccc', overflowY: 'scroll', padding: '10px', marginBottom: '10px'}}> 
                {messages.map((msg, index) => (
                    <div key={index} style={{
                        textAlign: msg.role === 'user' ? 'right' : 'left', 
                        margin: '10px 0'
                    }}>
                        <strong style={{color: msg.role === 'user' ? 'blue' : 'green' }}>
                            {msg.role === 'user' ? 'You' : 'AI: '}
                        </strong>
                        <span>{msg.content}</span>
                    </div>
                ))}
                {isLoading && <div style={{ color: 'gray', fontStyle: 'italic'}}> AI is thinking about your portfolio...</div>}
            </div>
            

            {/* Input Area */}
            <div style={{display: 'flex', gap: '10px' }}>
                <input 
                    type="text"
                    value={inputText}
                    onChange={(e) => setInputText(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
                    placeholder="Ask about your FinRL model..."
                    style={{flexGrow: 1, padding: '10px'}}
                />
                <button
                    onClick={handleSendMessage}
                    disabled={isLoading}
                    style={{padding: '10px 20px', cursor: 'pointer'}}
                >
                    Send
                </button>
            </div>
        </div>
    )
}
