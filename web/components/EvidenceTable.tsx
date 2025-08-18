"use client";
import { useState, useEffect, useCallback } from "react";
import { useParams } from "next/navigation";
import {
  listEvidence,
  linkEvidence,
  unlinkEvidence,
  formatFileSize,
  getFileIcon
} from "@/lib/evidence";
import type { Evidence, EvidenceListResponse } from "@/types/evidence";

interface EvidenceTableProps {
  onEvidenceSelect?: (evidence: Evidence) => void;
  refreshTrigger?: number;
  className?: string;
}

export default function EvidenceTable({ 
  onEvidenceSelect, 
  refreshTrigger = 0,
  className = "" 
}: EvidenceTableProps) {
  const { engagementId } = useParams<{ engagementId: string }>();
  const [evidenceData, setEvidenceData] = useState<EvidenceListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [linkingEvidence, setLinkingEvidence] = useState<string | null>(null);

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
      <div className={`${className}`}>
        <div className="flex items-center justify-center py-8">
          <div className="text-gray-600">Loading evidence...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`${className}`}>
        <div className="flex items-center justify-center py-8">
          <div className="text-red-600">Error: {error}</div>
        </div>
      </div>
    );
  }

  if (!evidenceData || evidenceData.data.length === 0) {
    return (
      <div className={`${className}`}>
        <div className="flex flex-col items-center justify-center py-12">
          <div className="text-4xl mb-4">📂</div>
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
        <table className="w-full">
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
                    >
                      View
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        navigator.clipboard.writeText(evidence.checksum_sha256);
                        alert('Checksum copied to clipboard');
                      }}
                      className="text-gray-600 hover:text-gray-800 text-sm"
                      title="Copy checksum"
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
    </div>
  );
}