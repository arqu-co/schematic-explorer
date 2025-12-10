/**
 * Main content area with tab views.
 */

import React, { useEffect, useState, useRef } from 'react';
import { Box, Tabs, Flex, Text, Badge, Table, Code } from '@radix-ui/themes';
import * as XLSX from 'xlsx';
import type { CarrierEntry, Layer } from '../types';
import { formatCurrency, formatPercent, hexToRgba, numToCol, parseRange } from '../utils';
import { getInputExcelUrl } from '../api';

// =============================================================================
// Tower Visualization
// =============================================================================

/**
 * Props for the TowerVisualization component.
 */
interface TowerVisualizationProps {
  /** Layers to display in the tower */
  layers: Layer[];
  /** Optional callback when a carrier cell is clicked */
  onCellClick?: (entry: CarrierEntry) => void;
}

function TowerVisualization({ layers, onCellClick }: TowerVisualizationProps) {
  return (
    <Box className="tower-viz">
      {layers.map((layer, idx) => (
        <Box
          key={layer.limit}
          className="tower-layer"
          style={{
            marginBottom: idx < layers.length - 1 ? '2px' : 0,
          }}
        >
          <Flex align="center" gap="3" className="layer-header">
            <Badge size="2" color="blue">
              {layer.limit}
            </Badge>
            <Text size="1" color="gray">
              {layer.entries.length} carrier{layer.entries.length !== 1 ? 's' : ''}
            </Text>
            {layer.totalPremium > 0 && (
              <Text size="1" weight="medium">
                {formatCurrency(layer.totalPremium)}
              </Text>
            )}
          </Flex>
          <Flex gap="2" wrap="wrap" className="layer-carriers">
            {layer.entries.map((entry, entryIdx) => (
              <Box
                key={entryIdx}
                className="carrier-block"
                style={{
                  backgroundColor: entry.fill_color ? hexToRgba(entry.fill_color, 0.5) : 'var(--accent-3)',
                  flex: entry.participation_pct ? `${entry.participation_pct * 100}` : '1',
                  minWidth: '120px',
                  cursor: onCellClick ? 'pointer' : 'default',
                }}
                onClick={() => onCellClick?.(entry)}
              >
                <Text size="2" weight="medium" className="carrier-name">
                  {entry.carrier}
                </Text>
                <Flex gap="3" wrap="wrap" mt="1">
                  {entry.participation_pct && (
                    <Text size="1" color="gray">
                      {formatPercent(entry.participation_pct)}
                    </Text>
                  )}
                  {entry.premium && (
                    <Text size="1" color="gray">
                      {formatCurrency(entry.premium)}
                    </Text>
                  )}
                  {entry.attachment_point && (
                    <Text size="1" color="gray">
                      xs {entry.attachment_point}
                    </Text>
                  )}
                </Flex>
                <Text size="1" color="gray" style={{ opacity: 0.6 }}>
                  {entry.excel_range}
                </Text>
              </Box>
            ))}
          </Flex>
        </Box>
      ))}
    </Box>
  );
}

// =============================================================================
// Carrier Table
// =============================================================================

/**
 * Props for the CarrierTable component.
 */
interface CarrierTableProps {
  /** Carrier entries to display in the table */
  entries: CarrierEntry[];
}

function CarrierTable({ entries }: CarrierTableProps) {
  return (
    <Table.Root>
      <Table.Header>
        <Table.Row>
          <Table.ColumnHeaderCell>Layer</Table.ColumnHeaderCell>
          <Table.ColumnHeaderCell>Carrier</Table.ColumnHeaderCell>
          <Table.ColumnHeaderCell>Participation</Table.ColumnHeaderCell>
          <Table.ColumnHeaderCell>Premium</Table.ColumnHeaderCell>
          <Table.ColumnHeaderCell>Attachment</Table.ColumnHeaderCell>
          <Table.ColumnHeaderCell>Cell</Table.ColumnHeaderCell>
        </Table.Row>
      </Table.Header>
      <Table.Body>
        {entries.map((entry, idx) => (
          <Table.Row key={idx}>
            <Table.Cell>
              <Badge>{entry.layer_limit}</Badge>
            </Table.Cell>
            <Table.Cell>
              <Text weight="medium">{entry.carrier}</Text>
              {entry.terms && (
                <Text size="1" color="gray" as="div">
                  {entry.terms}
                </Text>
              )}
            </Table.Cell>
            <Table.Cell>{formatPercent(entry.participation_pct)}</Table.Cell>
            <Table.Cell>{formatCurrency(entry.premium)}</Table.Cell>
            <Table.Cell>{entry.attachment_point || '—'}</Table.Cell>
            <Table.Cell>
              <Code size="1">{entry.excel_range}</Code>
            </Table.Cell>
          </Table.Row>
        ))}
      </Table.Body>
    </Table.Root>
  );
}

