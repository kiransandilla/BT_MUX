import { useEffect, useRef, useState } from 'react';

/**
 * Custom React hook for connecting to the BT-Mux WebSocket stream.
 * Automatically handles reconnection and parses incoming telemetry and scheduler events.
 */
export function useSchedulerSocket(url = 'ws://localhost:8000/ws') {
  const [isConnected, setIsConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState(null);
  const [eventHistory, setEventHistory] = useState([]);
  const wsRef = useRef(null);

  useEffect(() => {
    let reconnectTimeout = null;

    function connect() {
      try {
        const ws = new WebSocket(url);
        wsRef.current = ws;

        ws.onopen = () => {
          setIsConnected(true);
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            setLastEvent(data);
            setEventHistory((prev) => [data, ...prev].slice(0, 100));
          } catch {
            console.debug('Received raw text over WS:', event.data);
          }
        };

        ws.onclose = () => {
          setIsConnected(false);
          // Auto-reconnect after 2 seconds
          reconnectTimeout = setTimeout(connect, 2000);
        };

        ws.onerror = (err) => {
          console.debug('WebSocket error, disconnecting:', err);
          ws.close();
        };
      } catch (e) {
        console.debug('Failed to construct WebSocket, retrying:', e);
        reconnectTimeout = setTimeout(connect, 2500);
      }
    }

    connect();

    return () => {
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      if (wsRef.current) wsRef.current.close();
    };
  }, [url]);

  return { isConnected, lastEvent, eventHistory };
}
