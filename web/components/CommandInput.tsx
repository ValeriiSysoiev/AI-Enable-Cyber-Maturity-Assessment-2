'use client';

import { useState, useRef, useEffect } from 'react';
import { CommandSuggestion } from '@/types/chat';
import { getCommandSuggestions, parseCommand } from '@/lib/chat';

interface CommandInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
  className?: string;
}

export default function CommandInput({ 
  onSend, 
  disabled = false, 
  placeholder = "Type a message or use /command...",
  className = '' 
}: CommandInputProps) {
  const [message, setMessage] = useState('');
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [selectedSuggestion, setSelectedSuggestion] = useState(-1);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const suggestions = getCommandSuggestions();

  // Filter suggestions based on input
  const filteredSuggestions = message.startsWith('/')
    ? suggestions.filter(s => s.command.startsWith(message.split(' ')[0]))
    : [];

  useEffect(() => {
    setShowSuggestions(filteredSuggestions.length > 0 && message.startsWith('/'));
    setSelectedSuggestion(-1);
  }, [message, filteredSuggestions.length]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (showSuggestions && filteredSuggestions.length > 0) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedSuggestion(prev => 
          prev < filteredSuggestions.length - 1 ? prev + 1 : 0
        );
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedSuggestion(prev => 
          prev > 0 ? prev - 1 : filteredSuggestions.length - 1
        );
      } else if (e.key === 'Tab') {
        e.preventDefault();
        if (selectedSuggestion >= 0) {
          setMessage(filteredSuggestions[selectedSuggestion].example);
          setShowSuggestions(false);
        }
      }
    }

    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSend = () => {
    const trimmed = message.trim();
    if (trimmed && !disabled) {
      onSend(trimmed);
      setMessage('');
      setShowSuggestions(false);
    }
  };

  const selectSuggestion = (suggestion: CommandSuggestion) => {
    setMessage(suggestion.example);
    setShowSuggestions(false);
    inputRef.current?.focus();
  };

  const isCommand = parseCommand(message) !== null;

  return (
    <div className={`relative ${className}`}>
      {/* Suggestions dropdown */}
      {showSuggestions && filteredSuggestions.length > 0 && (
        <div className="absolute bottom-full mb-2 w-full bg-white border border-gray-200 rounded-lg shadow-lg z-10">
          {filteredSuggestions.map((suggestion, idx) => (
            <button
              key={suggestion.command}
              onClick={() => selectSuggestion(suggestion)}
              className={`w-full text-left px-4 py-3 hover:bg-gray-50 first:rounded-t-lg last:rounded-b-lg ${
                idx === selectedSuggestion ? 'bg-blue-50 border-r-2 border-blue-500' : ''
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <div className="font-mono font-medium text-blue-600">
                    {suggestion.command}
                  </div>
                  <div className="text-sm text-gray-600">
                    {suggestion.description}
                  </div>
                </div>
                <div className="text-xs text-gray-400 ml-2">
                  Tab to use
                </div>
              </div>
              <div className="text-xs text-gray-500 font-mono mt-1">
                {suggestion.example}
              </div>
            </button>
          ))}
        </div>
      )}

      {/* Input area */}
      <div className="flex gap-2">
        <div className="flex-1 relative">
          <textarea
            ref={inputRef}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            placeholder={placeholder}
            rows={1}
            className={`w-full px-4 py-3 border border-gray-300 rounded-lg resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
              isCommand ? 'border-blue-300 bg-blue-50' : ''
            } ${disabled ? 'opacity-50' : ''}`}
            style={{
              minHeight: '48px',
              maxHeight: '120px'
            }}
          />
          {isCommand && (
            <div className="absolute top-1 right-1 px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded font-medium">
              COMMAND
            </div>
          )}
        </div>
        <button
          onClick={handleSend}
          disabled={disabled || !message.trim()}
          className="px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          Send
        </button>
      </div>

      {/* Command hint */}
      {message.startsWith('/') && !showSuggestions && (
        <div className="mt-1 text-sm text-gray-500">
          Available commands: /ingest, /minutes, /score
        </div>
      )}
    </div>
  );
}