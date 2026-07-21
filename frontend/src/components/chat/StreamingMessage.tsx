"use client";

/**
 * StreamingMessage is a thin wrapper — the actual streaming state
 * is managed by useChat and rendered through MessageBubble's
 * isStreaming prop. This component exists for potential future
 * enhancements (e.g., progressive rendering, markdown parsing).
 */

import { ChatMessage } from "@/hooks/useChat";
import { MessageBubble } from "./MessageBubble";

interface StreamingMessageProps {
  message: ChatMessage;
}

export function StreamingMessage({ message }: StreamingMessageProps) {
  return <MessageBubble message={message} />;
}
