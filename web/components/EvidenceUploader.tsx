"use client";
import { useState, useRef } from "react";

interface EvidenceUploaderProps {
  onUploadComplete?: (blobUrl: string) => void;
}

export default function EvidenceUploader({ onUploadComplete }: EvidenceUploaderProps) {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadedUrl, setUploadedUrl] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  async function handleUpload(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setError(null);
    setUploadedUrl(null);

    try {
      // Generate a unique blob name
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
      const blobName = `evidence/${timestamp}-${file.name}`;

      // Get SAS URL from backend
      const sasResponse = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"}/uploads/sas`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          blob_name: blobName,
          permissions: "cw"
        })
      });

      if (sasResponse.status === 501) {
        setError("Evidence uploads not configured on server");
        return;
      }

      if (!sasResponse.ok) {
        const errorData = await sasResponse.json();
        throw new Error(errorData.detail || "Failed to get upload URL");
      }

      const { sasUrl } = await sasResponse.json();

      // Upload file directly to Azure Storage
      const uploadResponse = await fetch(sasUrl, {
        method: "PUT",
        headers: {
          "x-ms-blob-type": "BlockBlob",
          "Content-Type": file.type || "application/octet-stream"
        },
        body: file
      });

      if (!uploadResponse.ok) {
        throw new Error(`Upload failed: ${uploadResponse.statusText}`);
      }

      // Extract base URL (without SAS token) for display
      const baseUrl = sasUrl.split('?')[0];
      setUploadedUrl(baseUrl);
      
      // Notify parent component
      if (onUploadComplete) {
        onUploadComplete(baseUrl);
      }

    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <input
          ref={fileInputRef}
          type="file"
          onChange={handleUpload}
          disabled={uploading}
          className="text-sm file:mr-2 file:py-1 file:px-3 file:rounded file:border-0 file:text-sm file:font-medium file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 disabled:opacity-50"
          accept=".pdf,.docx,.xlsx,.csv,.md,.png,.jpg,.txt"
        />
        {uploading && <span className="text-sm text-gray-600">Uploading...</span>}
      </div>
      
      {error && (
        <div className="text-sm text-red-600">
          Error: {error}
        </div>
      )}
      
      {uploadedUrl && (
        <div className="text-sm text-green-600">
          ✓ Uploaded: {uploadedUrl.split('/').pop()}
        </div>
      )}
    </div>
  );
}










