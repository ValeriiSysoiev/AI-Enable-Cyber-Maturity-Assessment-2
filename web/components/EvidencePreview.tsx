"use client";
import { useState, useCallback } from "react";
import { linkEvidence, formatFileSize, getFileIcon } from "../lib/evidence";
import type { Evidence } from "../types/evidence";

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
    const isDocument = evidence.mime_type.includes('document') || evidence.mime_type.includes('word');
    const isSpreadsheet = evidence.mime_type.includes('sheet') || evidence.mime_type.includes('excel');
    const isPresentation = evidence.mime_type.includes('presentation') || evidence.mime_type.includes('powerpoint');

    if (isImage) {
      return (
        <div className="bg-gray-50 rounded-lg border-2 border-dashed border-gray-300 p-6">
          <div className="text-center mb-4">
            <div className="text-4xl mb-2">🖼️</div>
            <div className="text-sm font-medium text-gray-700">Image File</div>
            <div className="text-xs text-gray-500 mt-1">
              Visual content preview - Enhanced viewer coming soon
            </div>
          </div>
          <div className="bg-white rounded p-4 border">
            <div className="text-xs text-gray-600 space-y-1">
              <div><strong>Type:</strong> {evidence.mime_type}</div>
              <div><strong>Resolution:</strong> Preview will show actual dimensions</div>
              <div><strong>Color Space:</strong> Will display color profile information</div>
              <div><strong>Usage:</strong> Can be linked to assessment questions for evidence</div>
            </div>
          </div>
        </div>
      );
    }

    if (isPDF) {
      return (
        <div className="bg-gray-50 rounded-lg border-2 border-dashed border-gray-300 p-6">
          <div className="text-center mb-4">
            <div className="text-4xl mb-2">📄</div>
            <div className="text-sm font-medium text-gray-700">PDF Document</div>
            <div className="text-xs text-gray-500 mt-1">
              Document viewer with text search - Enhanced PDF viewer coming soon
            </div>
          </div>
          <div className="bg-white rounded p-4 border space-y-3">
            <div className="text-xs text-gray-600">
              <div><strong>Features Coming:</strong></div>
              <ul className="list-disc list-inside mt-1 space-y-1">
                <li>Page-by-page navigation</li>
                <li>Text search and highlighting</li>
                <li>Zoom and pan controls</li>
                <li>Annotation and markup tools</li>
                <li>Direct citation linking</li>
              </ul>
            </div>
          </div>
        </div>
      );
    }

    if (isDocument) {
      return (
        <div className="bg-gray-50 rounded-lg border-2 border-dashed border-gray-300 p-6">
          <div className="text-center mb-4">
            <div className="text-4xl mb-2">📝</div>
            <div className="text-sm font-medium text-gray-700">Word Document</div>
            <div className="text-xs text-gray-500 mt-1">
              Rich document viewer with formatting - Enhanced viewer coming soon
            </div>
          </div>
          <div className="bg-white rounded p-4 border">
            <div className="text-xs text-gray-600 space-y-2">
              <div><strong>Content Preview:</strong> Will show formatted text, tables, and images</div>
              <div><strong>Search:</strong> Full-text search with context highlighting</div>
              <div><strong>Navigation:</strong> Section and heading-based navigation</div>
              <div><strong>Linking:</strong> Link specific paragraphs to assessment items</div>
            </div>
          </div>
        </div>
      );
    }

    if (isSpreadsheet) {
      return (
        <div className="bg-gray-50 rounded-lg border-2 border-dashed border-gray-300 p-6">
          <div className="text-center mb-4">
            <div className="text-4xl mb-2">📊</div>
            <div className="text-sm font-medium text-gray-700">Spreadsheet</div>
            <div className="text-xs text-gray-500 mt-1">
              Interactive data viewer - Enhanced spreadsheet viewer coming soon
            </div>
          </div>
          <div className="bg-white rounded p-4 border">
            <div className="text-xs text-gray-600 space-y-2">
              <div><strong>Data View:</strong> Will display worksheets with filtering and sorting</div>
              <div><strong>Charts:</strong> Embedded charts and graphs will be rendered</div>
              <div><strong>Export:</strong> Extract specific data ranges for evidence</div>
              <div><strong>Analysis:</strong> Quick statistics and data validation</div>
            </div>
          </div>
        </div>
      );
    }

    if (isPresentation) {
      return (
        <div className="bg-gray-50 rounded-lg border-2 border-dashed border-gray-300 p-6">
          <div className="text-center mb-4">
            <div className="text-4xl mb-2">🎯</div>
            <div className="text-sm font-medium text-gray-700">Presentation</div>
            <div className="text-xs text-gray-500 mt-1">
              Slide viewer with thumbnails - Enhanced presentation viewer coming soon
            </div>
          </div>
          <div className="bg-white rounded p-4 border">
            <div className="text-xs text-gray-600 space-y-2">
              <div><strong>Slides:</strong> Will show thumbnail grid and slide-by-slide view</div>
              <div><strong>Content:</strong> Text extraction and image preview</div>
              <div><strong>Navigation:</strong> Quick jump to specific slides</div>
              <div><strong>Evidence:</strong> Link individual slides to assessment questions</div>
            </div>
          </div>
        </div>
      );
    }

    if (isText) {
      return (
        <div className="bg-gray-50 rounded-lg border-2 border-dashed border-gray-300 p-6">
          <div className="text-center mb-4">
            <div className="text-4xl mb-2">📄</div>
            <div className="text-sm font-medium text-gray-700">Text Document</div>
            <div className="text-xs text-gray-500 mt-1">
              Syntax-highlighted text viewer - Enhanced text viewer coming soon
            </div>
          </div>
          <div className="bg-white rounded p-4 border">
            <div className="text-xs text-gray-600 space-y-2">
              <div><strong>Display:</strong> Will show formatted text with line numbers</div>
              <div><strong>Search:</strong> Pattern matching and regex support</div>
              <div><strong>Highlighting:</strong> Syntax highlighting for code files</div>
              <div><strong>Selection:</strong> Quote specific lines for evidence</div>
            </div>
          </div>
        </div>
      );
    }

    return (
      <div className="bg-gray-50 rounded-lg border-2 border-dashed border-gray-300 p-6">
        <div className="text-center mb-4">
          <div className="text-4xl mb-2">{getFileIcon(evidence.mime_type)}</div>
          <div className="text-sm font-medium text-gray-700">File Preview</div>
          <div className="text-xs text-gray-500 mt-1">
            Specialized viewer for this file type - Enhanced preview coming soon
          </div>
        </div>
        <div className="bg-white rounded p-4 border">
          <div className="text-xs text-gray-600 space-y-2">
            <div><strong>Type:</strong> {evidence.mime_type}</div>
            <div><strong>Preview:</strong> Custom viewer will be developed for this file type</div>
            <div><strong>Download:</strong> Full file access available through secure download</div>
            <div><strong>Metadata:</strong> File properties and embedded information will be extracted</div>
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
      <div className="bg-white border rounded-lg">
        <div className="border-b px-4 py-3">
          <h4 className="font-medium text-gray-900">File Preview</h4>
          <p className="text-sm text-gray-600 mt-1">
            Preview capabilities are being enhanced. Current view shows file structure and planned features.
          </p>
        </div>
        <div className="p-4">
          {getPreviewContent()}
        </div>
      </div>

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