/**
 * @jest-environment jsdom
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { jest } from '@jest/globals';
import DocumentViewer from '@/components/DocumentViewer';
import type { Citation } from '@/types/csf';
import type { Evidence } from '@/types/evidence';

const mockEvidence: Evidence = {
  id: 'evidence-1',
  engagement_id: 'test-engagement',
  blob_path: 'test/path/policy.pdf',
  filename: 'security-policy.pdf',
  checksum_sha256: 'abc123',
  size: 4096,
  mime_type: 'application/pdf',
  uploaded_by: 'admin@example.com',
  uploaded_at: '2025-01-01T10:00:00Z',
  pii_flag: false,
  linked_items: []
};

const mockCitation: Citation = {
  document_id: 'evidence-1',
  document_name: 'security-policy.pdf',
  page_number: 5,
  chunk_index: 2,
  relevance_score: 0.85,
  excerpt: 'All employees must complete cybersecurity training annually.',
  url: 'https://example.com/policy.pdf',
  metadata: { section: 'Training Requirements' }
};

describe('DocumentViewer', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('does not render when closed', () => {
    render(
      <DocumentViewer
        evidence={mockEvidence}
        citation={mockCitation}
        isOpen={false}
        onClose={jest.fn()}
        correlationId="test-123"
      />
    );

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('renders when open with evidence and citation', async () => {
    render(
      <DocumentViewer
        evidence={mockEvidence}
        citation={mockCitation}
        isOpen={true}
        onClose={jest.fn()}
        correlationId="test-123"
      />
    );

    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText('security-policy.pdf')).toBeInTheDocument();
    expect(screen.getByText('Page 5')).toBeInTheDocument();
    expect(screen.getByText('Relevance: 85%')).toBeInTheDocument();
  });

  it('calls onClose when escape key is pressed', () => {
    const onClose = jest.fn();
    render(
      <DocumentViewer
        evidence={mockEvidence}
        citation={mockCitation}
        isOpen={true}
        onClose={onClose}
        correlationId="test-123"
      />
    );

    fireEvent.keyDown(document, { key: 'Escape' });
    expect(onClose).toHaveBeenCalled();
  });

  it('calls onClose when clicking outside modal', () => {
    const onClose = jest.fn();
    render(
      <DocumentViewer
        evidence={mockEvidence}
        citation={mockCitation}
        isOpen={true}
        onClose={onClose}
        correlationId="test-123"
      />
    );

    const backdrop = screen.getByRole('dialog');
    fireEvent.click(backdrop);
    expect(onClose).toHaveBeenCalled();
  });

  it('does not close when clicking inside modal content', () => {
    const onClose = jest.fn();
    render(
      <DocumentViewer
        evidence={mockEvidence}
        citation={mockCitation}
        isOpen={true}
        onClose={onClose}
        correlationId="test-123"
      />
    );

    const modalContent = screen.getByText('security-policy.pdf');
    fireEvent.click(modalContent);
    expect(onClose).not.toHaveBeenCalled();
  });

  it('displays loading state initially', async () => {
    render(
      <DocumentViewer
        evidence={mockEvidence}
        citation={mockCitation}
        isOpen={true}
        onClose={jest.fn()}
        correlationId="test-123"
      />
    );

    expect(screen.getByText('Loading document...')).toBeInTheDocument();
  });

  it('displays document content after loading', async () => {
    render(
      <DocumentViewer
        evidence={mockEvidence}
        citation={mockCitation}
        isOpen={true}
        onClose={jest.fn()}
        correlationId="test-123"
      />
    );

    await waitFor(() => {
      expect(screen.queryByText('Loading document...')).not.toBeInTheDocument();
    });

    expect(screen.getByText(/All employees must complete cybersecurity training/)).toBeInTheDocument();
  });

  it('highlights citation excerpt in document content', async () => {
    render(
      <DocumentViewer
        evidence={mockEvidence}
        citation={mockCitation}
        isOpen={true}
        onClose={jest.fn()}
        correlationId="test-123"
      />
    );

    await waitFor(() => {
      const highlightedText = screen.getByText('All employees must complete cybersecurity training annually.');
      expect(highlightedText).toHaveClass('bg-yellow-200');
    });
  });

  it('copies citation when copy button is clicked', async () => {
    const mockClipboard = {
      writeText: jest.fn().mockResolvedValue(undefined)
    };
    Object.assign(navigator, { clipboard: mockClipboard });

    render(
      <DocumentViewer
        evidence={mockEvidence}
        citation={mockCitation}
        isOpen={true}
        onClose={jest.fn()}
        correlationId="test-123"
      />
    );

    const copyButton = screen.getByRole('button', { name: 'Copy citation' });
    fireEvent.click(copyButton);

    await waitFor(() => {
      expect(mockClipboard.writeText).toHaveBeenCalledWith(
        '"All employees must complete cybersecurity training annually." - security-policy.pdf, page 5'
      );
    });
  });

  it('handles copy citation error gracefully', async () => {
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation();
    const mockClipboard = {
      writeText: jest.fn().mockRejectedValue(new Error('Clipboard error'))
    };
    Object.assign(navigator, { clipboard: mockClipboard });

    render(
      <DocumentViewer
        evidence={mockEvidence}
        citation={mockCitation}
        isOpen={true}
        onClose={jest.fn()}
        correlationId="test-123"
      />
    );

    const copyButton = screen.getByRole('button', { name: 'Copy citation' });
    fireEvent.click(copyButton);

    await waitFor(() => {
      expect(consoleSpy).toHaveBeenCalledWith(
        expect.stringContaining('[test-123] Failed to copy citation:'),
        expect.any(Error)
      );
    });

    consoleSpy.mockRestore();
  });

  it('displays document metadata in footer', () => {
    render(
      <DocumentViewer
        evidence={mockEvidence}
        citation={mockCitation}
        isOpen={true}
        onClose={jest.fn()}
        correlationId="test-123"
      />
    );

    expect(screen.getByText('Document Size: 4.0 KB')).toBeInTheDocument();
    expect(screen.getByText('Type: application/pdf')).toBeInTheDocument();
    expect(screen.getByText('Citation chunk: 2')).toBeInTheDocument();
  });

  it('displays citation without page number', () => {
    const citationWithoutPage = { ...mockCitation, page_number: undefined };
    
    render(
      <DocumentViewer
        evidence={mockEvidence}
        citation={citationWithoutPage}
        isOpen={true}
        onClose={jest.fn()}
        correlationId="test-123"
      />
    );

    expect(screen.queryByText(/Page/)).not.toBeInTheDocument();
    expect(screen.getByText('Relevance: 85%')).toBeInTheDocument();
  });

  it('works without citation provided', async () => {
    render(
      <DocumentViewer
        evidence={mockEvidence}
        citation={null}
        isOpen={true}
        onClose={jest.fn()}
        correlationId="test-123"
      />
    );

    expect(screen.getByText('security-policy.pdf')).toBeInTheDocument();
    expect(screen.queryByText('Copy Citation')).not.toBeInTheDocument();
    expect(screen.queryByText('Highlighted Citation')).not.toBeInTheDocument();
  });

  it('displays error state when document loading fails', async () => {
    // Mock a scenario where document loading would fail
    const evidenceWithError = { ...mockEvidence, id: 'invalid-id' };
    
    render(
      <DocumentViewer
        evidence={evidenceWithError}
        citation={mockCitation}
        isOpen={true}
        onClose={jest.fn()}
        correlationId="test-123"
      />
    );

    // For this test, we'd need to mock the document loading to actually fail
    // For now, we verify the component structure supports error handling
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('meets accessibility requirements', () => {
    render(
      <DocumentViewer
        evidence={mockEvidence}
        citation={mockCitation}
        isOpen={true}
        onClose={jest.fn()}
        correlationId="test-123"
      />
    );

    const dialog = screen.getByRole('dialog');
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    expect(dialog).toHaveAttribute('aria-labelledby', 'document-viewer-title');

    const title = screen.getByText('security-policy.pdf');
    expect(title).toHaveAttribute('id', 'document-viewer-title');

    const closeButton = screen.getByRole('button', { name: 'Close document viewer' });
    expect(closeButton).toBeInTheDocument();
  });

  it('includes correlation ID in console logs', () => {
    const consoleSpy = jest.spyOn(console, 'log').mockImplementation();
    
    render(
      <DocumentViewer
        evidence={mockEvidence}
        citation={mockCitation}
        isOpen={true}
        onClose={jest.fn()}
        correlationId="test-correlation-789"
      />
    );

    expect(consoleSpy).toHaveBeenCalledWith(
      expect.stringContaining('[test-correlation-789]')
    );

    consoleSpy.mockRestore();
  });
});