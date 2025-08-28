"use client";
import { useState, useEffect, useCallback } from "react";
import { useParams } from "next/navigation";
import {
  listEvidence,
  linkEvidence,
  unlinkEvidence,
  formatFileSize,
  getFileIcon
} from "../lib/evidence";
import type { Evidence, EvidenceListResponse } from "../types/evidence";

interface EvidenceTableProps {
  onEvidenceSelect?: (evidence: Evidence) => void;
  refreshTrigger?: number;
  className?: string;
  showLinkActions?: boolean;
}

export default function EvidenceTable({ 
  onEvidenceSelect, 
  refreshTrigger = 0,
  className = "",
  showLinkActions = false
}: EvidenceTableProps) {
  const { engagementId } = useParams<{ engagementId: string }>();
  const [evidenceData, setEvidenceData] = useState<EvidenceListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [linkingEvidence, setLinkingEvidence] = useState<string | null>(null);
  const [showLinkDialog, setShowLinkDialog] = useState<string | null>(null);
  const [linkForm, setLinkForm] = useState({ itemType: 'assessment', itemId: '' });

  const loadEvidence = useCallback(async () => {
    if (!engagementId) return;

    setLoading(true);
    setError(null);

    try {
      const data = await listEvidence(engagementId, currentPage, pageSize);
      setEvidenceData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load evidence');
    } finally {
      setLoading(false);
    }
  }, [engagementId, currentPage, pageSize]);

  // Load evidence on mount and when dependencies change
  useEffect(() => {
    loadEvidence();
  }, [loadEvidence, refreshTrigger]);

  const handlePageChange = useCallback((page: number) => {
    setCurrentPage(page);
  }, []);

  const handlePageSizeChange = useCallback((newPageSize: number) => {
    setPageSize(newPageSize);
    setCurrentPage(1); // Reset to first page
  }, []);

  const handleUnlink = useCallback(async (evidenceId: string, linkType: string, linkId: string) => {
    if (!confirm('Remove this link?')) return;

    setLinkingEvidence(evidenceId);
    try {
      await unlinkEvidence(evidenceId, `${linkType}:${linkId}`);
      await loadEvidence(); // Refresh the table
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to unlink evidence');
    } finally {
      setLinkingEvidence(null);
    }
  }, [loadEvidence]);

  const handleCreateLink = useCallback(async (evidenceId: string) => {
    if (!linkForm.itemType.trim() || !linkForm.itemId.trim()) {
      alert('Please enter both item type and item ID');
      return;
    }

    setLinkingEvidence(evidenceId);
    try {
      await linkEvidence(evidenceId, {
        item_type: linkForm.itemType.trim(),
        item_id: linkForm.itemId.trim()
      });
      setShowLinkDialog(null);
      setLinkForm({ itemType: 'assessment', itemId: '' });
      await loadEvidence(); // Refresh the table
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to create link');
    } finally {
      setLinkingEvidence(null);
    }
  }, [linkForm, loadEvidence]);

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const renderPaginationInfo = () => {
    if (!evidenceData) return null;
    
    const { total, page, page_size } = evidenceData;
    const start = (page - 1) * page_size + 1;
    const end = Math.min(page * page_size, total);
    
    return (
      <div className="text-sm text-gray-600">
        Showing {start}-{end} of {total} evidence files
      </div>
    );
  };

  const renderPaginationControls = () => {
    if (!evidenceData) return null;
    
    const { page, total_pages, has_previous, has_next } = evidenceData;
    
    return (
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-600">Items per page:</span>
          <select
            value={pageSize}
            onChange={(e) => handlePageSizeChange(Number(e.target.value))}
            className="border rounded px-2 py-1 text-sm"
          >
            <option value={10}>10</option>
            <option value={20}>20</option>
            <option value={50}>50</option>
            <option value={100}>100</option>
          </select>
        </div>
        
        <div className="flex items-center gap-2">
          <button
            onClick={() => handlePageChange(1)}
            disabled={!has_previous}
            className="px-2 py-1 text-sm border rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
          >
            ««
          </button>
          <button
            onClick={() => handlePageChange(page - 1)}
            disabled={!has_previous}
            className="px-2 py-1 text-sm border rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
          >
            ‹
          </button>
          
          <span className="text-sm text-gray-600">
            Page {page} of {total_pages}
          </span>
          
          <button
            onClick={() => handlePageChange(page + 1)}
            disabled={!has_next}
            className="px-2 py-1 text-sm border rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
          >
            ›
          </button>
          <button
            onClick={() => handlePageChange(total_pages)}
            disabled={!has_next}
            className="px-2 py-1 text-sm border rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
          >
            »»
          </button>
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className={`${className}`} role="status" aria-live="polite">
        <div className="flex items-center justify-center py-8">
          <div className="flex items-center gap-3">
            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600"></div>
            <div className="text-gray-600">Loading evidence...</div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`${className}`} role="alert" aria-live="assertive">
        <div className="flex items-center justify-center py-8">
          <div className="text-red-600 flex items-center gap-2">
            <span className="text-xl">⚠️</span>
            <span>Error: {error}</span>
          </div>
        </div>
      </div>
    );
  }

  if (!evidenceData || evidenceData.data.length === 0) {
    return (
      <div className={`${className}`} role="status">
        <div className="flex flex-col items-center justify-center py-12">
          <div className="text-4xl mb-4" aria-hidden="true">📂</div>
          <div className="text-gray-600 mb-2">No evidence files found</div>
          <div className="text-sm text-gray-500">Upload files to see them here</div>
        </div>
      </div>
    );
  }

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Table Header with Pagination Info */}
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold">Evidence Files</h3>
        {renderPaginationInfo()}
      </div>

      {/* Evidence Table */}
      <div className="overflow-hidden rounded-lg border">
        <table className="w-full" role="table" aria-label="Evidence files list">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                File
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Size
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Uploaded
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Links
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {evidenceData.data.map((evidence) => (
              <tr 
                key={evidence.id} 
                className="hover:bg-gray-50 cursor-pointer"
                onClick={() => onEvidenceSelect?.(evidence)}
                role="row"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    onEvidenceSelect?.(evidence);
                  }
                }}
                aria-label={`Evidence file ${evidence.filename}`}
              >
                <td className="px-4 py-4">
                  <div className="flex items-center">
                    <span className="text-lg mr-3">{getFileIcon(evidence.mime_type)}</span>
                    <div>
                      <div className="text-sm font-medium text-gray-900 truncate max-w-xs">
                        {evidence.filename}
                      </div>
                      <div className="text-xs text-gray-500">
                        {evidence.mime_type}
                      </div>
                    </div>
                  </div>
                </td>
                <td className="px-4 py-4 text-sm text-gray-600">
                  {formatFileSize(evidence.size)}
                </td>
                <td className="px-4 py-4 text-sm text-gray-600">
                  <div>{formatDate(evidence.uploaded_at)}</div>
                  <div className="text-xs text-gray-500">by {evidence.uploaded_by}</div>
                </td>
                <td className="px-4 py-4">
                  <div className="flex flex-wrap gap-1">
                    {evidence.linked_items.length === 0 ? (
                      <span className="text-xs text-gray-500">No links</span>
                    ) : (
                      evidence.linked_items.map((link, index) => (
                        <span
                          key={index}
                          className="inline-flex items-center gap-1 px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded"
                        >
                          {link.item_type}:{link.item_id.substring(0, 8)}...
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleUnlink(evidence.id, link.item_type, link.item_id);
                            }}
                            disabled={linkingEvidence === evidence.id}
                            className="ml-1 text-red-500 hover:text-red-700 disabled:opacity-50"
                            title="Remove link"
                          >
                            ×
                          </button>
                        </span>
                      ))
                    )}
                  </div>
                </td>
                <td className="px-4 py-4">
                  <div className="flex items-center gap-2">
                    <span className="inline-flex items-center px-2 py-1 text-xs font-medium bg-green-100 text-green-700 rounded">
                      ✓ Uploaded
                    </span>
                    {evidence.pii_flag && (
                      <span className="inline-flex items-center px-2 py-1 text-xs font-medium bg-orange-100 text-orange-700 rounded">
                        ⚠️ PII
                      </span>
                    )}
                  </div>
                </td>
                <td className="px-4 py-4">
                  <div className="flex items-center gap-2">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onEvidenceSelect?.(evidence);
                      }}
                      className="text-blue-600 hover:text-blue-800 text-sm"
                      aria-label="View evidence details"
                    >
                      View
                    </button>
                    {showLinkActions && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setShowLinkDialog(evidence.id);
                        }}
                        className="text-green-600 hover:text-green-800 text-sm"
                        aria-label="Link to item"
                        disabled={linkingEvidence === evidence.id}
                      >
                        🔗 Link
                      </button>
                    )}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        navigator.clipboard.writeText(evidence.checksum_sha256);
                        alert('Checksum copied to clipboard');
                      }}
                      className="text-gray-600 hover:text-gray-800 text-sm"
                      title="Copy checksum"
                      aria-label="Copy checksum"
                    >
                      📋
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination Controls */}
      <div className="flex justify-between items-center">
        {renderPaginationControls()}
      </div>

      {/* Link Dialog */}
      {showLinkDialog && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold mb-4">Link Evidence to Item</h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Item Type
                </label>
                <select
                  value={linkForm.itemType}
                  onChange={(e) => setLinkForm(prev => ({ ...prev, itemType: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  disabled={linkingEvidence === showLinkDialog}
                >
                  <option value="assessment">Assessment</option>
                  <option value="question">Question</option>
                  <option value="framework">Framework</option>
                  <option value="control">Control</option>
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Item ID
                </label>
                <input
                  type="text"
                  value={linkForm.itemId}
                  onChange={(e) => setLinkForm(prev => ({ ...prev, itemId: e.target.value }))}
                  placeholder="Enter the ID of the item to link to"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  disabled={linkingEvidence === showLinkDialog}
                />
              </div>
            </div>
            
            <div className="flex gap-3 mt-6">
              <button
                onClick={() => handleCreateLink(showLinkDialog)}
                disabled={linkingEvidence === showLinkDialog}
                className="flex-1 px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {linkingEvidence === showLinkDialog ? 'Creating Link...' : 'Create Link'}
              </button>
              <button
                onClick={() => {
                  setShowLinkDialog(null);
                  setLinkForm({ itemType: 'assessment', itemId: '' });
                }}
                disabled={linkingEvidence === showLinkDialog}
                className="flex-1 px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600 disabled:opacity-50"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}