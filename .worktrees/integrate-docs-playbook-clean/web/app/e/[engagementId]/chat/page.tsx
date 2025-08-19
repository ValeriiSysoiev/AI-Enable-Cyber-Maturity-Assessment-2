'use client';

import { useEffect, useState, useRef } from 'react';
import { useParams } from 'next/navigation';
import { ChatMessage, RunCard } from '@/types/chat';
import { sendMessage, getChatMessages, RunCardPoller } from '@/lib/chat';
import { useRequireAuth } from '@/components/AuthProvider';
import MessageBubble from '@/components/MessageBubble';
import RunCardComponent from '@/components/RunCardComponent';
import CommandInput from '@/components/CommandInput';

export default function ChatPage() {
  const { engagementId } = useParams<{ engagementId: string }>();
  const auth = useRequireAuth();
  
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [runCards, setRunCards] = useState<RunCard[]>([]);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string>('');
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const pollerRef = useRef<RunCardPoller | null>(null);

  // Scroll to bottom when messages update
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Load initial data
  useEffect(() => {
    if (!engagementId || auth.isLoading) return;

    const loadChatData = async () => {
      try {
        setLoading(true);
        const [messagesResponse] = await Promise.all([
          getChatMessages(engagementId, 1, 50)
        ]);
        
        setMessages(messagesResponse.messages.reverse()); // Show oldest first
        
        // Initialize RunCard poller
        pollerRef.current = new RunCardPoller(engagementId);
        pollerRef.current.onUpdate(setRunCards);
        pollerRef.current.start();
        
      } catch (err: any) {
        setError(err.message || 'Failed to load chat data');
      } finally {
        setLoading(false);
      }
    };

    loadChatData();

    // Cleanup poller on unmount
    return () => {
      if (pollerRef.current) {
        pollerRef.current.stop();
      }
    };
  }, [engagementId, auth.isLoading]);

  const handleSendMessage = async (messageText: string) => {
    if (!engagementId || sending) return;

    try {
      setSending(true);
      setError('');
      
      const newMessage = await sendMessage(engagementId, messageText);
      setMessages(prev => [...prev, newMessage]);
      
    } catch (err: any) {
      setError(err.message || 'Failed to send message');
    } finally {
      setSending(false);
    }
  };

  if (auth.isLoading || loading) {
    return (
      <div className="p-6">
        <div className="text-center">Loading chat...</div>
      </div>
    );
  }

  if (!engagementId) {
    return <div className="p-6">No engagement selected.</div>;
  }

  // Group RunCards by status for display
  const activeRunCards = runCards.filter(rc => ['queued', 'running'].includes(rc.status));
  const completedRunCards = runCards.filter(rc => ['done', 'error'].includes(rc.status));

  return (
    <div className="flex flex-col h-screen max-h-screen">
      {/* Header */}
      <div className="px-6 py-4 border-b bg-white">
        <h1 className="text-2xl font-semibold">Chat Shell</h1>
        <p className="text-sm text-gray-600">
          Send messages or use commands like <code className="bg-gray-100 px-1 rounded">/ingest docs</code>
        </p>
      </div>

      {/* Main chat area */}
      <div className="flex-1 flex gap-6 p-6 overflow-hidden">
        {/* Messages section */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Messages container */}
          <div className="flex-1 overflow-y-auto mb-4 border rounded-lg bg-gray-50 p-4">
            {error && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg">
                {error}
              </div>
            )}
            
            {messages.length === 0 && !error && (
              <div className="text-center text-gray-500 py-8">
                <p>No messages yet. Start a conversation!</p>
                <p className="text-sm mt-2">Try: <code className="bg-gray-200 px-1 rounded">/ingest docs</code></p>
              </div>
            )}
            
            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}
            
            <div ref={messagesEndRef} />
          </div>

          {/* Command input */}
          <CommandInput
            onSend={handleSendMessage}
            disabled={sending}
            placeholder={sending ? "Sending..." : "Type a message or use /command..."}
          />
        </div>

        {/* RunCards sidebar */}
        <div className="w-80 flex flex-col gap-4">
          {/* Active RunCards */}
          {activeRunCards.length > 0 && (
            <div>
              <h3 className="font-medium text-gray-900 mb-2">Active Commands</h3>
              <div className="space-y-2">
                {activeRunCards.map((runCard) => (
                  <RunCardComponent key={runCard.id} runCard={runCard} />
                ))}
              </div>
            </div>
          )}

          {/* Completed RunCards */}
          {completedRunCards.length > 0 && (
            <div>
              <h3 className="font-medium text-gray-900 mb-2">Recent Results</h3>
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {completedRunCards.slice(0, 5).map((runCard) => (
                  <RunCardComponent key={runCard.id} runCard={runCard} />
                ))}
              </div>
            </div>
          )}

          {/* Empty state */}
          {runCards.length === 0 && (
            <div className="text-center text-gray-500 py-8">
              <p className="text-sm">No commands executed yet.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}