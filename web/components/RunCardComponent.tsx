import { RunCard } from '../types/chat';

interface RunCardComponentProps {
  runCard: RunCard;
  className?: string;
}

export default function RunCardComponent({ runCard, className = '' }: RunCardComponentProps) {
  const statusColors = {
    queued: 'bg-yellow-50 border-yellow-200 text-yellow-800',
    running: 'bg-blue-50 border-blue-200 text-blue-800',
    done: 'bg-green-50 border-green-200 text-green-800',
    error: 'bg-red-50 border-red-200 text-red-800'
  };

  const statusIcons = {
    queued: '⏳',
    running: '⚡',
    done: '✅',
    error: '❌'
  };

  return (
    <div className={`border rounded-lg p-4 ${statusColors[runCard.status]} ${className}`}>
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-lg">{statusIcons[runCard.status]}</span>
          <code className="font-mono text-sm bg-black/10 px-2 py-1 rounded">
            {runCard.command}
          </code>
        </div>
        <span className={`px-2 py-1 text-xs font-medium rounded-full uppercase tracking-wide ${statusColors[runCard.status]}`}>
          {runCard.status}
        </span>
      </div>
      
      <div className="text-sm space-y-1">
        <div className="flex justify-between text-gray-600">
          <span>Created:</span>
          <span>{new Date(runCard.created_at).toLocaleString()}</span>
        </div>
        <div className="flex justify-between text-gray-600">
          <span>By:</span>
          <span>{runCard.created_by}</span>
        </div>
      </div>

      {Object.keys(runCard.inputs).length > 0 && (
        <div className="mt-2 pt-2 border-t border-current/20">
          <div className="text-xs font-medium mb-1">Inputs:</div>
          <div className="text-xs bg-black/10 rounded p-2 font-mono">
            {JSON.stringify(runCard.inputs, null, 2)}
          </div>
        </div>
      )}

      {runCard.outputs && (
        <div className="mt-2 pt-2 border-t border-current/20">
          <div className="text-xs font-medium mb-1">Results:</div>
          <div className="text-xs bg-black/10 rounded p-2 font-mono">
            {JSON.stringify(runCard.outputs, null, 2)}
          </div>
        </div>
      )}

      {runCard.citations && runCard.citations.length > 0 && (
        <div className="mt-2 pt-2 border-t border-current/20">
          <div className="text-xs font-medium mb-1">Citations:</div>
          <div className="text-xs space-y-1">
            {runCard.citations.map((citation, idx) => (
              <div key={idx} className="bg-black/10 rounded px-2 py-1 font-mono">
                {citation}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}