/**
 * Main content area with tab views.
 */

import React, { useEffect, useState, useRef } from 'react';
import { Box, Tabs, Flex, Text, Badge, Table, Code } from '@radix-ui/themes';
import * as XLSX from 'xlsx';
import type { CarrierEntry, Layer } from '../types';
import { formatCurrency, formatPercent, hexToRgba, parseRange, sanitizeHtml } from '../utils';
import { getInputExcelUrl } from '../api';

// =============================================================================
// Tower Visualization
// =============================================================================

interface TowerVisualizationProps {
  layers: Layer[];
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

interface CarrierTableProps {
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

interface ExcelViewerProps {
  stem: string;
  highlightRange?: string | null;
}

function ExcelViewer({ stem, highlightRange }: ExcelViewerProps) {
  const [html, setHtml] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

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
        const htmlOutput = XLSX.utils.sheet_to_html(firstSheet, { editable: false, id: 'excel-table' });
        setHtml(htmlOutput);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load Excel');
      } finally {
        setLoading(false);
      }
    }
    loadExcel();
  }, [stem]);

  useEffect(() => {
    if (!containerRef.current || !highlightRange) return;

    // Clear previous highlights
    containerRef.current.querySelectorAll('.cell-highlight').forEach((el) => {
      el.classList.remove('cell-highlight');
    });

    const parsed = parseRange(highlightRange);
    if (!parsed) return;

    const table = containerRef.current.querySelector('table');
    if (!table) return;

    const rows = table.querySelectorAll('tr');

    // Find how far right to extend (until hitting a non-empty cell in starting row)
    let endCol = parsed.startCol;
    const startRow = rows[parsed.startRow];
    if (startRow) {
      for (let c = parsed.startCol + 1; c < startRow.children.length; c++) {
        const cell = startRow.children[c] as HTMLElement;
        if (cell && cell.textContent?.trim()) break;
        endCol = c;
      }
    }

    // Find how far down to extend (until hitting a non-empty cell in starting column)
    let endRow = parsed.startRow;
    for (let r = parsed.startRow + 1; r < rows.length; r++) {
      const row = rows[r];
      if (!row) break;
      const cell = row.children[parsed.startCol] as HTMLElement;
      if (cell && cell.textContent?.trim()) break;
      endRow = r;
    }

    // Highlight the rectangular region
    let firstHighlighted: Element | null = null;
    for (let r = parsed.startRow; r <= endRow; r++) {
      const row = rows[r];
      if (!row) continue;
      for (let c = parsed.startCol; c <= endCol; c++) {
        const cell = row.children[c] as HTMLElement;
        if (cell) {
          cell.classList.add('cell-highlight');
          if (!firstHighlighted) firstHighlighted = cell;
        }
      }
    }

    if (firstHighlighted) {
      firstHighlighted.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'center' });
    }
  }, [highlightRange, html]);

  if (loading) return <Text color="gray">Loading spreadsheet...</Text>;
  if (error) return <Text color="red">{error}</Text>;

  return <Box ref={containerRef} className="excel-viewer" dangerouslySetInnerHTML={{ __html: sanitizeHtml(html) }} />;
}

// =============================================================================
// Main Content Component
// =============================================================================

interface MainContentProps {
  entries: CarrierEntry[];
  layers: Layer[];
  stem: string;
  activeTab: string;
  onTabChange: (tab: string) => void;
  highlightEntry: CarrierEntry | null;
  onCellClick: (entry: CarrierEntry) => void;
}

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
