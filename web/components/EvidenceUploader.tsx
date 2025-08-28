"use client";
import { useState, useRef, useCallback } from "react";
import { useParams } from "next/navigation";
import {
  generateEvidenceSAS,
  uploadFileToAzure,
  completeEvidenceUpload,
  computeFileChecksum,
  formatFileSize,
  getFileIcon
} from "../lib/evidence";
import type { Evidence, UploadState } from "../types/evidence";

interface EvidenceUploaderProps {
  onUploadComplete?: (evidence: Evidence) => void;
  className?: string;
}

const ALLOWED_TYPES = [
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
  "application/vnd.openxmlformats-officedocument.presentationml.presentation",
  "text/plain",
  "text/csv",
  "image/png",
  "image/jpeg",
  "image/gif",
  "application/zip",
  "application/x-zip-compressed"
];

const MAX_FILE_SIZE = 25 * 1024 * 1024; // 25MB

export default function EvidenceUploader({ onUploadComplete, className = "" }: EvidenceUploaderProps) {
  const { engagementId } = useParams<{ engagementId: string }>();
  const [uploadState, setUploadState] = useState<UploadState>({
    status: 'idle',
    progress: 0
  });
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const resetUpload = useCallback(() => {
    setUploadState({ status: 'idle', progress: 0 });
    setSelectedFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }, []);

  const validateFile = useCallback((file: File): string | null => {
    // Check file size
    if (file.size > MAX_FILE_SIZE) {
      return `File too large. Maximum size: ${formatFileSize(MAX_FILE_SIZE)}`;
    }

    // Check MIME type
    if (!ALLOWED_TYPES.includes(file.type)) {
      return `Unsupported file type: ${file.type}. Allowed types: PDF, DOCX, XLSX, PPTX, TXT, CSV, PNG, JPG, GIF, ZIP`;
    }

    return null;
  }, []);

  const handleFileSelect = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const validationError = validateFile(file);
    if (validationError) {
      setUploadState({
        status: 'error',
        progress: 0,
        error: validationError
      });
      return;
    }

    setSelectedFile(file);
    setUploadState({ status: 'idle', progress: 0 });
  }, [validateFile]);

  const handleUpload = useCallback(async () => {
    if (!selectedFile || !engagementId) return;

    try {
      // Step 1: Generate SAS token
      setUploadState({ status: 'generating_sas', progress: 10 });
      
      const sasResponse = await generateEvidenceSAS({
        engagement_id: engagementId,
        filename: selectedFile.name,
        mime_type: selectedFile.type,
        size_bytes: selectedFile.size
      });

      // Step 2: Upload to Azure Storage
      setUploadState({ status: 'uploading', progress: 30 });
      
      await uploadFileToAzure(sasResponse.upload_url, selectedFile);
      
      setUploadState({ status: 'uploading', progress: 70 });

      // Step 3: Compute client checksum
      const clientChecksum = await computeFileChecksum(selectedFile);
      
      setUploadState({ status: 'completing', progress: 90 });

      // Step 4: Complete upload
      const completeResponse = await completeEvidenceUpload({
        engagement_id: engagementId,
        blob_path: sasResponse.blob_path,
        filename: selectedFile.name,
        mime_type: selectedFile.type,
        size_bytes: selectedFile.size,
        client_checksum: clientChecksum
      });

      // Create evidence object for callback
      const evidence: Evidence = {
        id: completeResponse.evidence_id,
        engagement_id: engagementId,
        blob_path: sasResponse.blob_path,
        filename: selectedFile.name,
        checksum_sha256: completeResponse.checksum,
        size: completeResponse.size,
        mime_type: selectedFile.type,
        uploaded_by: "", // Will be set by backend
        uploaded_at: new Date().toISOString(),
        pii_flag: completeResponse.pii_flag,
        linked_items: []
      };

      setUploadState({
        status: 'completed',
        progress: 100,
        evidence
      });

      // Notify parent
      if (onUploadComplete) {
        onUploadComplete(evidence);
      }

    } catch (error) {
      setUploadState({
        status: 'error',
        progress: 0,
        error: error instanceof Error ? error.message : 'Upload failed'
      });
    }
  }, [selectedFile, engagementId, onUploadComplete]);

  const getStatusMessage = () => {
    switch (uploadState.status) {
      case 'generating_sas':
        return 'Generating upload URL...';
      case 'uploading':
        return 'Uploading file...';
      case 'completing':
        return 'Finalizing upload...';
      case 'completed':
        return 'Upload completed successfully!';
      case 'error':
        return `Error: ${uploadState.error}`;
      default:
        return '';
    }
  };

  const getStatusColor = () => {
    switch (uploadState.status) {
      case 'error':
        return 'text-red-600';
      case 'completed':
        return 'text-green-600';
      default:
        return 'text-blue-600';
    }
  };

  const isUploading = ['generating_sas', 'uploading', 'completing'].includes(uploadState.status);

  return (
    <div className={`space-y-4 ${className}`}>
      {/* File Selection */}
      <div 
        className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-gray-400 transition-colors"
        role="button"
        tabIndex={isUploading ? -1 : 0}
        aria-label="File upload area"
        onKeyDown={(e) => {
          if ((e.key === 'Enter' || e.key === ' ') && !isUploading) {
            e.preventDefault();
            fileInputRef.current?.click();
          }
        }}
      >
        <input
          ref={fileInputRef}
          type="file"
          onChange={handleFileSelect}
          disabled={isUploading}
          className="hidden"
          accept=".pdf,.docx,.xlsx,.pptx,.txt,.csv,.png,.jpg,.jpeg,.gif,.zip"
        />
        
        {!selectedFile ? (
          <div>
            <div className="text-4xl mb-2">📎</div>
            <div className="text-sm text-gray-600 mb-4">
              Select a file to upload as evidence
            </div>
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploading}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
              aria-label="Choose file to upload"
            >
              Choose File
            </button>
            <div className="text-xs text-gray-500 mt-2">
              Max size: {formatFileSize(MAX_FILE_SIZE)} • Supported: PDF, DOCX, XLSX, PPTX, TXT, CSV, Images, ZIP
            </div>
          </div>
        ) : (
          <div>
            <div className="text-4xl mb-2">{getFileIcon(selectedFile.type)}</div>
            <div className="text-sm font-medium mb-1">{selectedFile.name}</div>
            <div className="text-xs text-gray-500 mb-4">
              {formatFileSize(selectedFile.size)} • {selectedFile.type}
            </div>
            
            {uploadState.status === 'idle' && (
              <div className="flex gap-2 justify-center">
                <button
                  onClick={handleUpload}
                  className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
                >
                  Upload
                </button>
                <button
                  onClick={resetUpload}
                  className="px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600"
                >
                  Cancel
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Upload Progress */}
      {isUploading && (
        <div className="space-y-2" role="status" aria-live="polite">
          <div 
            className="w-full bg-gray-200 rounded-full h-2"
            role="progressbar"
            aria-valuenow={uploadState.progress}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label="Upload progress"
          >
            <div 
              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${uploadState.progress}%` }}
            />
          </div>
          <div className="text-sm text-center text-gray-600">
            {uploadState.progress}% - {getStatusMessage()}
          </div>
        </div>
      )}

      {/* Status Messages */}
      {uploadState.status !== 'idle' && !isUploading && (
        <div 
          className={`text-sm text-center ${getStatusColor()}`}
          role={uploadState.status === 'error' ? 'alert' : 'status'}
          aria-live={uploadState.status === 'error' ? 'assertive' : 'polite'}
        >
          {getStatusMessage()}
          {uploadState.status === 'completed' && uploadState.evidence?.pii_flag && (
            <div className="text-orange-600 mt-2" role="alert">
              ⚠️ Potential PII detected in this file
            </div>
          )}
        </div>
      )}

      {/* Success Actions */}
      {uploadState.status === 'completed' && (
        <div className="flex gap-2 justify-center">
          <button
            onClick={resetUpload}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Upload Another File
          </button>
        </div>
      )}
    </div>
  );
}










