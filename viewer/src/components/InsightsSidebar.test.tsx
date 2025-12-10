/**
 * Tests for InsightsSidebar component.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Theme } from '@radix-ui/themes';
import { InsightsSidebar } from './InsightsSidebar';

// Wrapper component for Radix UI Theme
function TestWrapper({ children }: { children: React.ReactNode }) {
  return <Theme>{children}</Theme>;
}

describe('InsightsSidebar', () => {
  describe('rendering', () => {
    it('renders the Insights heading', () => {
      render(
        <TestWrapper>
          <InsightsSidebar insights={null} />
        </TestWrapper>
      );

      expect(screen.getByText('Insights')).toBeInTheDocument();
    });

    it('shows message when no insights available', () => {
      render(
        <TestWrapper>
          <InsightsSidebar insights={null} />
        </TestWrapper>
      );

      expect(screen.getByText('No verification insights available')).toBeInTheDocument();
    });
  });

  describe('score badge', () => {
    it('displays green badge for score >= 90%', () => {
      render(
        <TestWrapper>
          <InsightsSidebar insights="Verification Score: 95%" />
        </TestWrapper>
      );

      expect(screen.getByText('95% Accuracy')).toBeInTheDocument();
    });

    it('displays yellow badge for score >= 70% and < 90%', () => {
      render(
        <TestWrapper>
          <InsightsSidebar insights="Verification Score: 75%" />
        </TestWrapper>
      );

      expect(screen.getByText('75% Accuracy')).toBeInTheDocument();
    });

    it('displays red badge for score < 70%', () => {
      render(
        <TestWrapper>
          <InsightsSidebar insights="Verification Score: 50%" />
        </TestWrapper>
      );

      expect(screen.getByText('50% Accuracy')).toBeInTheDocument();
    });

    it('does not show badge when score is not in insights', () => {
      render(
        <TestWrapper>
          <InsightsSidebar insights="Some insights without a score" />
        </TestWrapper>
      );

      expect(screen.queryByText(/Accuracy/)).not.toBeInTheDocument();
    });
  });

  describe('markdown rendering', () => {
    it('renders markdown content', () => {
      const { container } = render(
        <TestWrapper>
          <InsightsSidebar insights="## Heading" />
        </TestWrapper>
      );

      // Look for h2 element with text
      const heading = container.querySelector('h2');
      expect(heading).toBeInTheDocument();
      expect(heading?.textContent).toBe('Heading');
    });

    it('renders plain text content', () => {
      render(
        <TestWrapper>
          <InsightsSidebar insights="This is plain text content" />
        </TestWrapper>
      );

      expect(screen.getByText('This is plain text content')).toBeInTheDocument();
    });
  });

  describe('edge cases', () => {
    it('handles empty string insights', () => {
      render(
        <TestWrapper>
          <InsightsSidebar insights="" />
        </TestWrapper>
      );

      // Should not crash and should render the component
      expect(screen.getByText('Insights')).toBeInTheDocument();
    });

    it('handles insights with only score', () => {
      render(
        <TestWrapper>
          <InsightsSidebar insights="Score: 80%" />
        </TestWrapper>
      );

      expect(screen.getByText('80% Accuracy')).toBeInTheDocument();
    });
  });
});
