import { useEffect, useRef, useCallback } from 'react';
import { WsMessage } from '../types';
import { useAlertStore } from '../store';

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws';

interface UseAlertStreamOptions {
  onMessage?: (msg: WsMessage) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
}

export const useAlertStream = (options: UseAlertStreamOptions = {}) => {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const addAlert = useAlertStore((s) => s.addAlert);

  const connect = useCallback(() => {
    const token = localStorage.getItem('auth_token');
    const url = token ? `${WS_URL}?token=${token}` : WS_URL;

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('[WS] Connected');
        options.onConnect?.();
      };

      ws.onmessage = (event) => {
        try {
          const msg: WsMessage = JSON.parse(event.data);
          if (msg.type === 'alert') {
            addAlert(msg.payload);
          }
          options.onMessage?.(msg);
        } catch (err) {
          console.error('[WS] Failed to parse message', err);
        }
      };

      ws.onclose = () => {
        console.log('[WS] Disconnected — reconnecting in 3s...');
        options.onDisconnect?.();
        reconnectRef.current = setTimeout(connect, 3000);
      };

      ws.onerror = (err) => {
        console.error('[WS] Error', err);
        ws.close();
      };
    } catch (err) {
      console.error('[WS] Could not connect', err);
      reconnectRef.current = setTimeout(connect, 5000);
    }
  }, []);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectRef.current) clearTimeout(reconnectRef.current);
      wsRef.current?.close();
    };
  }, [connect]);

  const send = useCallback((data: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  return { send };
};
