"use client";

import { useState, useEffect, useRef } from "react";

interface PriceUpdate {
  ticker: string;
  price: number;
  timestamp: number;
}

export function usePriceStream(ticker: string | undefined, initialPrice: number, asOf?: string) {
  const [currentPrice, setCurrentPrice] = useState<number>(initialPrice);
  const [lastUpdate, setLastUpdate] = useState<number | null>(asOf ? new Date(asOf).getTime() : null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    // Sync initial price if it changes from props (e.g. user asks about a different stock)
    setCurrentPrice(initialPrice);
    setLastUpdate(asOf ? new Date(asOf).getTime() : null);
  }, [initialPrice, asOf, ticker]);

  useEffect(() => {
    if (!ticker) return;

    // Use absolute URL since this runs on the client
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const wsUrl = `${apiUrl.replace(/^http/, "ws")}/api/v1/ws/prices/${encodeURIComponent(ticker)}`;

    let ws: WebSocket;
    let reconnectTimeout: NodeJS.Timeout;

    const connect = () => {
      ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as PriceUpdate;
          if (data.ticker === ticker) {
            setCurrentPrice(data.price);
            setLastUpdate(data.timestamp * 1000); // Server sends seconds, we want ms
          }
        } catch (e) {
          console.error("Failed to parse price update:", e);
        }
      };

      ws.onclose = () => {
        // Silently reconnect on drop (e.g. if the backend restarts)
        reconnectTimeout = setTimeout(connect, 3000);
      };

      ws.onerror = () => {
        // Just let onclose handle it
      };
    };

    connect();

    return () => {
      clearTimeout(reconnectTimeout);
      if (wsRef.current) {
        wsRef.current.onclose = null; // Prevent reconnect on unmount
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [ticker]);

  return { currentPrice, lastUpdate };
}
