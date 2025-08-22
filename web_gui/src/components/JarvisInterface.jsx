import React, { useState, useEffect, useRef, useCallback, useMemo, memo } from 'react';
import GlassyBlob from './GlassyBlob';
import { useAudioAnalyzer } from './AudioAnalyzer';
import ChatPanel from './ChatPanel';

const MemoizedGlassyBlob = memo(GlassyBlob);
const MemoizedChatPanel = memo(ChatPanel);

const JarvisInterface = () => {
  const [mode, setMode] = useState('idle');
  const [intensity, setIntensity] = useState(0.5);
  const [userText, setUserText] = useState('');
  const [assistantText, setAssistantText] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [conversationHistory, setConversationHistory] = useState([]);
  const [currentResponse, setCurrentResponse] = useState('');
  const [micEnabled, setMicEnabled] = useState(false);
  const micEnabledRef = useRef(true);
  useEffect(() => {
    micEnabledRef.current = micEnabled;
  }, [micEnabled]);
  const [isWaitingForResponse, setIsWaitingForResponse] = useState(false);

  const wsRef = useRef(null);
  const responseRef = useRef('');
  const lastTextInputRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const isConnectingRef = useRef(false);

  // Helper function to safely send WebSocket messages
  const sendWebSocketMessage = useCallback((message) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
      return true;
    }
    console.warn('WebSocket not ready. Message not sent:', message);
    return false;
  }, []);

  // Audio analyzer for real-time audio level monitoring
  const { startListening, stopListening, isListening, audioLevel } = useAudioAnalyzer(
    (level) => {
      if (mode === 'listening' || mode === 'idle') {
        setIntensity(prevIntensity => {
          const newIntensity = Math.max(0.1, level * 1.5);
          // Only update if the change is significant
          if (Math.abs(newIntensity - prevIntensity) > 0.01) {
            return newIntensity;
          }
          return prevIntensity;
        });
      }
    }
  );

  const addToConversation = useCallback((role, text) => {
    const messageId = `${role}-${text}-${Date.now()}`;
    lastTextInputRef.current = { text, timestamp: Date.now() };
    setConversationHistory(prev => [...prev, { role, text, timestamp: new Date().toLocaleTimeString(), id: messageId }]);
  }, []);

  const handleJarvisMessage = useCallback((data) => {
    switch (data.type) {
      case 'user_text':
        if (lastTextInputRef.current && lastTextInputRef.current.text === data.text && (Date.now() - lastTextInputRef.current.timestamp) < 2000) {
          // Duplicate, do nothing
        } else {
          addToConversation('user', data.text);
        }
        setIsWaitingForResponse(true);
        break;
      case 'assistant_stream':
        setIsWaitingForResponse(false);
        responseRef.current += data.text;
        setCurrentResponse(responseRef.current);
        break;
      case 'assistant_final':
        setAssistantText(data.text);
        addToConversation('assistant', data.text);
        responseRef.current = '';
        setCurrentResponse('');
        setIsWaitingForResponse(false);
        setMode('idle');
        setIntensity(0.5);
        break;
      case 'mode_change':
        setMode(data.mode);
        if (data.mode === 'listening') {
          setIntensity(0.3);
          if (micEnabled) startListening();
        } else if (data.mode === 'speaking') {
          setIntensity(data.intensity || 0.8);
          stopListening();
        } else if (data.mode === 'idle') {
          setIntensity(0.5);
          if (micEnabled) startListening();
        } else {
          setIntensity(0.5);
          stopListening();
        }
        break;
      case 'audio_level':
        if (data.mode === 'speaking') {
          setIntensity(Math.max(0.3, data.level * 1.2));
        }
        break;
      default:
        console.log('Unknown message type:', data.type);
    }
  }, [addToConversation, micEnabled, startListening, stopListening]);

  // Keep a stable reference to the latest message handler to avoid reconnect churn
  const messageHandlerRef = useRef(() => {});
  useEffect(() => {
    messageHandlerRef.current = handleJarvisMessage;
  }, [handleJarvisMessage]);

  const connectToJarvis = useCallback(() => {
    // Clear any existing reconnection timeout
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current.timeout);
      reconnectTimeoutRef.current = null;
    }

    // Prevent multiple simultaneous connection attempts
    if (isConnectingRef.current || (wsRef.current && wsRef.current.readyState === WebSocket.CONNECTING)) {
      console.log('Connection attempt already in progress');
      return;
    }

    // Check if we're already connected
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      console.log('Already connected to Jarvis backend');
      setIsConnected(true);
      return;
    }

    // Limit reconnection attempts to prevent infinite loops
    const maxReconnectAttempts = 20;
    if (reconnectTimeoutRef.current && reconnectTimeoutRef.current.attempt >= maxReconnectAttempts) {
      console.error(`Maximum reconnection attempts (${maxReconnectAttempts}) reached. Stopping reconnection.`);
      return;
    }

    try {
      isConnectingRef.current = true;
      console.log('Attempting to connect to Jarvis backend...');
      wsRef.current = new WebSocket('ws://localhost:8765');
      
      wsRef.current.onopen = () => {
        isConnectingRef.current = false;
        console.log('Connected to Jarvis backend');
        setIsConnected(true);
        // Reset reconnection attempt counter on successful connection
        reconnectTimeoutRef.current = { attempt: 0 };
        // Use the helper function to send message
        // Add a small delay before sending the enable_mic message to ensure connection is stable
        setTimeout(() => {
          if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            const type = micEnabledRef.current ? 'enable_mic' : 'disable_mic';
            try {
              wsRef.current.send(JSON.stringify({ type }));
            } catch {}
          }
        }, 100);
      };
      wsRef.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          messageHandlerRef.current(data);
        } catch (e) {
          console.error('Failed to parse message:', e);
        }
      };
      wsRef.current.onclose = (event) => {
        isConnectingRef.current = false;
        console.log('Disconnected from Jarvis backend', event);
        setIsConnected(false);
        
        // Check if it was a clean close or an error
        if (event.wasClean) {
          console.log('Connection closed cleanly');
        } else {
          console.log('Connection closed unexpectedly');
        }
        console.log('Close code:', event.code);
        console.log('Close reason:', event.reason);
        
        // Only attempt reconnection if not explicitly closed by the component
        if (!event.wasClean) {
          console.log('Unclean disconnect, scheduling reconnection...');
          // More conservative exponential backoff: start with 10 seconds, max 120 seconds
          // This will significantly reduce the rapid connect/disconnect cycles
          const reconnectDelay = Math.min(10000 * Math.pow(1.5, (reconnectTimeoutRef.current?.attempt || 0)), 120000);
          reconnectTimeoutRef.current = { 
            attempt: (reconnectTimeoutRef.current?.attempt || 0) + 1,
            timeout: setTimeout(connectToJarvis, reconnectDelay)
          };
          console.log(`Reconnection scheduled in ${reconnectDelay}ms (attempt ${reconnectTimeoutRef.current.attempt})`);
        }
      };
      wsRef.current.onerror = (error) => {
        isConnectingRef.current = false;
        console.error('WebSocket error:', error);
        console.error('WebSocket readyState:', wsRef.current?.readyState);
        console.error('WebSocket URL:', wsRef.current?.url);
        
        // More descriptive error messages
        if (wsRef.current?.readyState === WebSocket.CLOSED) {
          console.error('WebSocket connection failed - server may be down or port unavailable');
        } else if (wsRef.current?.readyState === WebSocket.CONNECTING) {
          console.error('WebSocket connection failed during handshake');
        }
        
        setIsConnected(false);
        // Don't immediately reconnect on error - let the onclose handler deal with reconnection
        // This prevents double reconnection attempts
      };
    } catch (error) {
      isConnectingRef.current = false;
      console.error('Failed to connect to Jarvis:', error);
      setIsConnected(false);
      
      // Schedule reconnection with exponential backoff, but limit attempts
      if (!reconnectTimeoutRef.current || reconnectTimeoutRef.current.attempt < maxReconnectAttempts) {
        const reconnectDelay = Math.min(5000 * Math.pow(1.5, (reconnectTimeoutRef.current?.attempt || 0)), 60000);
        reconnectTimeoutRef.current = { 
          attempt: (reconnectTimeoutRef.current?.attempt || 0) + 1,
          timeout: setTimeout(connectToJarvis, reconnectDelay)
        };
        console.log(`Reconnection scheduled in ${reconnectDelay}ms due to error (attempt ${reconnectTimeoutRef.current.attempt})`);
      } else {
        console.error(`Maximum reconnection attempts (${maxReconnectAttempts}) reached. Stopping reconnection.`);
      }
    }
  }, []);

  useEffect(() => {
    connectToJarvis();
    return () => {
      // Clear reconnection timeout
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current.timeout);
        reconnectTimeoutRef.current = null;
      }
      
      // Close WebSocket connection cleanly
      if (wsRef.current) {
        try {
          wsRef.current.onclose = null; // Remove onclose handler to prevent reconnection
          wsRef.current.close(1000, 'Component unmounted');
        } catch (e) {
          console.log('Error closing WebSocket:', e);
        }
        wsRef.current = null;
      }
      
      stopListening();
      isConnectingRef.current = false;
    };
  }, []);

  const sendTextMessage = useCallback(() => {
    if (userText.trim() && isConnected) {
      const message = userText.trim();
      addToConversation('user', message);
      setIsWaitingForResponse(true);
      // Use the helper function to send message
      sendWebSocketMessage({ type: 'text_input', text: message });
      setUserText('');
    }
  }, [userText, isConnected, addToConversation, sendWebSocketMessage]);

  const toggleMicrophone = useCallback(async () => {
    if (!micEnabled) {
      try {
        await startListening();
        setMicEnabled(true);
        // Use the helper function to send message
        sendWebSocketMessage({ type: 'enable_mic' });
      } catch (error) {
        console.error('Failed to enable microphone:', error);
      }
    } else {
      stopListening();
      setMicEnabled(false);
      // Use the helper function to send message
      sendWebSocketMessage({ type: 'disable_mic' });
    }
  }, [micEnabled, startListening, stopListening, sendWebSocketMessage]);

  const clearConversation = useCallback(() => {
    setConversationHistory([]);
    setCurrentResponse('');
    responseRef.current = '';
  }, []);

  const [isChatOpen, setIsChatOpen] = useState(false);

  const containerStyle = useMemo(() => ({
    minHeight: '100vh',
    background: 'linear-gradient(135deg, #000000 0%, #0a0a0a 100%)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontFamily: 'Inter, system-ui, sans-serif',
    position: 'relative',
    overflow: 'hidden'
  }), []);

  const connectionStatusStyle = useMemo(() => ({
    position: 'absolute',
    top: '20px',
    left: '20px',
    color: isConnected ? '#00ff88' : '#ff4757',
    fontSize: '12px',
    fontWeight: '500',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '8px 12px',
    background: 'rgba(0, 0, 0, 0.3)',
    borderRadius: '20px',
    backdropFilter: 'blur(10px)'
  }), [isConnected]);

  const connectionIndicatorStyle = useMemo(() => ({
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    background: isConnected ? '#00ff88' : '#ff4757',
    boxShadow: `0 0 10px ${isConnected ? '#00ff88' : '#ff4757'}`
  }), [isConnected]);

  const chatButtonStyle = useMemo(() => ({
    position: 'fixed',
    bottom: '40px',
    right: '40px',
    width: '50px',
    height: '50px',
    borderRadius: '50%',
    background: 'rgba(64, 158, 255, 0.2)',
    border: '1px solid rgba(64, 158, 255, 0.4)',
    cursor: 'pointer',
    display: isChatOpen ? 'none' : 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    backdropFilter: 'blur(10px)',
    transition: 'all 0.3s ease',
    zIndex: 1000,
    boxShadow: '0 0 20px rgba(64, 158, 255, 0.3)'
  }), [isChatOpen]);

  const micButtonStyle = useMemo(() => ({
    position: 'fixed',
    bottom: '35px',
    left: 'calc(50vw - 30px)',
    width: '60px',
    height: '60px',
    borderRadius: '50%',
    background: micEnabled
      ? 'linear-gradient(135deg, #00ff88, #00d4aa)'
      : 'rgba(36, 58, 82, 0.8)',
    border: micEnabled
      ? '2px solid rgba(0, 255, 136, 0.4)'
      : '2px solid rgba(255, 255, 255, 0.2)',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    backdropFilter: 'blur(10px)',
    transition: 'all 0.3s ease',
    boxShadow: micEnabled
      ? '0 0 30px rgba(0, 255, 136, 0.4), 0 4px 15px rgba(0, 0, 0, 0.3)'
      : '0 0 20px rgba(36, 58, 82, 0.5), 0 4px 15px rgba(0, 0, 0, 0.3)',
    zIndex: 1000
  }), [micEnabled]);

  return (
    <div style={containerStyle}>
      <div style={connectionStatusStyle}>
        <div style={connectionIndicatorStyle}></div>
        {isConnected ? 'Connected' : 'Disconnected'}
        {!isConnected && (
          <span style={{ marginLeft: '8px', fontStyle: 'italic' }}>
            (Retrying...)
          </span>
        )}
      </div>

      <button
        onClick={() => setIsChatOpen(!isChatOpen)}
        title="Toggle Chat Panel"
        style={chatButtonStyle}
        onMouseOver={(e) => {
          const button = e.currentTarget;
          button.style.transform = 'scale(1.1)';
          button.style.background = 'rgba(64, 158, 255, 0.3)';
          button.style.boxShadow = '0 0 30px rgba(64, 158, 255, 0.5)';
        }}
        onMouseOut={(e) => {
          const button = e.currentTarget;
          button.style.transform = 'scale(1)';
          button.style.background = 'rgba(64, 158, 255, 0.2)';
          button.style.boxShadow = '0 0 20px rgba(64, 158, 255, 0.3)';
        }}
      >
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M20 2H4C2.9 2 2 2.9 2 4V22L6 18H20C21.1 18 22 17.1 22 16V4C22 2.9 21.1 2 20 2ZM20 16H6L4 18V4H20V16Z" fill="#409EFF"/>
        </svg>
      </button>

      <button
        onClick={toggleMicrophone}
        title={micEnabled ? "Disable Microphone" : "Enable Microphone"}
        style={micButtonStyle}
        onMouseOver={(e) => {
          const button = e.currentTarget;
          button.style.transform = 'scale(1.1)';
          if (micEnabled) {
            button.style.boxShadow = '0 0 40px rgba(0, 255, 136, 0.6), 0 4px 20px rgba(0, 0, 0, 0.4)';
          } else {
            button.style.boxShadow = '0 0 30px rgba(36, 58, 82, 0.7), 0 4px 20px rgba(0, 0, 0, 0.4)';
          }
        }}
        onMouseOut={(e) => {
          const button = e.currentTarget;
          button.style.transform = 'scale(1)';
          if (micEnabled) {
            button.style.boxShadow = '0 0 30px rgba(0, 255, 136, 0.4), 0 4px 15px rgba(0, 0, 0, 0.3)';
          } else {
            button.style.boxShadow = '0 0 20px rgba(36, 58, 82, 0.5), 0 4px 15px rgba(0, 0, 0, 0.3)';
          }
        }}
      >
        <div style={{
          width: '36px',
          height: '36px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          position: 'relative'
        }}>
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className="mic-icon">
            <g className="mic-body">
              <path d="M12 15C13.6569 15 15 13.6569 15 12V6C15 4.34315 13.6569 3 12 3C10.3431 3 9 4.34315 9 6V12C9 13.6569 10.3431 15 12 15Z" fill="white"/>
            </g>
            <g className="mic-stand">
              <path d="M17 12C17 14.7614 14.7614 17 12 17C9.23858 17 7 14.7614 7 12H5C5 15.866 7.93452 19 11.5 19V22H12.5V19C16.0655 19 19 15.866 19 12H17Z" fill="white"/>
            </g>
          </svg>
          {micEnabled && (
            <>
              <div style={{
                position: 'absolute',
                right: '-6px',
                top: '50%',
                transform: 'translateY(-50%)',
                width: '4px',
                height: '4px',
                border: '1px solid rgba(0, 255, 136, 0.6)',
                borderRadius: '50%',
                animation: 'soundwave 2s ease-out infinite'
              }} />
              <div style={{
                position: 'absolute',
                right: '-10px',
                top: '50%',
                transform: 'translateY(-50%)',
                width: '6px',
                height: '6px',
                border: '1px solid rgba(0, 255, 136, 0.4)',
                borderRadius: '50%',
                animation: 'soundwave 2s ease-out 0.3s infinite'
              }} />
            </>
          )}
        </div>
      </button>

      <div style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1
      }}>
        <div style={{
          marginBottom: '30px',
          filter: 'drop-shadow(0 0 50px rgba(255, 215, 0, 0.3))'
        }}>
          <MemoizedGlassyBlob
            mode={mode}
            intensity={intensity}
            size={500}
          />
        </div>

        <div style={{
          color: 'rgba(255, 255, 255, 0.7)',
          fontSize: '14px',
          fontWeight: '400',
          textAlign: 'center',
          textTransform: 'uppercase',
          letterSpacing: '2px',
          opacity: 0.8
        }}>
          {mode === 'idle' && 'Ready'}
          {mode === 'listening' && `Listening ${Math.round(audioLevel * 100)}%`}
          {mode === 'thinking' && 'Processing...'}
          {mode === 'speaking' && 'Speaking'}
        </div>
      </div>

      <MemoizedChatPanel
        isOpen={isChatOpen}
        conversationHistory={conversationHistory}
        currentResponse={currentResponse}
        isWaitingForResponse={isWaitingForResponse}
        onSendMessage={sendTextMessage}
        userText={userText}
        setUserText={setUserText}
        isConnected={isConnected}
        onClearHistory={clearConversation}
        onClose={() => setIsChatOpen(false)}
      />

      <style>
        {`
          @keyframes blink {
            0%, 50% { opacity: 1; }
            51%, 100% { opacity: 0; }
          }
          
          @keyframes slideIn {
            from { transform: translateX(100%); }
            to { transform: translateX(0); }
          }
          
          @keyframes slideOut {
            from { transform: translateX(0); }
            to { transform: translateX(100%); }
          }
          
          * {
            box-sizing: border-box;
          }
          
          ::-webkit-scrollbar {
            width: 6px;
          }
          
          ::-webkit-scrollbar-track {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 3px;
          }
          
          ::-webkit-scrollbar-thumb {
            background: rgba(255, 255, 255, 0.2);
            border-radius: 3px;
          }
          
          ::-webkit-scrollbar-thumb:hover {
            background: rgba(255, 255, 255, 0.3);
          }
          
          @keyframes pulse {
            from { 
              opacity: 0.6;
              transform: translateX(-50%) scaleY(0.8);
            }
            to { 
              opacity: 1;
              transform: translateX(-50%) scaleY(1.2);
            }
          }
          
          @keyframes soundwave {
            0% {
              transform: translateY(-50%) scale(0);
              opacity: 1;
            }
            50% {
              opacity: 0.5;
            }
            100% {
              transform: translateY(-50%) scale(2);
              opacity: 0;
            }
          }
        `}
      </style>
    </div>
  );
};

export default JarvisInterface;