// =============================================================================
// Excel Viewer
// =============================================================================

/**
 * Props for the ExcelViewer component.
 */
interface ExcelViewerProps {
  /** File stem to load Excel data from */
  stem: string;
  /** Optional Excel range to highlight (e.g., "B5:D7") */
  highlightRange?: string | null;
}

/**
 * Build a grid of cells from an Excel sheet, expanding merged cells.
 * Returns a 2D array where each element is { value, isMerged, isOrigin }.
 */
function buildCellGrid(sheet: XLSX.WorkSheet): { value: string; isMerged: boolean; isOrigin: boolean }[][] {
  const range = XLSX.utils.decode_range(sheet['!ref'] || 'A1');
  const numRows = range.e.r - range.s.r + 1;
  const numCols = range.e.c - range.s.c + 1;

  // Initialize grid with empty cells
  const grid: { value: string; isMerged: boolean; isOrigin: boolean }[][] = [];
  for (let r = 0; r < numRows; r++) {
    grid[r] = [];
    for (let c = 0; c < numCols; c++) {
      grid[r][c] = { value: '', isMerged: false, isOrigin: false };
    }
  }

  // Build merged cell lookup
  const mergedRanges = sheet['!merges'] || [];
  const mergedCells = new Map<string, { startRow: number; startCol: number }>();
  for (const merge of mergedRanges) {
    for (let r = merge.s.r; r <= merge.e.r; r++) {
      for (let c = merge.s.c; c <= merge.e.c; c++) {
        const key = `${r},${c}`;
        mergedCells.set(key, { startRow: merge.s.r, startCol: merge.s.c });
      }
    }
  }

  // Fill grid with cell values
  for (let r = 0; r < numRows; r++) {
    for (let c = 0; c < numCols; c++) {
      const cellAddr = XLSX.utils.encode_cell({ r: r + range.s.r, c: c + range.s.c });
      const cell = sheet[cellAddr];
      const mergeInfo = mergedCells.get(`${r + range.s.r},${c + range.s.c}`);

      if (mergeInfo) {
        const isOrigin = mergeInfo.startRow === r + range.s.r && mergeInfo.startCol === c + range.s.c;
        grid[r][c] = {
          value: isOrigin && cell ? String(cell.v ?? '') : '',
          isMerged: !isOrigin,
          isOrigin,
        };
      } else {
        grid[r][c] = {
          value: cell ? String(cell.v ?? '') : '',
          isMerged: false,
          isOrigin: false,
        };
      }
    }
  }

  return grid;
}

// Virtual scrolling constants
const ROW_HEIGHT = 26;
const COL_WIDTH = 80;
const ROW_HEADER_WIDTH = 50;
const COL_HEADER_HEIGHT = 30;
const BUFFER_ROWS = 5;
const BUFFER_COLS = 3;

