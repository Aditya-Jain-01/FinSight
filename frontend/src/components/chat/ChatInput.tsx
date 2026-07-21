"use client";

import { useState, useRef, useEffect } from "react";

interface ChatInputProps {
  onSend: (content: string) => void;
  disabled?: boolean;
}

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    const ta = textareaRef.current;
    if (ta) {
      ta.style.height = "auto";
      ta.style.height = `${Math.min(ta.scrollHeight, 160)}px`;
    }
  }, [value]);

  const handleSend = () => {
    if (!value.trim() || disabled) return;
    onSend(value.trim());
    setValue("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="border-t bg-panel p-4 relative z-10"
         style={{ borderColor: "var(--border)" }}>
      <div className="flex items-end gap-3 max-w-3xl mx-auto">
        <div className="flex-1 rounded-lg p-1 transition-colors bg-panel"
             style={{ border: "1px solid var(--border)" }}>
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about any US or Indian stock…"
            disabled={disabled}
            rows={1}
            id="chat-input"
            className="w-full bg-transparent resize-none text-base px-3 py-2.5 focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed"
            style={{
              color: "var(--text-primary)",
              fontFamily: "var(--font-body)",
            }}
          />
        </div>

        <button
          onClick={handleSend}
          disabled={disabled || !value.trim()}
          id="send-button"
          className="p-3 rounded-lg flex-shrink-0 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          style={{
            background: "var(--accent)",
            color: "#fff",
          }}
          aria-label="Send message"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5}
              d="M12 19V5m0 0l-7 7m7-7l7 7" />
          </svg>
        </button>
      </div>
    </div>
  );
}
