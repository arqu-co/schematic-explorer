/**
 * Resizable and collapsible panel component.
 */

import { useState, useRef, useCallback, useEffect, type ReactNode } from 'react';
import { Box, Flex, IconButton, Heading, Text } from '@radix-ui/themes';

interface ResizablePanelProps {
  /** Panel title displayed in header */
  title: string;
  /** Panel content */
  children: ReactNode;
  /** Initial width in pixels */
  defaultWidth: number;
  /** Minimum width in pixels */
  minWidth?: number;
  /** Maximum width in pixels */
  maxWidth?: number;
  /** Which side has the resize handle: 'left' or 'right' */
  resizeFrom: 'left' | 'right';
  /** CSS class name for the panel */
  className?: string;
  /** Storage key for persisting width/collapsed state */
  storageKey?: string;
}

/**
 * A panel that can be resized by dragging and collapsed/expanded.
 */
export function ResizablePanel({
  title,
  children,
  defaultWidth,
  minWidth = 150,
  maxWidth = 500,
  resizeFrom,
  className = '',
  storageKey,
}: ResizablePanelProps) {
  // Load initial state from localStorage
  const getInitialWidth = () => {
    if (storageKey) {
      const saved = localStorage.getItem(`${storageKey}-width`);
      if (saved) return parseInt(saved, 10);
    }
    return defaultWidth;
  };

  const getInitialCollapsed = () => {
    if (storageKey) {
      const saved = localStorage.getItem(`${storageKey}-collapsed`);
      if (saved) return saved === 'true';
    }
    return false;
  };

  const [width, setWidth] = useState(getInitialWidth);
  const [isCollapsed, setIsCollapsed] = useState(getInitialCollapsed);
  const [isResizing, setIsResizing] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const startXRef = useRef(0);
  const startWidthRef = useRef(0);

  // Persist state to localStorage
  useEffect(() => {
    if (storageKey) {
      localStorage.setItem(`${storageKey}-width`, String(width));
    }
  }, [width, storageKey]);

  useEffect(() => {
    if (storageKey) {
      localStorage.setItem(`${storageKey}-collapsed`, String(isCollapsed));
    }
  }, [isCollapsed, storageKey]);

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      setIsResizing(true);
      startXRef.current = e.clientX;
      startWidthRef.current = width;
    },
    [width]
  );

  const handleMouseMove = useCallback(
    (e: MouseEvent) => {
      if (!isResizing) return;

      const delta = resizeFrom === 'right'
        ? e.clientX - startXRef.current
        : startXRef.current - e.clientX;

      const newWidth = Math.min(maxWidth, Math.max(minWidth, startWidthRef.current + delta));
      setWidth(newWidth);
    },
    [isResizing, minWidth, maxWidth, resizeFrom]
  );

  const handleMouseUp = useCallback(() => {
    setIsResizing(false);
  }, []);

  useEffect(() => {
    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
  }, [isResizing, handleMouseMove, handleMouseUp]);

  const toggleCollapse = () => {
    setIsCollapsed(!isCollapsed);
  };

  const chevronIcon = isCollapsed
    ? resizeFrom === 'right'
      ? '‹'
      : '›'
    : resizeFrom === 'right'
      ? '›'
      : '‹';

  if (isCollapsed) {
    return (
      <Box
        ref={panelRef}
        className={`resizable-panel collapsed ${className}`}
        style={{ width: 40 }}
      >
        <Flex direction="column" align="center" gap="2" py="2">
          <IconButton
            variant="ghost"
            size="1"
            onClick={toggleCollapse}
            aria-label={`Expand ${title}`}
          >
            {chevronIcon}
          </IconButton>
          <Text
            size="1"
            color="gray"
            style={{
              writingMode: 'vertical-rl',
              textOrientation: 'mixed',
              transform: 'rotate(180deg)',
            }}
          >
            {title}
          </Text>
        </Flex>
      </Box>
    );
  }

  return (
    <Box
      ref={panelRef}
      className={`resizable-panel ${className}`}
      style={{ width, position: 'relative' }}
    >
      {/* Resize handle */}
      <Box
        className={`resize-handle resize-handle-${resizeFrom}`}
        onMouseDown={handleMouseDown}
        style={{
          position: 'absolute',
          top: 0,
          bottom: 0,
          width: 6,
          cursor: 'col-resize',
          ...(resizeFrom === 'right' ? { right: -3 } : { left: -3 }),
        }}
      />

      {/* Header with collapse button */}
      <Flex justify="between" align="center" mb="2">
        <Heading size="3">{title}</Heading>
        <IconButton
          variant="ghost"
          size="1"
          onClick={toggleCollapse}
          aria-label={`Collapse ${title}`}
        >
          {chevronIcon}
        </IconButton>
      </Flex>

      {/* Content */}
      <Box className="resizable-panel-content">{children}</Box>
    </Box>
  );
}