function ExcelViewer({ stem, highlightRange }: ExcelViewerProps) {
  const [grid, setGrid] = useState<{ value: string; isMerged: boolean; isOrigin: boolean }[][] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hiddenCols, setHiddenCols] = useState<Set<number>>(new Set());
  const [hiddenRows, setHiddenRows] = useState<Set<number>>(new Set());
  const [colWidths, setColWidths] = useState<Map<number, number>>(new Map());
  const [resizingCol, setResizingCol] = useState<number | null>(null);
  const [scrollPos, setScrollPos] = useState({ top: 0, left: 0 });
  const [containerSize, setContainerSize] = useState({ width: 0, height: 0 });
  const containerRef = useRef<HTMLDivElement>(null);
  const startXRef = useRef(0);
  const startWidthRef = useRef(0);

  useEffect(() => {
    async function loadExcel() {
      setLoading(true);
      setError(null);
      try {
        const response = await fetch(getInputExcelUrl(stem));
        if (!response.ok) throw new Error('Failed to load Excel file');
        const arrayBuffer = await response.arrayBuffer();
        const workbook = XLSX.read(arrayBuffer, { type: 'array', cellStyles: true });
        const firstSheet = workbook.Sheets[workbook.SheetNames[0]];
        const cellGrid = buildCellGrid(firstSheet);
        setGrid(cellGrid);
        setHiddenCols(new Set());
        setHiddenRows(new Set());
        setColWidths(new Map());
        setScrollPos({ top: 0, left: 0 });
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load Excel');
      } finally {
        setLoading(false);
      }
    }
    loadExcel();
  }, [stem]);

  // Observe container size
  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry) {
        setContainerSize({
          width: entry.contentRect.width,
          height: entry.contentRect.height,
        });
      }
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  // Mouse move handler for column resizing
  useEffect(() => {
    if (resizingCol === null) return;

    const handleMouseMove = (e: MouseEvent) => {
      const delta = e.clientX - startXRef.current;
      const newWidth = Math.max(30, startWidthRef.current + delta);
      setColWidths((prev) => new Map(prev).set(resizingCol, newWidth));
    };

    const handleMouseUp = () => {
      setResizingCol(null);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [resizingCol]);

  // Build visible row/col indices (excluding hidden)
  const visibleRows = React.useMemo(() => {
    if (!grid) return [];
    return grid.map((_, i) => i).filter((i) => !hiddenRows.has(i));
  }, [grid, hiddenRows]);

  const visibleCols = React.useMemo(() => {
    if (!grid || grid.length === 0) return [];
    return grid[0].map((_, i) => i).filter((i) => !hiddenCols.has(i));
  }, [grid, hiddenCols]);

  // Calculate column positions
  const colPositions = React.useMemo(() => {
    const positions: number[] = [];
    let x = 0;
    for (const colIdx of visibleCols) {
      positions.push(x);
      x += colWidths.get(colIdx) ?? COL_WIDTH;
    }
    positions.push(x); // Total width at end
    return positions;
  }, [visibleCols, colWidths]);

  const totalWidth = colPositions[colPositions.length - 1] ?? 0;
  const totalHeight = visibleRows.length * ROW_HEIGHT;

  // Calculate visible range based on scroll position
  const getVisibleRange = React.useCallback(() => {
    const viewTop = scrollPos.top;
    const viewBottom = scrollPos.top + containerSize.height - COL_HEADER_HEIGHT;
    const viewLeft = scrollPos.left;
    const viewRight = scrollPos.left + containerSize.width - ROW_HEADER_WIDTH;

    // Find row range
    const startRowIdx = Math.max(0, Math.floor(viewTop / ROW_HEIGHT) - BUFFER_ROWS);
    const endRowIdx = Math.min(visibleRows.length - 1, Math.ceil(viewBottom / ROW_HEIGHT) + BUFFER_ROWS);

    // Find column range using binary search
    let startColIdx = 0;
    let endColIdx = visibleCols.length - 1;
    for (let i = 0; i < colPositions.length - 1; i++) {
      if (colPositions[i + 1] >= viewLeft) {
        startColIdx = Math.max(0, i - BUFFER_COLS);
        break;
      }
    }
    for (let i = colPositions.length - 2; i >= 0; i--) {
      if (colPositions[i] <= viewRight) {
        endColIdx = Math.min(visibleCols.length - 1, i + BUFFER_COLS);
        break;
      }
    }

    return { startRowIdx, endRowIdx, startColIdx, endColIdx };
  }, [scrollPos, containerSize, visibleRows.length, visibleCols.length, colPositions]);

  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const target = e.currentTarget;
    setScrollPos({ top: target.scrollTop, left: target.scrollLeft });
  };

  // Scroll to highlighted range
  useEffect(() => {
    if (!containerRef.current || !highlightRange || !grid) return;

    const parsed = parseRange(highlightRange);
    if (!parsed) return;

    const { startRow, startCol } = parsed;

    // Find visual indices
    const visualRowIdx = visibleRows.indexOf(startRow);
    const visualColIdx = visibleCols.indexOf(startCol);
    if (visualRowIdx === -1 || visualColIdx === -1) return;

    const targetTop = visualRowIdx * ROW_HEIGHT;
    const targetLeft = colPositions[visualColIdx] ?? 0;

    containerRef.current.scrollTo({
      top: Math.max(0, targetTop - containerSize.height / 2 + ROW_HEIGHT),
      left: Math.max(0, targetLeft - containerSize.width / 2 + COL_WIDTH),
      behavior: 'smooth',
    });
  }, [highlightRange, grid, visibleRows, visibleCols, colPositions, containerSize]);

  const handleResizeStart = (colIdx: number, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setResizingCol(colIdx);
    startXRef.current = e.clientX;
    startWidthRef.current = colWidths.get(colIdx) ?? COL_WIDTH;
  };

  const toggleColumnHidden = (colIdx: number) => {
    setHiddenCols((prev) => {
      const next = new Set(prev);
      if (next.has(colIdx)) {
        next.delete(colIdx);
      } else {
        next.add(colIdx);
      }
      return next;
    });
  };

  const showAll = () => {
    setHiddenCols(new Set());
    setHiddenRows(new Set());
  };

  const hideEmptyRowsAndCols = () => {
    if (!grid) return;

    const numRows = grid.length;
    const numCols = grid[0]?.length || 0;

    const emptyCols = new Set<number>();
    for (let c = 0; c < numCols; c++) {
      let isEmpty = true;
      for (let r = 0; r < numRows; r++) {
        if (grid[r][c].value.trim() !== '') {
          isEmpty = false;
          break;
        }
      }
      if (isEmpty) emptyCols.add(c);
    }

    const emptyRows = new Set<number>();
    for (let r = 0; r < numRows; r++) {
      let isEmpty = true;
      for (let c = 0; c < numCols; c++) {
        if (grid[r][c].value.trim() !== '') {
          isEmpty = false;
          break;
        }
      }
      if (isEmpty) emptyRows.add(r);
    }

    setHiddenCols(emptyCols);
    setHiddenRows(emptyRows);
  };

  if (loading) return <Text color="gray">Loading spreadsheet...</Text>;
  if (error) return <Text color="red">{error}</Text>;
  if (!grid || grid.length === 0) return <Text color="gray">No data</Text>;

  const hasHidden = hiddenCols.size > 0 || hiddenRows.size > 0;
  const { startRowIdx, endRowIdx, startColIdx, endColIdx } = getVisibleRange();

  // Parse highlight range for cell highlighting
  const highlightParsed = highlightRange ? parseRange(highlightRange) : null;
  const isHighlighted = (rowIdx: number, colIdx: number) => {
    if (!highlightParsed) return false;
    return (
      rowIdx >= highlightParsed.startRow &&
      rowIdx <= highlightParsed.endRow &&
      colIdx >= highlightParsed.startCol &&
      colIdx <= highlightParsed.endCol
    );
  };

  return (
    <Box className="excel-viewer">
      <Flex gap="2" mb="2" align="center" className="excel-toolbar">
        <button className="excel-toolbar-btn" onClick={hideEmptyRowsAndCols}>
          Hide empty
        </button>
        {hasHidden && (
          <>
            <Text size="1" color="gray">
              {hiddenCols.size > 0 && `${hiddenCols.size} col(s)`}
              {hiddenCols.size > 0 && hiddenRows.size > 0 && ', '}
              {hiddenRows.size > 0 && `${hiddenRows.size} row(s)`}
              {' hidden'}
            </Text>
            <button className="excel-show-all-btn" onClick={showAll}>
              Show all
            </button>
          </>
        )}
        <Text size="1" color="gray" style={{ marginLeft: 'auto' }}>
          {visibleRows.length} × {visibleCols.length}
        </Text>
      </Flex>

      <div
        ref={containerRef}
        className="excel-virtual-container"
        onScroll={handleScroll}
      >
        {/* Total scrollable area */}
        <div
          className="excel-virtual-content"
          style={{
            width: totalWidth + ROW_HEADER_WIDTH,
            height: totalHeight + COL_HEADER_HEIGHT,
          }}
        >
          {/* Corner cell (sticky) */}
          <div
            className="excel-corner-cell"
            style={{
              position: 'sticky',
              top: 0,
              left: 0,
              width: ROW_HEADER_WIDTH,
              height: COL_HEADER_HEIGHT,
              zIndex: 3,
            }}
          />

          {/* Column headers (sticky top) */}
          {visibleCols.slice(startColIdx, endColIdx + 1).map((colIdx, i) => {
            const visualIdx = startColIdx + i;
            const left = colPositions[visualIdx] + ROW_HEADER_WIDTH;
            const width = colWidths.get(colIdx) ?? COL_WIDTH;
            return (
              <div
                key={`col-${colIdx}`}
                className="excel-col-header"
                style={{
                  position: 'absolute',
                  top: 0,
                  left,
                  width,
                  height: COL_HEADER_HEIGHT,
                  transform: `translateY(${scrollPos.top}px)`,
                }}
              >
                <Flex align="center" justify="between" gap="1" style={{ height: '100%', padding: '0 4px' }}>
                  <span>{numToCol(colIdx + 1)}</span>
                  <button
                    className="col-hide-btn"
                    onClick={() => toggleColumnHidden(colIdx)}
                    title={`Hide column ${numToCol(colIdx + 1)}`}
                  >
                    ×
                  </button>
                </Flex>
                <div
                  className="col-resize-handle"
                  onMouseDown={(e) => handleResizeStart(colIdx, e)}
                />
              </div>
            );
          })}

          {/* Row headers (sticky left) */}
          {visibleRows.slice(startRowIdx, endRowIdx + 1).map((rowIdx, i) => {
            const visualIdx = startRowIdx + i;
            const top = visualIdx * ROW_HEIGHT + COL_HEADER_HEIGHT;
            return (
              <div
                key={`row-${rowIdx}`}
                className="excel-row-header"
                style={{
                  position: 'absolute',
                  top,
                  left: 0,
                  width: ROW_HEADER_WIDTH,
                  height: ROW_HEIGHT,
                  transform: `translateX(${scrollPos.left}px)`,
                }}
              >
                {rowIdx + 1}
              </div>
            );
          })}

          {/* Data cells */}
          {visibleRows.slice(startRowIdx, endRowIdx + 1).map((rowIdx, ri) => {
            const visualRowIdx = startRowIdx + ri;
            const top = visualRowIdx * ROW_HEIGHT + COL_HEADER_HEIGHT;

            return visibleCols.slice(startColIdx, endColIdx + 1).map((colIdx, ci) => {
              const visualColIdx = startColIdx + ci;
              const left = colPositions[visualColIdx] + ROW_HEADER_WIDTH;
              const width = colWidths.get(colIdx) ?? COL_WIDTH;
              const cell = grid[rowIdx][colIdx];
              const highlighted = isHighlighted(rowIdx, colIdx);

              return (
                <div
                  key={`${rowIdx}-${colIdx}`}
                  className={`excel-cell ${cell.isMerged ? 'merged-cell' : ''} ${highlighted ? 'cell-highlight' : ''}`}
                  style={{
                    position: 'absolute',
                    top,
                    left,
                    width,
                    height: ROW_HEIGHT,
                  }}
                >
                  {cell.value}
                </div>
              );
            });
          })}
        </div>
      </div>
    </Box>
  );
}

