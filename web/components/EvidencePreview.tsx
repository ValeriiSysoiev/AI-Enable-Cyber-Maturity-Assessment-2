"use client";
import { useState, useCallback } from "react";
import { linkEvidence, formatFileSize, getFileIcon } from "@/lib/evidence";
import type { Evidence } from "@/types/evidence";

interface EvidencePreviewProps {
  evidence: Evidence | null;
  onClose?: () => void;
  onLinked?: () => void;
  className?: string;
}

export default function EvidencePreview({ 
  evidence, 
  onClose, 
  onLinked,
  className = "" 
}: EvidencePreviewProps) {
  const [linkForm, setLinkForm] = useState({ itemType: '', itemId: '' });
  const [linking, setLinking] = useState(false);
  const [linkError, setLinkError] = useState<string | null>(null);

  const handleLink = useCallback(async () => {
    if (!evidence || !linkForm.itemType.trim() || !linkForm.itemId.trim()) return;

    setLinking(true);
    setLinkError(null);

    try {
      await linkEvidence(evidence.id, {
        item_type: linkForm.itemType.trim(),
        item_id: linkForm.itemId.trim()
      });

      setLinkForm({ itemType: '', itemId: '' });
      onLinked?.();
    } catch (err) {
      setLinkError(err instanceof Error ? err.message : 'Failed to create link');
    } finally {
      setLinking(false);
    }
  }, [evidence, linkForm, onLinked]);

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getPreviewContent = () => {
    if (!evidence) return null;

    const isImage = evidence.mime_type.startsWith('image/');
    const isPDF = evidence.mime_type.includes('pdf');
    const isText = evidence.mime_type.startsWith('text/');

    if (isImage) {
      return (
        <div className="flex items-center justify-center h-64 bg-gray-50 rounded border-2 border-dashed border-gray-300">
          <div className="text-center">
            <div className="text-4xl mb-2">🖼️</div>
            <div className="text-sm text-gray-600">Image Preview</div>
            <div className="text-xs text-gray-500 mt-1">
              Preview functionality coming soon
            </div>
          </div>
        </div>
      );
    }

    if (isPDF) {
      return (
        <div className="flex items-center justify-center h-64 bg-gray-50 rounded border-2 border-dashed border-gray-300">
          <div className="text-center">
            <div className="text-4xl mb-2">📄</div>
            <div className="text-sm text-gray-600">PDF Document</div>
            <div className="text-xs text-gray-500 mt-1">
              PDF viewer coming soon
            </div>
          </div>
        </div>
      );
    }

    if (isText) {
      return (
        <div className="flex items-center justify-center h-64 bg-gray-50 rounded border-2 border-dashed border-gray-300">
          <div className="text-center">
            <div className="text-4xl mb-2">📄</div>
            <div className="text-sm text-gray-600">Text Document</div>
            <div className="text-xs text-gray-500 mt-1">
              Text preview coming soon
            </div>
          </div>
        </div>
      );
    }

    return (
      <div className="flex items-center justify-center h-64 bg-gray-50 rounded border-2 border-dashed border-gray-300">
        <div className="text-center">
          <div className="text-4xl mb-2">{getFileIcon(evidence.mime_type)}</div>
          <div className="text-sm text-gray-600">File Preview</div>
          <div className="text-xs text-gray-500 mt-1">
            Preview not available for this file type
          </div>
        </div>
      </div>
    );
  };

  if (!evidence) {
    return (
      <div className={`${className}`}>
        <div className="flex items-center justify-center h-96 bg-gray-50 rounded border-2 border-dashed border-gray-300">
          <div className="text-center">
            <div className="text-4xl mb-2">📂</div>
            <div className="text-gray-600">Select an evidence file to preview</div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Evidence Preview</h3>
        {onClose && (
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            ✕
          </button>
        )}
      </div>

      {/* File Info */}
      <div className="bg-gray-50 rounded-lg p-4">
        <div className="flex items-start gap-4">
          <div className="text-3xl">{getFileIcon(evidence.mime_type)}</div>
          <div className="flex-1 min-w-0">
            <h4 className="text-lg font-medium text-gray-900 truncate">
              {evidence.filename}
            </h4>
            <div className="grid grid-cols-2 gap-4 mt-2 text-sm text-gray-600">
              <div>
                <span className="font-medium">Size:</span> {formatFileSize(evidence.size)}
              </div>
              <div>
                <span className="font-medium">Type:</span> {evidence.mime_type}
              </div>
              <div>
                <span className="font-medium">Uploaded:</span> {formatDate(evidence.uploaded_at)}
              </div>
              <div>
                <span className="font-medium">By:</span> {evidence.uploaded_by}
              </div>
            </div>
            
            {evidence.pii_flag && (
              <div className="mt-2 inline-flex items-center px-2 py-1 text-xs bg-orange-100 text-orange-700 rounded">
                ⚠️ Potential PII detected
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Preview Content */}
      {getPreviewContent()}

      {/* Links Section */}
      <div className="space-y-3">
        <h4 className="font-medium text-gray-900">Linked Items</h4>
        
        {evidence.linked_items.length === 0 ? (
          <div className="text-sm text-gray-500 italic">No linked items</div>
        ) : (
          <div className="space-y-2">
            {evidence.linked_items.map((link, index) => (
              <div key={index} className="flex items-center justify-between bg-blue-50 rounded px-3 py-2">
                <div className="text-sm">
                  <span className="font-medium">{link.item_type}:</span> {link.item_id}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Add Link Form */}
        <div className="border-t pt-3">
          <h5 className="text-sm font-medium text-gray-700 mb-2">Add New Link</h5>
          <div className="space-y-2">
            <div className="grid grid-cols-2 gap-2">
              <input
                type="text"
                placeholder="Item type (e.g., assessment)"
                value={linkForm.itemType}
                onChange={(e) => setLinkForm(prev => ({ ...prev, itemType: e.target.value }))}
                disabled={linking}
                className="px-3 py-2 border rounded text-sm"
              />
              <input
                type="text"
                placeholder="Item ID"
                value={linkForm.itemId}
                onChange={(e) => setLinkForm(prev => ({ ...prev, itemId: e.target.value }))}
                disabled={linking}
                className="px-3 py-2 border rounded text-sm"
              />
            </div>
            
            {linkError && (
              <div className="text-sm text-red-600">{linkError}</div>
            )}
            
            <button
              onClick={handleLink}
              disabled={linking || !linkForm.itemType.trim() || !linkForm.itemId.trim()}
              className="w-full px-3 py-2 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {linking ? 'Creating Link...' : 'Add Link'}
            </button>
          </div>
        </div>
      </div>

      {/* Metadata */}
      <div className="border-t pt-4">
        <h4 className="font-medium text-gray-900 mb-2">File Metadata</h4>
        <div className="grid grid-cols-1 gap-2 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-600">Evidence ID:</span>
            <span className="font-mono text-xs">{evidence.id}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">Checksum (SHA-256):</span>
            <span 
              className="font-mono text-xs cursor-pointer hover:bg-gray-100 px-1 rounded"
              onClick={() => {
                navigator.clipboard.writeText(evidence.checksum_sha256);
                alert('Checksum copied to clipboard');
              }}
              title="Click to copy"
            >
              {evidence.checksum_sha256.substring(0, 16)}...
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">Blob Path:</span>
            <span className="font-mono text-xs text-gray-500 truncate max-w-xs">
              {evidence.blob_path}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}