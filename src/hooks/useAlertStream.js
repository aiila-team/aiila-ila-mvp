// src/hooks/useAlertStream.js
// Connect to Sridhar's WebSocket server for live alert push

import { useEffect, useRef, useState } from 'react';

export default function useAlertStream(onNewAlert) {
  const wsRef = useRef(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';
    
    function connect() {
      try {
        wsRef.current = new WebSocket(`${WS_URL}/ws/alerts`);
        
        wsRef.current.onopen = () => {
          console.log('[ILA] Alert stream connected');
          setConnected(true);
        };

        wsRef.current.onmessage = (event) => {
          try {
            const alert = JSON.parse(event.data);
            onNewAlert(alert);
          } catch (e) {
            console.error('[ILA] WS parse error', e);
          }
        };

        wsRef.current.onclose = () => {
          setConnected(false);
          console.log('[ILA] Alert stream disconnected, reconnecting in 3s...');
          setTimeout(connect, 3000);
        };

        wsRef.current.onerror = (e) => {
          console.error('[ILA] WS error:', e);
        };
      } catch (e) {
        console.error('[ILA] WS connect failed:', e);
        setTimeout(connect, 5000);
      }
    }

    // Only connect in production (backend is running)
    if (import.meta.env.PROD) {
      connect();
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.onclose = null; // Prevent reconnect on cleanup
        wsRef.current.close();
      }
    };
  }, []);

  return { connected };
}
