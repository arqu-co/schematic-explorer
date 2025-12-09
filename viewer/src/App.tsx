import { useEffect, useState } from 'react';
import { Theme, Container, Flex, Heading, Text, Card, Badge, Box, Tabs, ScrollArea, Table, Tooltip, Code } from '@radix-ui/themes';
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

function TowerVisualization({ layers }: { layers: Layer[] }) {
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
          <Flex gap="1" wrap="wrap" className="layer-carriers">
            {layer.entries.map((entry, entryIdx) => (
              <Tooltip key={entryIdx} content={
                <Box>
                  <Text as="div" weight="bold">{entry.carrier}</Text>
                  {entry.participation_pct && <Text as="div" size="1">Participation: {formatPercent(entry.participation_pct)}</Text>}
                  {entry.premium && <Text as="div" size="1">Premium: {formatCurrency(entry.premium)}</Text>}
                  {entry.attachment_point && <Text as="div" size="1">Attachment: {entry.attachment_point}</Text>}
                  <Text as="div" size="1" color="gray">Cell: {entry.excel_range}</Text>
                </Box>
              }>
                <Box
                  className="carrier-block"
                  style={{
                    backgroundColor: entry.fill_color ? hexToRgba(entry.fill_color, 0.5) : 'var(--accent-3)',
                    flex: entry.participation_pct ? `${entry.participation_pct * 100}` : '1',
                    minWidth: '60px',
                  }}
                >
                  <Text size="1" className="carrier-name" truncate>{entry.carrier}</Text>
                  {entry.participation_pct && (
                    <Text size="1" color="gray">{formatPercent(entry.participation_pct)}</Text>
                  )}
                </Box>
              </Tooltip>
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
    <Box>
      {score !== null && (
        <Flex gap="2" align="center" mb="3">
          <Badge size="2" color={score >= 90 ? 'green' : score >= 70 ? 'yellow' : 'red'}>
            {score}% Accuracy
          </Badge>
        </Flex>
      )}
      <ScrollArea style={{ maxHeight: '400px' }}>
        <pre className="insights-content">{insights}</pre>
      </ScrollArea>
    </Box>
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
      <Theme appearance="dark" accentColor="blue">
        <Container size="4" p="4">
          <Text>Loading schematics...</Text>
        </Container>
      </Theme>
    );
  }

  if (error) {
    return (
      <Theme appearance="dark" accentColor="blue">
        <Container size="4" p="4">
          <Text color="red">{error}</Text>
        </Container>
      </Theme>
    );
  }

  const layers = selectedFile ? groupByLayer(selectedFile.entries) : [];

  return (
    <Theme appearance="dark" accentColor="blue">
      <Container size="4" p="4">
        <Heading size="6" mb="4">Schematic Explorer</Heading>

        <Flex gap="4">
          <Box style={{ width: '280px', flexShrink: 0 }}>
            <Heading size="3" mb="2">Files</Heading>
            <ScrollArea style={{ maxHeight: 'calc(100vh - 150px)' }}>
              <Flex direction="column" gap="2">
                {files.map(file => (
                  <SchematicCard
                    key={file.name}
                    file={file}
                    isSelected={selectedFile?.name === file.name}
                    onSelect={() => setSelectedFile(file)}
                  />
                ))}
              </Flex>
            </ScrollArea>
          </Box>

          <Box style={{ flex: 1, minWidth: 0 }}>
            {selectedFile && (
              <Tabs.Root defaultValue="tower">
                <Tabs.List>
                  <Tabs.Trigger value="tower">Tower View</Tabs.Trigger>
                  <Tabs.Trigger value="table">Table View</Tabs.Trigger>
                  <Tabs.Trigger value="insights">Insights</Tabs.Trigger>
                  <Tabs.Trigger value="json">Raw JSON</Tabs.Trigger>
                </Tabs.List>

                <Box pt="3">
                  <Tabs.Content value="tower">
                    <TowerVisualization layers={layers} />
                  </Tabs.Content>

                  <Tabs.Content value="table">
                    <ScrollArea>
                      <CarrierTable entries={selectedFile.entries} />
                    </ScrollArea>
                  </Tabs.Content>

                  <Tabs.Content value="insights">
                    <InsightsPanel insights={selectedFile.insights} />
                  </Tabs.Content>

                  <Tabs.Content value="json">
                    <ScrollArea style={{ maxHeight: '600px' }}>
                      <pre className="json-content">
                        {JSON.stringify(selectedFile.entries, null, 2)}
                      </pre>
                    </ScrollArea>
                  </Tabs.Content>
                </Box>
              </Tabs.Root>
            )}
          </Box>
        </Flex>
      </Container>
    </Theme>
  );
}

export default App;
