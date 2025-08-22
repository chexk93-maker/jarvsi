import React, { useState, useMemo, memo } from 'react';

const MessageItem = memo(({ message }) => {
  const messageStyle = useMemo(() => ({
    display: 'flex',
    justifyContent: message.role === 'user' ? 'flex-end' : 'flex-start',
    marginBottom: '8px'
  }), [message.role]);

  const bubbleStyle = useMemo(() => ({
    maxWidth: '85%',
    padding: '12px 16px',
    borderRadius: message.role === 'user'
      ? '20px 20px 5px 20px'   // user on right
      : '20px 20px 20px 5px',  // assistant on left
    background: message.role === 'user'
      ? 'rgba(59, 130, 246, 0.8)'
      : 'rgba(148, 163, 184, 0.9)',
    color: 'white',
    fontSize: '14px',
    lineHeight: '1.4',
    wordWrap: 'break-word',
    backdropFilter: 'blur(10px)',
    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.3)'
  }), [message.role]);

  return (
    <div style={messageStyle}>
      <div style={bubbleStyle}>
        {message.text}
      </div>
    </div>
  );
});

const ChatPanel = ({
  isOpen,
  conversationHistory,
  currentResponse,
  isWaitingForResponse,
  onSendMessage,
  userText,
  setUserText,
  isConnected,
  onClearHistory,
  onClose
}) => {
  const [isInputFocused, setIsInputFocused] = useState(false);

  const backdropStyle = useMemo(() => ({
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    background: 'rgba(0, 0, 0, 0.5)',
    zIndex: 998,
    backdropFilter: 'blur(2px)',
    animation: 'fadeIn 0.3s ease'
  }), []);

  const panelStyle = useMemo(() => ({
    position: 'fixed',
    top: 0,
    right: 0,
    width: '400px',
    height: '100vh',
    background: 'linear-gradient(180deg, #1e293b 0%, #0f172a 50%, #020617 100%)',
    border: 'none',
    zIndex: 999,
    display: 'flex',
    flexDirection: 'column',
    transform: isOpen ? 'translateX(0)' : 'translateX(100%)',
    transition: 'transform 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
    boxShadow: '0 0 50px rgba(0, 0, 0, 0.8)'
  }), [isOpen]);

  return (
    <>
      {isOpen && <div style={backdropStyle} />}
      <div style={panelStyle}>
        {/* Header */}
        <div style={{
          padding: '20px',
          borderBottom: '1px solid rgba(59, 130, 246, 0.3)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          position: 'relative',
          background: 'rgba(30, 41, 59, 0.8)',
          backdropFilter: 'blur(10px)'
        }}>
          <button
            onClick={onClose}
            style={{
              position: 'absolute',
              top: '15px',
              left: '15px',
              width: '30px',
              height: '30px',
              borderRadius: '50%',
              background: 'rgba(255, 87, 87, 0.2)',
              border: '1px solid rgba(255, 87, 87, 0.4)',
              color: '#FF5757',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '16px',
              fontWeight: 'bold',
              transition: 'all 0.2s ease',
              zIndex: 1001
            }}
            onMouseOver={(e) => {
              e.target.style.background = 'rgba(255, 87, 87, 0.3)';
              e.target.style.transform = 'scale(1.1)';
            }}
            onMouseOut={(e) => {
              e.target.style.background = 'rgba(255, 87, 87, 0.2)';
              e.target.style.transform = 'scale(1)';
            }}
          >
            ✕
          </button>

          <h3 style={{
            color: 'rgba(255, 255, 255, 0.9)',
            margin: 0,
            fontSize: '16px',
            fontWeight: '600',
            letterSpacing: '0.5px',
            marginLeft: '40px'
          }}>
            Conversation
          </h3>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <button
              onClick={onClearHistory}
              style={{
                padding: '8px 12px',
                background: 'rgba(255, 87, 34, 0.2)',
                color: '#FF5722',
                border: '1px solid rgba(255, 87, 34, 0.3)',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '11px',
                fontWeight: '500',
                textTransform: 'uppercase',
                letterSpacing: '0.5px',
                transition: 'all 0.2s ease'
              }}
              onMouseOver={(e) => {
                e.target.style.background = 'rgba(255, 87, 34, 0.3)';
              }}
              onMouseOut={(e) => {
                e.target.style.background = 'rgba(255, 87, 34, 0.2)';
              }}
            >
              Clear
            </button>
          </div>
        </div>

        {/* Messages Area */}
        <div style={{
          flex: 1,
          overflowY: 'auto',
          padding: '20px 15px',
          display: 'flex',
          flexDirection: 'column',
          gap: '12px'
        }}>
          {conversationHistory.length === 0 ? (
            <div style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              height: '100%',
              textAlign: 'center',
              color: 'rgba(148, 163, 184, 0.6)'
            }}>
              <div style={{
                fontSize: '48px',
                marginBottom: '16px',
                opacity: 0.4
              }}>
                💬
              </div>
              <p style={{ margin: 0, fontSize: '14px' }}>
                Start a conversation with JARVIS
              </p>
            </div>
          ) : (
            <>
              {conversationHistory.map((message, index) => (
                <MessageItem key={index} message={message} />
              ))}

              {isWaitingForResponse && !currentResponse && (
                <div style={{
                  display: 'flex',
                  justifyContent: 'flex-start',
                  marginBottom: '8px'
                }}>
                  <div style={{
                    maxWidth: '85%',
                    padding: '12px 16px',
                    borderRadius: '20px 20px 20px 5px',
                    background: 'rgba(148, 163, 184, 0.9)',
                    color: 'white',
                    fontSize: '14px',
                    lineHeight: '1.4',
                    opFilter: 'blur(10px)',
                    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.3)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px'
                  }}>
                    <div className="loading-dots">
                      <div className="dot"></div>
                      <div className="dot"></div>
                      <div className="dot"></div>
                    </div>
                  </div>
                </div>
              )}

              {currentResponse && (
                <div style={{
                  display: 'flex',
                  justifyContent: 'flex-start',
                  marginBottom: '8px'
                }}>
                  <div style={{
                    maxWidth: '85%',
                    padding: '12px 16px',
                    borderRadius: '20px 20px 20px 5px',
                    background: 'rgba(148, 163, 184, 0.9)',
                    color: 'white',
                    fontSize: '14px',
                    lineHeight: '1.4',
                    wordWrap: 'break-word',
                    backdropFilter: 'blur(10px)',
                    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.3)'
                  }}>
                    {currentResponse}
                    <span style={{
                      animation: 'blink 1s infinite',
                      marginLeft: '2px',
                      color: 'rgba(255, 255, 255, 0.7)'
                    }}>|</span>
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Floating Input Area */}
        <div style={{
          position: 'relative',
          padding: '20px',
          paddingTop: '10px',
          display: 'flex',
          alignItems: 'center',
          gap: '10px'
        }}>
          <div
            style={{
              flex: 1,
              background: 'rgba(30, 41, 59, 0.8)',
              borderRadius: '25px',
              padding: '12px 16px',
              boxShadow: isInputFocused
                ? '0 0 15px rgba(59, 130, 246, 0.5), 0 8px 32px rgba(0, 0, 0, 0.6)'
                : '0 8px 32px rgba(0, 0, 0, 0.5)',
              backdropFilter: 'blur(20px)',
              border: `1px solid ${isInputFocused ? 'rgba(59, 130, 246, 0.6)' : 'rgba(59, 130, 246, 0.3)'}`,
              transition: 'all 0.3s ease'
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
                background: 'transparent',
                border: 'none',
                outline: 'none',
                color: 'rgba(255, 255, 255, 0.9)',
                fontSize: '14px',
                fontFamily: 'Inter, system-ui, sans-serif',
                resize: 'none',
                minHeight: '20px',
                maxHeight: '120px',
                lineHeight: '1.4'
              }}
              rows={1}
              onInput={(e) => {
                e.target.style.height = 'auto';
                e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
              }}
            />
          </div>

          <button
            onClick={onSendMessage}
            disabled={!userText.trim() || !isConnected}
            style={{
              width: '50px',
              height: '50px',
              borderRadius: '50%',
              background: (isConnected && userText.trim())
                ? 'linear-gradient(135deg, #6366f1, #8b5cf6)'
                : 'rgba(156, 163, 175, 0.5)',
              color: 'white',
              border: 'none',
              cursor: (isConnected && userText.trim()) ? 'pointer' : 'not-allowed',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '14px',
              transition: 'all 0.2s ease',
              flexShrink: 0,
              boxShadow: (isConnected && userText.trim())
                ? '0 4px 12px rgba(99, 102, 241, 0.3)'
                : 'none'
            }}
            onMouseOver={(e) => {
              if (isConnected && userText.trim()) {
                e.target.style.transform = 'scale(1.05)';
                e.target.style.boxShadow = '0 6px 16px rgba(99, 102, 241, 0.4)';
              }
            }}
            onMouseOut={(e) => {
              e.target.style.transform = 'scale(1)';
              e.target.style.boxShadow = (isConnected && userText.trim())
                ? '0 4px 12px rgba(99, 102, 241, 0.3)'
                : 'none';
            }}
          >
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                d="M2 21L23 12L2 3V10L17 12L2 14V21Z"
                fill="white"
              />
            </svg>
          </button>
        </div>
      </div>

      <style>
        {`
          @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
          }
          
          @keyframes loadingDots {
            0%, 20% {
              opacity: 0.4;
              transform: scale(0.8);
            }
            50% {
              opacity: 1;
              transform: scale(1.2);
            }
            80%, 100% {
              opacity: 0.4;
              transform: scale(0.8);
            }
          }
          
          .loading-dots {
            display: flex;
            align-items: center;
            gap: 4px;
          }
          
          .loading-dots .dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background-color: rgba(255, 255, 255, 0.8);
            animation: loadingDots 1.5s ease-in-out infinite;
          }
          
          .loading-dots .dot:nth-child(1) {
            animation-delay: 0s;
          }
          
          .loading-dots .dot:nth-child(2) {
            animation-delay: 0.3s;
          }
          
          .loading-dots .dot:nth-child(3) {
            animation-delay: 0.6s;
          }
        `}
      </style>
    </>
  );
};

export default memo(ChatPanel);
