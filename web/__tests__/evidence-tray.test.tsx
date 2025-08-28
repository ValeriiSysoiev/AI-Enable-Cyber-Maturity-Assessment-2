/**
 * @jest-environment jsdom
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { jest } from '@jest/globals';
import EvidenceTray from '../components/EvidenceTray';
import type { Evidence } from '../types/evidence';
import type { Citation } from '../types/csf';

const mockEvidence: Evidence[] = [
  {
    id: 'evidence-1',
    engagement_id: 'test-engagement',
    blob_path: 'test/path/security-policy.pdf',
    filename: 'security-policy.pdf',
    checksum_sha256: 'abc123',
    size: 4096,
    mime_type: 'application/pdf',
    uploaded_by: 'admin@example.com',
    uploaded_at: '2025-01-01T10:00:00Z',
    pii_flag: false,
    linked_items: [{ item_type: 'subcategory', item_id: 'ID.AM-1' }]
  },
  {
    id: 'evidence-2',
    engagement_id: 'test-engagement',
    blob_path: 'test/path/incident-report.docx',
    filename: 'incident-report.docx',
    checksum_sha256: 'def456',
    size: 2048,
    mime_type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    uploaded_by: 'security@example.com',
    uploaded_at: '2025-01-01T11:00:00Z',
    pii_flag: true,
    linked_items: []
  }
];

const mockCitations: Citation[] = [
  {
    document_id: 'evidence-1',
    document_name: 'security-policy.pdf',
    page_number: 3,
    chunk_index: 0,
    relevance_score: 0.85,
    excerpt: 'All physical devices must be inventoried and tracked according to organizational policies.',
    url: 'https://example.com/evidence-1',
    metadata: { section: 'Device Management' }
  },
  {
    document_id: 'evidence-1',
    document_name: 'security-policy.pdf',
    page_number: 5,
    chunk_index: 1,
    relevance_score: 0.72,
    excerpt: 'Regular audits of device inventory shall be conducted quarterly.',
    metadata: { section: 'Audit Requirements' }
  }
];

describe('EvidenceTray', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders loading state', () => {
    render(<EvidenceTray evidence={[]} loading={true} correlationId="test-123" />);
    
    expect(screen.getByText('Loading evidence...')).toBeInTheDocument();
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('renders error state with retry button', () => {
    const onRetry = jest.fn();
    render(
      <EvidenceTray 
        evidence={[]} 
        error="Network connection failed"
        onRetry={onRetry}
        correlationId="test-123"
      />
    );
    
    expect(screen.getByText('Failed to load evidence')).toBeInTheDocument();
    expect(screen.getByText('Network connection failed')).toBeInTheDocument();
    
    const retryButton = screen.getByRole('button', { name: 'Retry' });
    fireEvent.click(retryButton);
    expect(onRetry).toHaveBeenCalled();
  });

  it('renders empty state when no evidence', () => {
    render(<EvidenceTray evidence={[]} correlationId="test-123" />);
    
    expect(screen.getByText('No evidence files found')).toBeInTheDocument();
    expect(screen.getByText(/Upload documents and link them/)).toBeInTheDocument();
  });

  it('renders evidence list with citations', () => {
    render(
      <EvidenceTray 
        evidence={mockEvidence} 
        citations={mockCitations}
        correlationId="test-123"
      />
    );
    
    expect(screen.getByText('Evidence & Citations')).toBeInTheDocument();
    expect(screen.getByText('2 files • 2 citations')).toBeInTheDocument();
    
    // Check first evidence item
    expect(screen.getByText('security-policy.pdf')).toBeInTheDocument();
    expect(screen.getByText('2 citations')).toBeInTheDocument();
    
    // Check second evidence item
    expect(screen.getByText('incident-report.docx')).toBeInTheDocument();
  });

  it('expands evidence item to show details', () => {
    render(
      <EvidenceTray 
        evidence={mockEvidence} 
        citations={mockCitations}
        correlationId="test-123"
      />
    );
    
    // Find and click the expand button for first evidence
    const expandButton = screen.getAllByLabelText('Expand details')[0];
    fireEvent.click(expandButton);
    
    // Should show file information
    expect(screen.getByText('File Information')).toBeInTheDocument();
    expect(screen.getByText('Size: 4.0 KB')).toBeInTheDocument();
    expect(screen.getByText('Type: application/pdf')).toBeInTheDocument();
    expect(screen.getByText('Uploaded by: admin@example.com')).toBeInTheDocument();
  });

  it('shows PII warning for flagged evidence', () => {
    render(
      <EvidenceTray 
        evidence={mockEvidence} 
        citations={mockCitations}
        correlationId="test-123"
      />
    );
    
    // Expand second evidence item which has PII flag
    const expandButtons = screen.getAllByLabelText('Expand details');
    fireEvent.click(expandButtons[1]);
    
    expect(screen.getByText('Potential PII detected')).toBeInTheDocument();
  });

  it('displays linked items when present', () => {
    render(
      <EvidenceTray 
        evidence={mockEvidence} 
        citations={mockCitations}
        correlationId="test-123"
      />
    );
    
    // Expand first evidence item which has linked items
    const expandButton = screen.getAllByLabelText('Expand details')[0];
    fireEvent.click(expandButton);
    
    expect(screen.getByText('Linked Items')).toBeInTheDocument();
    expect(screen.getByText('subcategory: ID.AM-1')).toBeInTheDocument();
  });

  it('displays inline citations with relevance scores', () => {
    render(
      <EvidenceTray 
        evidence={mockEvidence} 
        citations={mockCitations}
        correlationId="test-123"
      />
    );
    
    // Expand first evidence item to see citations
    const expandButton = screen.getAllByLabelText('Expand details')[0];
    fireEvent.click(expandButton);
    
    expect(screen.getByText('Inline Citations')).toBeInTheDocument();
    expect(screen.getByText('Page 3 • Relevance: 85%')).toBeInTheDocument();
    expect(screen.getByText(/All physical devices must be inventoried/)).toBeInTheDocument();
    expect(screen.getByText('Page 5 • Relevance: 72%')).toBeInTheDocument();
  });

  it('calls onEvidenceSelect when evidence is clicked', () => {
    const onEvidenceSelect = jest.fn();
    render(
      <EvidenceTray 
        evidence={mockEvidence} 
        citations={mockCitations}
        onEvidenceSelect={onEvidenceSelect}
        correlationId="test-123"
      />
    );
    
    const evidenceItem = screen.getByText('security-policy.pdf').closest('[role="button"]');
    fireEvent.click(evidenceItem!);
    
    expect(onEvidenceSelect).toHaveBeenCalledWith(mockEvidence[0]);
  });

  it('calls onCitationView when citation is clicked', () => {
    const onCitationView = jest.fn();
    render(
      <EvidenceTray 
        evidence={mockEvidence} 
        citations={mockCitations}
        onCitationView={onCitationView}
        correlationId="test-123"
      />
    );
    
    // Expand evidence to see citations
    const expandButton = screen.getAllByLabelText('Expand details')[0];
    fireEvent.click(expandButton);
    
    // Click on first citation
    const citationViewButtons = screen.getAllByText('View');
    fireEvent.click(citationViewButtons[0]);
    
    expect(onCitationView).toHaveBeenCalledWith(mockCitations[0]);
  });

  it('supports keyboard navigation', () => {
    const onEvidenceSelect = jest.fn();
    render(
      <EvidenceTray 
        evidence={mockEvidence} 
        citations={mockCitations}
        onEvidenceSelect={onEvidenceSelect}
        correlationId="test-123"
      />
    );
    
    const evidenceItem = screen.getByText('security-policy.pdf').closest('[role="button"]');
    evidenceItem!.focus();
    fireEvent.keyDown(evidenceItem!, { key: 'Enter' });
    
    expect(onEvidenceSelect).toHaveBeenCalledWith(mockEvidence[0]);
  });

  it('supports keyboard navigation for citations', () => {
    const onCitationView = jest.fn();
    render(
      <EvidenceTray 
        evidence={mockEvidence} 
        citations={mockCitations}
        onCitationView={onCitationView}
        correlationId="test-123"
      />
    );
    
    // Expand evidence to see citations
    const expandButton = screen.getAllByLabelText('Expand details')[0];
    fireEvent.click(expandButton);
    
    // Find and focus first citation
    const citation = screen.getByLabelText('View citation from page 3');
    citation.focus();
    fireEvent.keyDown(citation, { key: 'Enter' });
    
    expect(onCitationView).toHaveBeenCalledWith(mockCitations[0]);
  });

  it('handles space key for keyboard activation', () => {
    const onEvidenceSelect = jest.fn();
    render(
      <EvidenceTray 
        evidence={mockEvidence} 
        citations={mockCitations}
        onEvidenceSelect={onEvidenceSelect}
        correlationId="test-123"
      />
    );
    
    const evidenceItem = screen.getByText('security-policy.pdf').closest('[role="button"]');
    fireEvent.keyDown(evidenceItem!, { key: ' ' });
    
    expect(onEvidenceSelect).toHaveBeenCalledWith(mockEvidence[0]);
  });

  it('meets accessibility requirements', () => {
    render(
      <EvidenceTray 
        evidence={mockEvidence} 
        citations={mockCitations}
        correlationId="test-123"
      />
    );
    
    // Check list structure
    expect(screen.getByRole('list', { name: 'Evidence files' })).toBeInTheDocument();
    
    // Check each evidence item has proper role
    const listItems = screen.getAllByRole('listitem');
    expect(listItems).toHaveLength(2);
    
    // Check evidence items are focusable
    const evidenceButtons = screen.getAllByRole('button');
    evidenceButtons.forEach(button => {
      expect(button).toHaveAttribute('tabIndex');
    });
  });

  it('includes correlation ID in console logs', () => {
    const consoleSpy = jest.spyOn(console, 'log').mockImplementation();
    const onEvidenceSelect = jest.fn();
    
    render(
      <EvidenceTray 
        evidence={mockEvidence} 
        citations={mockCitations}
        onEvidenceSelect={onEvidenceSelect}
        correlationId="test-correlation-456"
      />
    );
    
    // Trigger an action that logs
    const evidenceItem = screen.getByText('security-policy.pdf').closest('[role="button"]');
    fireEvent.click(evidenceItem!);
    
    expect(consoleSpy).toHaveBeenCalledWith(
      expect.stringContaining('[test-correlation-456]')
    );
    
    consoleSpy.mockRestore();
  });

  it('handles citation with no page number', () => {
    const citationWithoutPage: Citation = {
      ...mockCitations[0],
      page_number: undefined
    };
    
    render(
      <EvidenceTray 
        evidence={mockEvidence} 
        citations={[citationWithoutPage]}
        correlationId="test-123"
      />
    );
    
    // Expand evidence to see citation
    const expandButton = screen.getAllByLabelText('Expand details')[0];
    fireEvent.click(expandButton);
    
    expect(screen.getByText('Relevance: 85%')).toBeInTheDocument();
    expect(screen.queryByText('Page')).not.toBeInTheDocument();
  });
});