// =============================================================================
// Main Content Component
// =============================================================================

/**
 * Props for the MainContent component.
 */
interface MainContentProps {
  /** All carrier entries for the selected file */
  entries: CarrierEntry[];
  /** Entries grouped by layer for tower view */
  layers: Layer[];
  /** File stem for loading Excel data */
  stem: string;
  /** Currently active tab (tower, table, json, excel) */
  activeTab: string;
  /** Callback when tab is changed */
  onTabChange: (tab: string) => void;
  /** Entry to highlight in Excel view, or null */
  highlightEntry: CarrierEntry | null;
  /** Callback when a carrier cell is clicked */
  onCellClick: (entry: CarrierEntry) => void;
}

/**
 * Main content area with tab views for exploring schematic data.
 * Supports tower visualization, table view, raw JSON, and Excel preview.
 */
export function MainContent({
  entries,
  layers,
  stem,
  activeTab,
  onTabChange,
  highlightEntry,
  onCellClick,
}: MainContentProps) {
  return (
    <Box className="main-content">
      <Tabs.Root value={activeTab} onValueChange={onTabChange}>
        <Tabs.List>
          <Tabs.Trigger value="tower">Tower View</Tabs.Trigger>
          <Tabs.Trigger value="table">Table View</Tabs.Trigger>
          <Tabs.Trigger value="json">Raw JSON</Tabs.Trigger>
          <Tabs.Trigger value="excel">Excel</Tabs.Trigger>
        </Tabs.List>
      </Tabs.Root>

      <div className="tab-scroll-container">
        {activeTab === 'tower' && <TowerVisualization layers={layers} onCellClick={onCellClick} />}
        {activeTab === 'table' && <CarrierTable entries={entries} />}
        {activeTab === 'json' && <pre className="json-content">{JSON.stringify(entries, null, 2)}</pre>}
        {activeTab === 'excel' && <ExcelViewer stem={stem} highlightRange={highlightEntry?.excel_range ?? null} />}
      </div>
    </Box>
  );
}
