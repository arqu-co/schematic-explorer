/**
 * Tests for FileList component.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Theme } from '@radix-ui/themes';
import { FileList } from './FileList';
import type { SchematicFile } from '../types';

// Wrapper component for Radix UI Theme
function TestWrapper({ children }: { children: React.ReactNode }) {
  return <Theme>{children}</Theme>;
}

// Helper to create mock schematic files
function createMockFile(overrides: Partial<SchematicFile> = {}): SchematicFile {
  return {
    name: 'test-file.json',
    stem: 'test-file',
    entries: [],
    insights: null,
    ...overrides,
  };
}

describe('FileList', () => {
  describe('rendering', () => {
    it('renders the Files heading', () => {
      render(
        <TestWrapper>
          <FileList files={[]} selectedFile={null} onFileSelect={() => {}} />
        </TestWrapper>
      );

      expect(screen.getByText('Files')).toBeInTheDocument();
    });

    it('renders file names', () => {
      const files = [
        createMockFile({ name: 'file1.json', stem: 'file1' }),
        createMockFile({ name: 'file2.json', stem: 'file2' }),
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
        createMockFile({
          stem: 'test',
          entries: [
            { carrier: 'Carrier A', layer_limit: '$50M' },
            { carrier: 'Carrier B', layer_limit: '$50M' },
          ] as SchematicFile['entries'],
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
        createMockFile({
          stem: 'test',
          entries: [
            { carrier: 'Carrier A', layer_limit: '$50M' },
            { carrier: 'Carrier B', layer_limit: '$25M' },
          ] as SchematicFile['entries'],
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
      const file = createMockFile({ stem: 'clickable' });

      render(
        <TestWrapper>
          <FileList files={[file]} selectedFile={null} onFileSelect={onFileSelect} />
        </TestWrapper>
      );

      fireEvent.click(screen.getByText('clickable'));
      expect(onFileSelect).toHaveBeenCalledWith(file);
    });

    it('applies selected class to selected file', () => {
      const file = createMockFile({ stem: 'selected-file' });

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
      const file = createMockFile({
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
      const file = createMockFile({
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
      const file = createMockFile({
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
      const file = createMockFile({
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
      render(
        <TestWrapper>
          <FileList files={[]} selectedFile={null} onFileSelect={() => {}} />
        </TestWrapper>
      );

      expect(screen.getByText('Files')).toBeInTheDocument();
    });
  });
});
