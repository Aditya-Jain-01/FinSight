"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { checkHealth } from "@/lib/api";
import { AppNav } from "./AppNav";

export function AppHeader() {
  const [backendStatus, setBackendStatus] = useState<"checking" | "online" | "waking" | "offline">("checking");

  useEffect(() => {
    let cancelled = false;

    async function check() {
      setBackendStatus("checking");
      const start = Date.now();
      const healthy = await checkHealth();
      const elapsed = Date.now() - start;

      if (cancelled) return;

      if (healthy) {
        setBackendStatus("online");
      } else if (elapsed > 3000) {
        setBackendStatus("waking");
        
        let attempts = 0;
        const maxAttempts = 12;

        const poll = async () => {
          if (cancelled) return;
          if (attempts >= maxAttempts) {
            setBackendStatus("offline");
            return;
          }
          
          attempts++;
          const retryHealthy = await checkHealth();
          if (cancelled) return;
          
          if (retryHealthy) {
            setBackendStatus("online");
          } else {
            setTimeout(poll, 5000);
          }
        };
        
        setTimeout(poll, 5000);
      } else {
        setBackendStatus("offline");
      }
    }

    check();
    return () => { cancelled = true; };
  }, []);

  return (
    <div className="flex flex-col relative z-20">
      <header className="flex items-center justify-between px-6 py-3 bg-panel border-b border-border">
        <Link href="/" className="flex items-center gap-2 group">
          <span className="text-xl font-bold font-display text-accent">
            FinSight
          </span>
        </Link>

        {/* Backend status indicator */}
        <div className="flex items-center gap-2 font-mono text-xs">
          {backendStatus === "waking" && (
            <div className="flex items-center gap-2 text-text-secondary">
              <svg className="w-3.5 h-3.5 animate-spin text-text-muted" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Waking up (~30s)…
            </div>
          )}
          {backendStatus === "offline" && (
            <div className="flex items-center gap-2 text-loss">
              <span className="w-1.5 h-1.5 rounded-full bg-loss" />
              Backend offline
            </div>
          )}
          {backendStatus === "online" && (
            <div className="flex items-center gap-2 text-gain">
              <span className="w-1.5 h-1.5 rounded-full bg-gain animate-pulse" />
              Online
            </div>
          )}
        </div>
      </header>
      <AppNav />
    </div>
  );
}
