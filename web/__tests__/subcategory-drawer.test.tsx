/**
 * @jest-environment jsdom
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { jest } from '@jest/globals';
import SubcategoryDrawer from '../components/SubcategoryDrawer';
import type { CSFSubcategory } from '../types/csf';
import type { Evidence } from '../types/evidence';

// Mock Next.js router
jest.mock('next/navigation', () => ({
  useParams: jest.fn(() => ({ engagementId: 'test-engagement' })),
}));

// Mock evidence API
jest.mock('../lib/evidence', () => ({
  listEvidence: jest.fn(),
}));

const mockSubcategory: CSFSubcategory = {
  id: 'ID.AM-1',
  function_id: 'ID',
  category_id: 'ID.AM',
  title: 'Physical devices and systems within the organization are inventoried',
  description: 'Maintain an accurate, current, and comprehensive inventory of authorized and unauthorized physical devices.'
};

const mockEvidence: Evidence[] = [
  {
    id: 'evidence-1',
    engagement_id: 'test-engagement',
    blob_path: 'test/path/device-inventory.pdf',
    filename: 'device-inventory.pdf',
    checksum_sha256: 'abc123',
    size: 2048,
    mime_type: 'application/pdf',
    uploaded_by: 'user@example.com',
    uploaded_at: '2025-01-01T00:00:00Z',
    pii_flag: false,
    linked_items: [{ item_type: 'subcategory', item_id: 'ID.AM-1' }]
  }
];

describe('SubcategoryDrawer', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders when open with subcategory', () => {
    render(
      <SubcategoryDrawer
        subcategory={mockSubcategory}
        isOpen={true}
        onClose={jest.fn()}
        correlationId="test-123"
      />
    );

    expect(screen.getByText('ID.AM-1')).toBeInTheDocument();
    expect(screen.getByText(mockSubcategory.title)).toBeInTheDocument();
    expect(screen.getByText(mockSubcategory.description)).toBeInTheDocument();
  });

  it('does not render when closed', () => {
    render(
      <SubcategoryDrawer
        subcategory={mockSubcategory}
        isOpen={false}
        onClose={jest.fn()}
        correlationId="test-123"
      />
    );

    expect(screen.queryByText('ID.AM-1')).not.toBeInTheDocument();
  });

  it('calls onClose when escape key is pressed', () => {
    const onClose = jest.fn();
    render(
      <SubcategoryDrawer
        subcategory={mockSubcategory}
        isOpen={true}
        onClose={onClose}
        correlationId="test-123"
      />
    );

    fireEvent.keyDown(document, { key: 'Escape' });
    expect(onClose).toHaveBeenCalled();
  });

  it('calls onClose when clicking outside drawer', () => {
    const onClose = jest.fn();
    render(
      <SubcategoryDrawer
        subcategory={mockSubcategory}
        isOpen={true}
        onClose={onClose}
        correlationId="test-123"
      />
    );

    const backdrop = screen.getByRole('dialog');
    fireEvent.click(backdrop);
    expect(onClose).toHaveBeenCalled();
  });

  it('handles score changes via buttons', () => {
    const onScoreChange = jest.fn();
    render(
      <SubcategoryDrawer
        subcategory={mockSubcategory}
        isOpen={true}
        onClose={jest.fn()}
        onScoreChange={onScoreChange}
        correlationId="test-123"
      />
    );

    const scoreButton = screen.getByRole('button', { name: '3' });
    fireEvent.click(scoreButton);
    expect(onScoreChange).toHaveBeenCalledWith(3);
  });

  it('handles score changes via keyboard shortcuts', () => {
    const onScoreChange = jest.fn();
    render(
      <SubcategoryDrawer
        subcategory={mockSubcategory}
        isOpen={true}
        onClose={jest.fn()}
        onScoreChange={onScoreChange}
        correlationId="test-123"
      />
    );

    fireEvent.keyDown(document, { key: '4', ctrlKey: true });
    expect(onScoreChange).toHaveBeenCalledWith(4);
  });

  it('handles rationale changes', () => {
    const onRationaleChange = jest.fn();
    render(
      <SubcategoryDrawer
        subcategory={mockSubcategory}
        isOpen={true}
        onClose={jest.fn()}
        onRationaleChange={onRationaleChange}
        correlationId="test-123"
      />
    );

    const textarea = screen.getByRole('textbox', { name: /assessment rationale/i });
    fireEvent.change(textarea, { target: { value: 'Test rationale' } });
    expect(onRationaleChange).toHaveBeenCalledWith('Test rationale');
  });

  it('switches between assessment and evidence tabs', () => {
    render(
      <SubcategoryDrawer
        subcategory={mockSubcategory}
        isOpen={true}
        onClose={jest.fn()}
        correlationId="test-123"
      />
    );

    // Should start on assessment tab
    expect(screen.getByRole('tab', { selected: true })).toHaveTextContent('Assessment');

    // Click evidence tab
    const evidenceTab = screen.getByRole('tab', { name: /evidence/i });
    fireEvent.click(evidenceTab);

    // Evidence tab should now be selected
    expect(screen.getByRole('tab', { selected: true })).toHaveTextContent(/Evidence/);
  });

  it('loads evidence on mount', async () => {
    const { listEvidence } = require('../lib/evidence');
    listEvidence.mockResolvedValue({
      data: mockEvidence,
      total: 1,
      page: 1,
      page_size: 100,
      total_pages: 1,
      has_next: false,
      has_previous: false
    });

    render(
      <SubcategoryDrawer
        subcategory={mockSubcategory}
        isOpen={true}
        onClose={jest.fn()}
        correlationId="test-123"
      />
    );

    // Switch to evidence tab to see loading
    const evidenceTab = screen.getByRole('tab', { name: /evidence/i });
    fireEvent.click(evidenceTab);

    await waitFor(() => {
      expect(listEvidence).toHaveBeenCalledWith('test-engagement', 1, 100);
    });
  });

  it('displays error state for evidence loading', async () => {
    const { listEvidence } = require('../lib/evidence');
    listEvidence.mockRejectedValue(new Error('Network error'));

    render(
      <SubcategoryDrawer
        subcategory={mockSubcategory}
        isOpen={true}
        onClose={jest.fn()}
        correlationId="test-123"
      />
    );

    // Switch to evidence tab
    const evidenceTab = screen.getByRole('tab', { name: /evidence/i });
    fireEvent.click(evidenceTab);

    await waitFor(() => {
      expect(screen.getByText('Failed to load evidence')).toBeInTheDocument();
      expect(screen.getByText('Network error')).toBeInTheDocument();
    });
  });

  it('displays empty state when no evidence', async () => {
    const { listEvidence } = require('../lib/evidence');
    listEvidence.mockResolvedValue({
      data: [],
      total: 0,
      page: 1,
      page_size: 100,
      total_pages: 0,
      has_next: false,
      has_previous: false
    });

    render(
      <SubcategoryDrawer
        subcategory={mockSubcategory}
        isOpen={true}
        onClose={jest.fn()}
        correlationId="test-123"
      />
    );

    // Switch to evidence tab
    const evidenceTab = screen.getByRole('tab', { name: /evidence/i });
    fireEvent.click(evidenceTab);

    await waitFor(() => {
      expect(screen.getByText('No evidence files found')).toBeInTheDocument();
    });
  });

  it('meets accessibility requirements', () => {
    render(
      <SubcategoryDrawer
        subcategory={mockSubcategory}
        isOpen={true}
        onClose={jest.fn()}
        correlationId="test-123"
      />
    );

    // Check ARIA attributes
    expect(screen.getByRole('dialog')).toHaveAttribute('aria-modal', 'true');
    expect(screen.getByRole('dialog')).toHaveAttribute('aria-labelledby', 'drawer-title');
    
    // Check tab accessibility
    const tabs = screen.getAllByRole('tab');
    tabs.forEach(tab => {
      expect(tab).toHaveAttribute('aria-selected');
      expect(tab).toHaveAttribute('aria-controls');
    });

    // Check score buttons have proper ARIA
    const scoreButtons = screen.getAllByRole('button').filter(btn => 
      ['1', '2', '3', '4', '5'].includes(btn.textContent || '')
    );
    scoreButtons.forEach(button => {
      expect(button).toHaveAttribute('aria-pressed');
    });
  });

  it('focuses on score input when opened', () => {
    render(
      <SubcategoryDrawer
        subcategory={mockSubcategory}
        isOpen={true}
        onClose={jest.fn()}
        correlationId="test-123"
      />
    );

    const scoreSlider = screen.getByRole('slider');
    expect(scoreSlider).toHaveFocus();
  });

  it('includes correlation ID in console logs', () => {
    const consoleSpy = jest.spyOn(console, 'log').mockImplementation();
    
    render(
      <SubcategoryDrawer
        subcategory={mockSubcategory}
        isOpen={true}
        onClose={jest.fn()}
        correlationId="test-correlation-123"
      />
    );

    expect(consoleSpy).toHaveBeenCalledWith(
      expect.stringContaining('[test-correlation-123]')
    );

    consoleSpy.mockRestore();
  });
});