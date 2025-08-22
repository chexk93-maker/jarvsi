import React, { useState } from 'react';

const ChatInput = ({
  userText,
  setUserText,
  onSendMessage,
  isConnected,
}) => {
  const [isInputFocused, setIsInputFocused] = useState(false);

  return (
    <div style={{
      position: 'relative',
      padding: '20px',
      paddingTop: '10px',
      display: 'flex',
      alignItems: 'center',
      gap: '8px'
    }}>
      <div
        style={{
          flex: 1,
          position: 'relative',
        }}
      >
        <textarea
          value={userText}
          onChange={(e) => setUserText(e.target.value)}
          onFocus={() => setIsInputFocused(true)}
          onBlur={() => setIsInputFocused(false)}
          onKeyPress={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              onSendMessage();
            }
          }}
          placeholder="Message JARVIS..."
          style={{
            width: '100%',
            background: 'rgba(30, 41, 59, 0.8)',
            border: `1px solid ${isInputFocused ? 'rgba(59, 130, 246, 0.6)' : 'rgba(59, 130, 246, 0.3)'}`,
            outline: 'none',
