'use client';

import { useState, useEffect, useRef } from 'react';

interface ChatMessage {
  message_id: string;
  design_id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
}

interface ChatPanelProps {
  designId: string;
  onReadyToRender: (refinedPrompt: string) => void;
}

export default function ChatPanel({ designId, onReadyToRender }: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  useEffect(() => {
    const loadHistory = async () => {
      try {
        const response = await fetch(`${apiUrl}/api/chat/${designId}/messages`);
        if (!response.ok) {
          throw new Error(`Failed to load chat history (${response.status})`);
        }
        const data = await response.json();
        setMessages(data.messages || []);
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Failed to load chat history';
        setError(msg);
      }
    };

    loadHistory();
  }, [designId, apiUrl]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async () => {
    const trimmed = input.trim();
    if (!trimmed || loading) return;

    setError(null);
    setInput('');
    setLoading(true);

    const tempId = `temp-${Date.now()}`;
    const userMessage: ChatMessage = {
      message_id: tempId,
      design_id: designId,
      role: 'user',
      content: trimmed,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);

    try {
      const response = await fetch(`${apiUrl}/api/chat/${designId}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: trimmed }),
      });

      if (!response.ok) {
        let detail = `Server error (${response.status})`;
        try {
          const body = await response.json();
          if (body && body.detail) {
            detail = body.detail;
          }
        } catch {
          detail = `Server error: ${response.status} ${response.statusText}`;
        }
        throw new Error(detail);
      }

      const data = await response.json();

      const assistantMessage: ChatMessage = {
        message_id: data.message.message_id,
        design_id: data.message.design_id,
        role: 'assistant',
        content: data.message.content,
        created_at: data.message.created_at,
      };
      setMessages((prev) => [...prev, assistantMessage]);

      if (data.ready_to_render && data.refined_prompt) {
        onReadyToRender(data.refined_prompt);
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to send message';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="card flex flex-col h-full">
      {/* Header */}
      <div className="pb-4 border-b border-neutral-200">
        <h3 className="text-xl font-display font-bold text-neutral-900">
          Design Refinement Chat
        </h3>
        <p className="text-sm text-neutral-500 mt-1">
          Describe changes to refine your design. When you&apos;re done, say &quot;generate it&quot; or &quot;render it&quot; to create the final visualization.
        </p>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm flex items-center justify-between">
          <span>{error}</span>
          <button
            onClick={() => setError(null)}
            className="ml-2 text-red-500 hover:text-red-700"
            aria-label="Dismiss error"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      )}

      {/* Messages Area */}
      <div
        ref={messagesContainerRef}
        className="flex-1 overflow-y-auto py-4 space-y-3 min-h-[200px] max-h-[400px]"
      >
        {messages.length === 0 && !loading && (
          <div className="flex items-center justify-center h-full text-neutral-400 text-sm">
            Start a conversation to refine your design
          </div>
        )}

        {messages.map((msg) => (
          <div
            key={msg.message_id}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] px-4 py-2.5 rounded-2xl text-sm leading-relaxed ${
                msg.role === 'user'
                  ? 'bg-blue-500 text-white rounded-br-md'
                  : 'bg-gray-100 text-gray-900 rounded-bl-md'
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 text-gray-500 px-4 py-2.5 rounded-2xl rounded-bl-md text-sm">
              <span className="inline-flex items-center gap-1">
                <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="pt-3 border-t border-neutral-200">
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Describe design changes..."
            disabled={loading}
            className="flex-1 px-4 py-2.5 border border-neutral-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent disabled:opacity-50 disabled:bg-neutral-50"
          />
          <button
            onClick={sendMessage}
            disabled={loading || !input.trim()}
            className="px-4 py-2.5 bg-primary-600 text-white rounded-xl text-sm font-medium hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            aria-label="Send message"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
