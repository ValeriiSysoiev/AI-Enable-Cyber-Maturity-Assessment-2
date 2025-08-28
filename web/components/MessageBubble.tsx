import { ChatMessage } from '../types/chat';

interface MessageBubbleProps {
  message: ChatMessage;
  className?: string;
}

export default function MessageBubble({ message, className = '' }: MessageBubbleProps) {
  const isUser = message.sender === 'user';
  
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4 ${className}`}>
      <div 
        className={`max-w-[70%] px-4 py-2 rounded-lg ${
          isUser 
            ? 'bg-blue-500 text-white rounded-br-sm' 
            : 'bg-gray-100 text-gray-900 rounded-bl-sm'
        }`}
      >
        <div className="whitespace-pre-wrap break-words">
          {message.message}
        </div>
        <div 
          className={`text-xs mt-1 ${
            isUser ? 'text-blue-100' : 'text-gray-500'
          }`}
        >
          {new Date(message.timestamp).toLocaleTimeString([], { 
            hour: '2-digit', 
            minute: '2-digit' 
          })}
        </div>
      </div>
    </div>
  );
}