import React, { useEffect, useState, useRef } from 'react';
import { Theme, Flex, Heading, Text, Card, Badge, Box, Tabs, ScrollArea, Table, Code, IconButton } from '@radix-ui/themes';
import Markdown from 'react-markdown';
import * as XLSX from 'xlsx';
import '@radix-ui/themes/styles.css';
import type { CarrierEntry, SchematicFile, Layer } from './types';
import './App.css';

function parseLimit(limit: string): number {
  const cleaned = limit.replace('$', '').replace(',', '').toUpperCase();
  let multiplier = 1;
  let value = cleaned;
  if (cleaned.endsWith('M')) {
    multiplier = 1_000_000;
    value = cleaned.slice(0, -1);
  } else if (cleaned.endsWith('K')) {
    multiplier = 1_000;
    value = cleaned.slice(0, -1);
  } else if (cleaned.endsWith('B')) {
    multiplier = 1_000_000_000;
    value = cleaned.slice(0, -1);
  }
  return parseFloat(value) * multiplier || 0;
}

function groupByLayer(entries: CarrierEntry[]): Layer[] {
  const layerMap = new Map<string, CarrierEntry[]>();

  entries.forEach(entry => {
    const existing = layerMap.get(entry.layer_limit) || [];
    existing.push(entry);
    layerMap.set(entry.layer_limit, existing);
  });

  return Array.from(layerMap.entries())
    .map(([limit, entries]) => ({
      limit,
      entries,
      totalPremium: entries.reduce((sum, e) => sum + (e.premium || 0), 0)
    }))
    .sort((a, b) => parseLimit(b.limit) - parseLimit(a.limit));
}

function formatCurrency(value: number | null): string {
  if (value === null || value === undefined) return '—';
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(value);
}

function formatPercent(value: number | null): string {
  if (value === null || value === undefined) return '—';
  return `${(value * 100).toFixed(1)}%`;
}

function hexToRgba(hex: string | null, alpha: number = 0.3): string {
  if (!hex) return 'transparent';
  const cleanHex = hex.startsWith('FF') && hex.length === 8 ? hex.slice(2) : hex;
  const r = parseInt(cleanHex.slice(0, 2), 16);
  const g = parseInt(cleanHex.slice(2, 4), 16);
  const b = parseInt(cleanHex.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function TowerVisualization({ layers, onCellClick }: { layers: Layer[]; onCellClick?: (entry: CarrierEntry) => void }) {
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
            <Badge size="2" color="blue">{layer.limit}</Badge>
            <Text size="1" color="gray">{layer.entries.length} carrier{layer.entries.length !== 1 ? 's' : ''}</Text>
            {layer.totalPremium > 0 && (
              <Text size="1" weight="medium">{formatCurrency(layer.totalPremium)}</Text>
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
                <Text size="2" weight="medium" className="carrier-name">{entry.carrier}</Text>
                <Flex gap="3" wrap="wrap" mt="1">
                  {entry.participation_pct && (
                    <Text size="1" color="gray">{formatPercent(entry.participation_pct)}</Text>
                  )}
                  {entry.premium && (
                    <Text size="1" color="gray">{formatCurrency(entry.premium)}</Text>
                  )}
                  {entry.attachment_point && (
                    <Text size="1" color="gray">xs {entry.attachment_point}</Text>
                  )}
                </Flex>
                <Text size="1" color="gray" style={{ opacity: 0.6 }}>{entry.excel_range}</Text>
              </Box>
            ))}
          </Flex>
        </Box>
      ))}
    </Box>
  );
}

function CarrierTable({ entries }: { entries: CarrierEntry[] }) {
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
            <Table.Cell><Badge>{entry.layer_limit}</Badge></Table.Cell>
            <Table.Cell>
              <Text weight="medium">{entry.carrier}</Text>
              {entry.terms && <Text size="1" color="gray" as="div">{entry.terms}</Text>}
            </Table.Cell>
            <Table.Cell>{formatPercent(entry.participation_pct)}</Table.Cell>
            <Table.Cell>{formatCurrency(entry.premium)}</Table.Cell>
            <Table.Cell>{entry.attachment_point || '—'}</Table.Cell>
            <Table.Cell><Code size="1">{entry.excel_range}</Code></Table.Cell>
          </Table.Row>
        ))}
      </Table.Body>
    </Table.Root>
  );
}

function InsightsPanel({ insights }: { insights: string | null }) {
  if (!insights) return <Text color="gray">No verification insights available</Text>;

  const scoreMatch = insights.match(/Score:\s*(\d+)%/);
  const score = scoreMatch ? parseInt(scoreMatch[1]) : null;

  return (
    <Box className="insights-panel">
      {score !== null && (
        <Flex gap="2" align="center" mb="3">
          <Badge size="2" color={score >= 90 ? 'green' : score >= 70 ? 'yellow' : 'red'}>
            {score}% Accuracy
          </Badge>
        </Flex>
      )}
      <Box className="insights-content">
        <Markdown>{insights}</Markdown>
      </Box>
    </Box>
  );
}

