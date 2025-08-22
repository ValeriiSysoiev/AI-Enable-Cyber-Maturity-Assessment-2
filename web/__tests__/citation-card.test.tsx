/**
 * @jest-environment jsdom
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { jest } from '@jest/globals';
import CitationCard from '@/components/CitationCard';
import type { Citation } from '@/types/csf';
import type { Evidence } from '@/types/evidence';

const mockCitation: Citation = {
  document_id: 'doc-1',
  document_name: 'security-framework.pdf',
  page_number: 12,
  chunk_index: 5,
  relevance_score: 0.78,
  excerpt: 'Organizations should implement multi-factor authentication for all user accounts to enhance security posture.',
  url: 'https://example.com/framework.pdf',
  metadata: { 
    section: 'Authentication Controls',
    category: 'Access Management'
  }
};

const mockEvidence: Evidence = {
  id: 'doc-1',
  engagement_id: 'test-engagement',
  blob_path: 'test/path/framework.pdf',
  filename: 'security-framework.pdf',
  checksum_sha256: 'def456',
  size: 8192,
  mime_type: 'application/pdf',
  uploaded_by: 'security@example.com',
  uploaded_at: '2025-01-01T12:00:00Z',
  pii_flag: false,
  linked_items: []
};

describe('CitationCard', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders citation information correctly', () => {
    render(
      <CitationCard
        citation={mockCitation}
        evidence={mockEvidence}
        correlationId="test-123"
      />
    );

    expect(screen.getByText('security-framework.pdf')).toBeInTheDocument();
    expect(screen.getByText('Page 12')).toBeInTheDocument();
    expect(screen.getByText('Relevance: 78%')).toBeInTheDocument();
    expect(screen.getByText('Chunk 5')).toBeInTheDocument();
    expect(screen.getByText(/Organizations should implement multi-factor authentication/)).toBeInTheDocument();
  });

  it('displays metadata when available', () => {
    render(
      <CitationCard
        citation={mockCitation}
        evidence={mockEvidence}
        correlationId="test-123"
      />
    );

    expect(screen.getByText('Metadata:')).toBeInTheDocument();
    expect(screen.getByText('section: Authentication Controls')).toBeInTheDocument();
    expect(screen.getByText('category: Access Management')).toBeInTheDocument();
  });

  it('displays URL link when available', () => {
    render(
      <CitationCard
        citation={mockCitation}
        evidence={mockEvidence}
        correlationId="test-123"
      />
    );

    const urlLink = screen.getByText('View original source ↗');
    expect(urlLink).toBeInTheDocument();
    expect(urlLink).toHaveAttribute('href', 'https://example.com/framework.pdf');
    expect(urlLink).toHaveAttribute('target', '_blank');
  });

  it('handles citation without page number', () => {
    const citationWithoutPage = { ...mockCitation, page_number: undefined };
    
    render(
      <CitationCard
        citation={citationWithoutPage}
        evidence={mockEvidence}
        correlationId="test-123"
      />
    );

    expect(screen.queryByText(/Page/)).not.toBeInTheDocument();
    expect(screen.getByText('Relevance: 78%')).toBeInTheDocument();
  });

  it('handles citation without metadata', () => {
    const citationWithoutMetadata = { ...mockCitation, metadata: undefined };
    
    render(
      <CitationCard
        citation={citationWithoutMetadata}
        evidence={mockEvidence}
        correlationId="test-123"
      />
    );

    expect(screen.queryByText('Metadata:')).not.toBeInTheDocument();
  });

  it('handles citation without URL', () => {
    const citationWithoutUrl = { ...mockCitation, url: undefined };
    
    render(
      <CitationCard
        citation={citationWithoutUrl}
        evidence={mockEvidence}
        correlationId="test-123"
      />
    );

    expect(screen.queryByText('View original source')).not.toBeInTheDocument();
  });

  it('calls onViewInContext when excerpt is clicked', () => {
    const onViewInContext = jest.fn();
    
    render(
      <CitationCard
        citation={mockCitation}
        evidence={mockEvidence}
        onViewInContext={onViewInContext}
        correlationId="test-123"
      />
    );

    const excerpt = screen.getByText(/Organizations should implement multi-factor authentication/);
    fireEvent.click(excerpt);

    expect(onViewInContext).toHaveBeenCalledWith(mockCitation, mockEvidence);
  });

  it('calls onViewInContext when view button is clicked', () => {
    const onViewInContext = jest.fn();
    
    render(
      <CitationCard
        citation={mockCitation}
        evidence={mockEvidence}
        onViewInContext={onViewInContext}
        correlationId="test-123"
      />
    );

    const viewButton = screen.getByRole('button', { name: 'View citation in document context' });
    fireEvent.click(viewButton);

    expect(onViewInContext).toHaveBeenCalledWith(mockCitation, mockEvidence);
  });

  it('supports keyboard navigation for excerpt', () => {
    const onViewInContext = jest.fn();
    
    render(
      <CitationCard
        citation={mockCitation}
        evidence={mockEvidence}
        onViewInContext={onViewInContext}
        correlationId="test-123"
      />
    );

    const excerpt = screen.getByText(/Organizations should implement multi-factor authentication/).closest('[role="button"]');
    
    // Test Enter key
    fireEvent.keyDown(excerpt!, { key: 'Enter' });
    expect(onViewInContext).toHaveBeenCalledWith(mockCitation, mockEvidence);

    // Test Space key
    fireEvent.keyDown(excerpt!, { key: ' ' });
    expect(onViewInContext).toHaveBeenCalledTimes(2);
  });

  it('copies citation to clipboard when copy button is clicked', async () => {
    const mockClipboard = {
      writeText: jest.fn().mockResolvedValue(undefined)
    };
    Object.assign(navigator, { clipboard: mockClipboard });

    const onCitationCopy = jest.fn();
    
    render(
      <CitationCard
        citation={mockCitation}
        evidence={mockEvidence}
        onCitationCopy={onCitationCopy}
        correlationId="test-123"
      />
    );

    const copyButton = screen.getByRole('button', { name: 'Copy citation to clipboard' });
    fireEvent.click(copyButton);

    await waitFor(() => {
      expect(mockClipboard.writeText).toHaveBeenCalledWith(
        '"Organizations should implement multi-factor authentication for all user accounts to enhance security posture." - security-framework.pdf, page 12'
      );
    });

    expect(onCitationCopy).toHaveBeenCalledWith(mockCitation, mockEvidence);
  });

  it('shows success toast when citation is copied', async () => {
    const mockClipboard = {
      writeText: jest.fn().mockResolvedValue(undefined)
    };
    Object.assign(navigator, { clipboard: mockClipboard });

    render(
      <CitationCard
        citation={mockCitation}
        evidence={mockEvidence}
        correlationId="test-123"
      />
    );

    const copyButton = screen.getByRole('button', { name: 'Copy citation to clipboard' });
    fireEvent.click(copyButton);

    await waitFor(() => {
      expect(screen.getByText('Citation copied to clipboard')).toBeInTheDocument();
    });

    // Toast should disappear after timeout
    await waitFor(() => {
      expect(screen.queryByText('Citation copied to clipboard')).not.toBeInTheDocument();
    }, { timeout: 3000 });
  });

  it('shows error toast when clipboard fails', async () => {
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation();
    const mockClipboard = {
      writeText: jest.fn().mockRejectedValue(new Error('Clipboard access denied'))
    };
    Object.assign(navigator, { clipboard: mockClipboard });

    render(
      <CitationCard
        citation={mockCitation}
        evidence={mockEvidence}
        correlationId="test-123"
      />
    );

    const copyButton = screen.getByRole('button', { name: 'Copy citation to clipboard' });
    fireEvent.click(copyButton);

    await waitFor(() => {
      expect(screen.getByText('Failed to copy citation')).toBeInTheDocument();
    });

    expect(consoleSpy).toHaveBeenCalledWith(
      expect.stringContaining('[test-123] Failed to copy citation:'),
      expect.any(Error)
    );

    consoleSpy.mockRestore();
  });

  it('does not show view button when onViewInContext is not provided', () => {
    render(
      <CitationCard
        citation={mockCitation}
        evidence={mockEvidence}
        correlationId="test-123"
      />
    );

    expect(screen.queryByRole('button', { name: 'View citation in document context' })).not.toBeInTheDocument();
  });

  it('does not make excerpt clickable when onViewInContext is not provided', () => {
    render(
      <CitationCard
        citation={mockCitation}
        evidence={mockEvidence}
        correlationId="test-123"
      />
    );

    const excerpt = screen.getByText(/Organizations should implement multi-factor authentication/);
    expect(excerpt.closest('[role="button"]')).toBeNull();
  });

  it('applies custom className', () => {
    render(
      <CitationCard
        citation={mockCitation}
        evidence={mockEvidence}
        className="custom-class"
        correlationId="test-123"
      />
    );

    const card = screen.getByText('security-framework.pdf').closest('.custom-class');
    expect(card).toBeInTheDocument();
  });

  it('includes correlation ID in console logs', () => {
    const consoleSpy = jest.spyOn(console, 'log').mockImplementation();
    const onViewInContext = jest.fn();
    
    render(
      <CitationCard
        citation={mockCitation}
        evidence={mockEvidence}
        onViewInContext={onViewInContext}
        correlationId="test-correlation-456"
      />
    );

    const viewButton = screen.getByRole('button', { name: 'View citation in document context' });
    fireEvent.click(viewButton);

    expect(consoleSpy).toHaveBeenCalledWith(
      expect.stringContaining('[test-correlation-456]')
    );

    consoleSpy.mockRestore();
  });

  it('meets accessibility requirements', () => {
    render(
      <CitationCard
        citation={mockCitation}
        evidence={mockEvidence}
        onViewInContext={jest.fn()}
        correlationId="test-123"
      />
    );

    // Check button accessibility
    const copyButton = screen.getByRole('button', { name: 'Copy citation to clipboard' });
    expect(copyButton).toHaveAttribute('aria-label');

    const viewButton = screen.getByRole('button', { name: 'View citation in document context' });
    expect(viewButton).toHaveAttribute('aria-label');

    // Check clickable excerpt accessibility
    const excerpt = screen.getByText(/Organizations should implement multi-factor authentication/).closest('[role="button"]');
    expect(excerpt).toHaveAttribute('aria-label');
    expect(excerpt).toHaveAttribute('tabIndex', '0');
  });
});