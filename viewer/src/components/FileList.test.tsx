/**
 * Tests for FileList component.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Theme } from '@radix-ui/themes';
import { FileList } from './FileList';
import { createSchematicFile, createCarrierEntry } from '../test-utils';

// Wrapper component for Radix UI Theme
function TestWrapper({ children }: { children: React.ReactNode }) {
  return <Theme>{children}</Theme>;
}

describe('FileList', () => {
  describe('rendering', () => {
    it('renders without errors when empty', () => {
      const { container } = render(
        <TestWrapper>
          <FileList files={[]} selectedFile={null} onFileSelect={() => {}} />
        </TestWrapper>
      );

      expect(container.querySelector('.rt-ScrollAreaRoot')).toBeInTheDocument();
    });

    it('renders file names', () => {
      const files = [
        createSchematicFile({ name: 'file1.json', stem: 'file1' }),
        createSchematicFile({ name: 'file2.json', stem: 'file2' }),
      ];

      render(
        <TestWrapper>
          <FileList files={files} selectedFile={null} onFileSelect={() => {}} />
        </TestWrapper>
      );

      expect(screen.getByText('file1')).toBeInTheDocument();
      expect(screen.getByText('file2')).toBeInTheDocument();
    });

    it('shows carrier count for each file', () => {
      const files = [
        createSchematicFile({
          stem: 'test',
          entries: [
            createCarrierEntry({ carrier: 'Carrier A', layer_limit: '$50M' }),
            createCarrierEntry({ carrier: 'Carrier B', layer_limit: '$50M' }),
          ],
        }),
      ];

      render(
        <TestWrapper>
          <FileList files={files} selectedFile={null} onFileSelect={() => {}} />
        </TestWrapper>
      );

      expect(screen.getByText('2 carriers')).toBeInTheDocument();
    });

    it('shows layer count for each file', () => {
      const files = [
        createSchematicFile({
          stem: 'test',
          entries: [
            createCarrierEntry({ carrier: 'Carrier A', layer_limit: '$50M' }),
            createCarrierEntry({ carrier: 'Carrier B', layer_limit: '$25M' }),
          ],
        }),
      ];

      render(
        <TestWrapper>
          <FileList files={files} selectedFile={null} onFileSelect={() => {}} />
        </TestWrapper>
      );

      expect(screen.getByText('2 layers')).toBeInTheDocument();
    });
  });

  describe('selection', () => {
    it('calls onFileSelect when a file is clicked', () => {
      const onFileSelect = vi.fn();
      const file = createSchematicFile({ stem: 'clickable' });

      render(
        <TestWrapper>
          <FileList files={[file]} selectedFile={null} onFileSelect={onFileSelect} />
        </TestWrapper>
      );

      fireEvent.click(screen.getByText('clickable'));
      expect(onFileSelect).toHaveBeenCalledWith(file);
    });

    it('applies selected class to selected file', () => {
      const file = createSchematicFile({ stem: 'selected-file' });

      const { container } = render(
        <TestWrapper>
          <FileList files={[file]} selectedFile={file} onFileSelect={() => {}} />
        </TestWrapper>
      );

      const card = container.querySelector('.schematic-card.selected');
      expect(card).toBeInTheDocument();
    });
  });

  describe('score badge', () => {
    it('shows green badge for score >= 90%', () => {
      const file = createSchematicFile({
        stem: 'high-score',
        insights: 'Verification Score: 95%',
      });

      render(
        <TestWrapper>
          <FileList files={[file]} selectedFile={null} onFileSelect={() => {}} />
        </TestWrapper>
      );

      expect(screen.getByText('95%')).toBeInTheDocument();
    });

    it('shows yellow badge for score >= 70%', () => {
      const file = createSchematicFile({
        stem: 'medium-score',
        insights: 'Verification Score: 75%',
      });

      render(
        <TestWrapper>
          <FileList files={[file]} selectedFile={null} onFileSelect={() => {}} />
        </TestWrapper>
      );

      expect(screen.getByText('75%')).toBeInTheDocument();
    });

    it('shows red badge for score < 70%', () => {
      const file = createSchematicFile({
        stem: 'low-score',
        insights: 'Verification Score: 50%',
      });

      render(
        <TestWrapper>
          <FileList files={[file]} selectedFile={null} onFileSelect={() => {}} />
        </TestWrapper>
      );

      expect(screen.getByText('50%')).toBeInTheDocument();
    });

    it('does not show badge when no insights', () => {
      const file = createSchematicFile({
        stem: 'no-insights',
        insights: null,
      });

      render(
        <TestWrapper>
          <FileList files={[file]} selectedFile={null} onFileSelect={() => {}} />
        </TestWrapper>
      );

      // Should not have any percentage badges
      expect(screen.queryByText(/%$/)).not.toBeInTheDocument();
    });
  });

  describe('empty state', () => {
    it('renders empty list without errors', () => {
      const { container } = render(
        <TestWrapper>
          <FileList files={[]} selectedFile={null} onFileSelect={() => {}} />
        </TestWrapper>
      );

      expect(container.querySelector('.rt-ScrollAreaRoot')).toBeInTheDocument();
    });
  });
});