function parseRange(range: string): { startCol: number; startRow: number; endCol: number; endRow: number } | null {
  // Parse ranges like "B5", "B5:D7", "Sheet1!B5:D7"
  const cellPart = range.includes('!') ? range.split('!')[1] : range;
  const match = cellPart.match(/^([A-Z]+)(\d+)(?::([A-Z]+)(\d+))?$/i);
  if (!match) return null;

  const colToNum = (col: string) => {
    let num = 0;
    for (let i = 0; i < col.length; i++) {
      num = num * 26 + col.charCodeAt(i) - 64;
    }
    return num;
  };

  // Convert to 0-indexed for HTML table access
  const startCol = colToNum(match[1].toUpperCase()) - 1;
  const startRow = parseInt(match[2]) - 1;
  const endCol = match[3] ? colToNum(match[3].toUpperCase()) - 1 : startCol;
  const endRow = match[4] ? parseInt(match[4]) - 1 : startRow;

  return { startCol, startRow, endCol, endRow };
}

function ExcelViewer({ stem, highlightRange }: { stem: string; highlightRange?: string | null }) {
  const [html, setHtml] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    async function loadExcel() {
      setLoading(true);
      setError(null);
      try {
        const response = await fetch(`/api/input/${stem}.xlsx`);
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
    containerRef.current.querySelectorAll('.cell-highlight').forEach(el => {
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

  return (
    <Box ref={containerRef} className="excel-viewer" dangerouslySetInnerHTML={{ __html: html }} />
  );
}

function SchematicCard({ file, onSelect, isSelected }: { file: SchematicFile; onSelect: () => void; isSelected: boolean }) {
  const layers = groupByLayer(file.entries);
  const totalPremium = file.entries.reduce((sum, e) => sum + (e.premium || 0), 0);
  const scoreMatch = file.insights?.match(/Score:\s*(\d+)%/);
  const score = scoreMatch ? parseInt(scoreMatch[1]) : null;

  return (
    <Card
      className={`schematic-card ${isSelected ? 'selected' : ''}`}
      onClick={onSelect}
      style={{ cursor: 'pointer' }}
    >
      <Flex justify="between" align="start">
        <Box>
          <Heading size="3">{file.stem}</Heading>
          <Flex gap="2" mt="1">
            <Text size="1" color="gray">{file.entries.length} carriers</Text>
            <Text size="1" color="gray">•</Text>
            <Text size="1" color="gray">{layers.length} layers</Text>
            {totalPremium > 0 && (
              <>
                <Text size="1" color="gray">•</Text>
                <Text size="1" color="gray">{formatCurrency(totalPremium)}</Text>
              </>
            )}
          </Flex>
        </Box>
        {score !== null && (
          <Badge color={score >= 90 ? 'green' : score >= 70 ? 'yellow' : 'red'}>
            {score}%
          </Badge>
        )}
      </Flex>
    </Card>
  );
}

function App() {
  const [files, setFiles] = useState<SchematicFile[]>([]);
  const [selectedFile, setSelectedFile] = useState<SchematicFile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState('tower');
  const [highlightEntry, setHighlightEntry] = useState<CarrierEntry | null>(null);
  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('theme');
      if (saved === 'light' || saved === 'dark') return saved;
      return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    return 'dark';
  });

  const toggleTheme = () => {
    const newTheme = theme === 'dark' ? 'light' : 'dark';
    setTheme(newTheme);
    localStorage.setItem('theme', newTheme);
  };

  const handleCellClick = (entry: CarrierEntry) => {
    setHighlightEntry(entry);
    setActiveTab('excel');
  };

  const handleFileSelect = (file: SchematicFile) => {
    setSelectedFile(file);
    setHighlightEntry(null);
    setActiveTab('tower');
  };

  useEffect(() => {
    async function loadData() {
      try {
        const indexRes = await fetch('/api/files');
        if (!indexRes.ok) throw new Error('Failed to load file index');
        const fileList: string[] = await indexRes.json();

        const loaded: SchematicFile[] = await Promise.all(
          fileList.map(async (name) => {
            const stem = name.replace('.json', '');
            const [jsonRes, insightsRes] = await Promise.all([
              fetch(`/api/data/${name}`),
              fetch(`/api/data/${stem}_insights.txt`).catch(() => null)
            ]);

            const entries: CarrierEntry[] = jsonRes.ok ? await jsonRes.json() : [];
            const insights = insightsRes?.ok ? await insightsRes.text() : null;

            return { name, stem, entries, insights };
          })
        );

        setFiles(loaded.filter(f => f.entries.length > 0));
        if (loaded.length > 0) setSelectedFile(loaded[0]);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load data');
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  if (loading) {
    return (
      <Theme appearance={theme} accentColor="blue">
        <Box className="app-container">
          <Text>Loading schematics...</Text>
        </Box>
      </Theme>
    );
  }

  if (error) {
    return (
      <Theme appearance={theme} accentColor="blue">
        <Box className="app-container">
          <Text color="red">{error}</Text>
        </Box>
      </Theme>
    );
  }

  const layers = selectedFile ? groupByLayer(selectedFile.entries) : [];

  return (
    <Theme appearance={theme} accentColor="blue">
      <Box className="app-container">
        <Flex justify="between" align="center" className="app-header">
          <Heading size="6">Schematic Explorer</Heading>
          <IconButton
            variant="ghost"
            size="2"
            onClick={toggleTheme}
            aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
          >
            {theme === 'dark' ? (
              <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                <path d="M8 1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-1 0v-1A.5.5 0 0 1 8 1zm0 10a3 3 0 1 0 0-6 3 3 0 0 0 0 6zm6.5-2.5a.5.5 0 0 1 0 1h-1a.5.5 0 0 1 0-1h1zm-12 0a.5.5 0 0 1 0 1h-1a.5.5 0 0 1 0-1h1zm9.743-4.036a.5.5 0 0 1 0 .707l-.707.707a.5.5 0 1 1-.707-.707l.707-.707a.5.5 0 0 1 .707 0zm-8.486 6.072a.5.5 0 0 1 0 .707l-.707.707a.5.5 0 1 1-.707-.707l.707-.707a.5.5 0 0 1 .707 0zm7.779 0a.5.5 0 0 1 .707 0l.707.707a.5.5 0 1 1-.707.707l-.707-.707a.5.5 0 0 1 0-.707zm-8.486-6.072a.5.5 0 0 1 .707 0l.707.707a.5.5 0 0 1-.707.707l-.707-.707a.5.5 0 0 1 0-.707zM8 13a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-1 0v-1A.5.5 0 0 1 8 13z"/>
              </svg>
            ) : (
              <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                <path d="M6 0.278a.768.768 0 0 1 .08.858 7.208 7.208 0 0 0-.878 3.46c0 4.021 3.278 7.277 7.318 7.277.527 0 1.04-.055 1.533-.16a.787.787 0 0 1 .81.316.733.733 0 0 1-.031.893A8.349 8.349 0 0 1 8.344 16C3.734 16 0 12.286 0 7.71 0 4.266 2.114 1.312 5.124.06A.752.752 0 0 1 6 .278z"/>
              </svg>
            )}
          </IconButton>
        </Flex>

        <Flex gap="4" className="app-content">
          <Box className="sidebar-left">
            <Heading size="3" mb="2">Files</Heading>
            <ScrollArea className="sidebar-scroll">
              <Flex direction="column" gap="2">
                {files.map(file => (
                  <SchematicCard
                    key={file.name}
                    file={file}
                    isSelected={selectedFile?.name === file.name}
                    onSelect={() => handleFileSelect(file)}
                  />
                ))}
              </Flex>
            </ScrollArea>
          </Box>

          <Box className="main-content">
            {selectedFile && (
              <>
                <Tabs.Root value={activeTab} onValueChange={setActiveTab}>
                  <Tabs.List>
                    <Tabs.Trigger value="tower">Tower View</Tabs.Trigger>
                    <Tabs.Trigger value="table">Table View</Tabs.Trigger>
                    <Tabs.Trigger value="json">Raw JSON</Tabs.Trigger>
                    <Tabs.Trigger value="excel">Excel</Tabs.Trigger>
                  </Tabs.List>
                </Tabs.Root>

                <div className="tab-scroll-container">
                  {activeTab === 'tower' && (
                    <TowerVisualization layers={layers} onCellClick={handleCellClick} />
                  )}
                  {activeTab === 'table' && (
                    <CarrierTable entries={selectedFile.entries} />
                  )}
                  {activeTab === 'json' && (
                    <pre className="json-content">
                      {JSON.stringify(selectedFile.entries, null, 2)}
                    </pre>
                  )}
                  {activeTab === 'excel' && (
                    <ExcelViewer stem={selectedFile.stem} highlightRange={highlightEntry?.excel_range ?? null} />
                  )}
                </div>
              </>
            )}
          </Box>

          <Box className="sidebar-right">
            <Heading size="3" mb="2">Insights</Heading>
            {selectedFile && <InsightsPanel insights={selectedFile.insights} />}
          </Box>
        </Flex>
      </Box>
    </Theme>
  );
}

export default App;
