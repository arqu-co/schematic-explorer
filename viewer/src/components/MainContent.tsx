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

function ExcelViewer({ stem, highlightRange }: ExcelViewerProps) {
  const [grid, setGrid] = useState<{ value: string; isMerged: boolean; isOrigin: boolean }[][] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hiddenCols, setHiddenCols] = useState<Set<number>>(new Set());
  const [colWidths, setColWidths] = useState<Map<number, number>>(new Map());
  const [resizingCol, setResizingCol] = useState<number | null>(null);
  const tableRef = useRef<HTMLTableElement>(null);
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
        setColWidths(new Map());
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load Excel');
      } finally {
        setLoading(false);
      }
    }
    loadExcel();
  }, [stem]);

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

  // Highlight effect
  useEffect(() => {
    if (!tableRef.current || !highlightRange || !grid) return;

    // Clear previous highlights
    tableRef.current.querySelectorAll('.cell-highlight').forEach((el) => {
      el.classList.remove('cell-highlight');
    });

    const parsed = parseRange(highlightRange);
    if (!parsed) return;

    const { startCol, startRow, endCol, endRow } = parsed;

    // Find and highlight cells (accounting for header row/col and hidden columns)
    let firstHighlighted: Element | null = null;
    for (let r = startRow; r <= endRow; r++) {
      for (let c = startCol; c <= endCol; c++) {
        if (hiddenCols.has(c)) continue;
        // Calculate visual column index accounting for hidden columns
        let visualCol = 1; // Start at 1 for row number column
        for (let i = 0; i <= c; i++) {
          if (!hiddenCols.has(i)) visualCol++;
        }
        const cell = tableRef.current.querySelector(
          `tr:nth-child(${r + 2}) > *:nth-child(${visualCol})`
        ) as HTMLElement;
        if (cell) {
          cell.classList.add('cell-highlight');
          if (!firstHighlighted) firstHighlighted = cell;
        }
      }
    }

    if (firstHighlighted) {
      firstHighlighted.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'center' });
    }
  }, [highlightRange, grid, hiddenCols]);

  const handleResizeStart = (colIdx: number, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setResizingCol(colIdx);
    startXRef.current = e.clientX;
    const th = e.currentTarget.parentElement as HTMLElement;
    startWidthRef.current = th.offsetWidth;
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

  const showAllColumns = () => {
    setHiddenCols(new Set());
  };

  if (loading) return <Text color="gray">Loading spreadsheet...</Text>;
  if (error) return <Text color="red">{error}</Text>;
  if (!grid || grid.length === 0) return <Text color="gray">No data</Text>;

  const numCols = grid[0]?.length || 0;
  const hasHiddenCols = hiddenCols.size > 0;

  return (
    <Box className="excel-viewer">
      {hasHiddenCols && (
        <Flex gap="2" mb="2" align="center" className="excel-toolbar">
          <Text size="1" color="gray">
            {hiddenCols.size} column(s) hidden
          </Text>
          <button className="excel-show-all-btn" onClick={showAllColumns}>
            Show all
          </button>
        </Flex>
      )}
      <table ref={tableRef} id="excel-table">
        <thead>
          <tr className="excel-header-row">
            <th className="excel-corner-cell"></th>
            {Array.from({ length: numCols }, (_, c) => {
              if (hiddenCols.has(c)) return null;
              const width = colWidths.get(c);
              return (
                <th
                  key={c}
                  className="excel-col-header"
                  style={width ? { width, minWidth: width, maxWidth: width } : undefined}
                >
                  <Flex align="center" justify="between" gap="1">
                    <span>{numToCol(c + 1)}</span>
                    <Flex gap="1">
                      <button
                        className="col-hide-btn"
                        onClick={() => toggleColumnHidden(c)}
                        title={`Hide column ${numToCol(c + 1)}`}
                      >
                        ×
                      </button>
                    </Flex>
                  </Flex>
                  <div
                    className="col-resize-handle"
                    onMouseDown={(e) => handleResizeStart(c, e)}
                  />
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {grid.map((row, rowIdx) => (
            <tr key={rowIdx}>
              <th className="excel-row-header">{rowIdx + 1}</th>
              {row.map((cell, colIdx) => {
                if (hiddenCols.has(colIdx)) return null;
                const width = colWidths.get(colIdx);
                return (
                  <td
                    key={colIdx}
                    className={cell.isMerged ? 'merged-cell' : ''}
                    style={width ? { width, minWidth: width, maxWidth: width } : undefined}
                  >
                    {cell.value}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
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
