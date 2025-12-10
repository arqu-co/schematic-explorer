/**
 * File list sidebar component.
 */

import { Heading, Box, ScrollArea, Flex, Card, Text, Badge } from '@radix-ui/themes';
import type { SchematicFile } from '../types';
import { formatCurrency, groupByLayer } from '../utils';

interface SchematicCardProps {
  file: SchematicFile;
  onSelect: () => void;
  isSelected: boolean;
}

function SchematicCard({ file, onSelect, isSelected }: SchematicCardProps) {
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
            <Text size="1" color="gray">
              {file.entries.length} carriers
            </Text>
            <Text size="1" color="gray">
              •
            </Text>
            <Text size="1" color="gray">
              {layers.length} layers
            </Text>
            {totalPremium > 0 && (
              <>
                <Text size="1" color="gray">
                  •
                </Text>
                <Text size="1" color="gray">
                  {formatCurrency(totalPremium)}
                </Text>
              </>
            )}
          </Flex>
        </Box>
        {score !== null && (
          <Badge color={score >= 90 ? 'green' : score >= 70 ? 'yellow' : 'red'}>{score}%</Badge>
        )}
      </Flex>
    </Card>
  );
}

interface FileListProps {
  files: SchematicFile[];
  selectedFile: SchematicFile | null;
  onFileSelect: (file: SchematicFile) => void;
}

export function FileList({ files, selectedFile, onFileSelect }: FileListProps) {
  return (
    <Box className="sidebar-left">
      <Heading size="3" mb="2">
        Files
      </Heading>
      <ScrollArea className="sidebar-scroll">
        <Flex direction="column" gap="2">
          {files.map((file) => (
            <SchematicCard
              key={file.name}
              file={file}
              isSelected={selectedFile?.name === file.name}
              onSelect={() => onFileSelect(file)}
            />
          ))}
        </Flex>
      </ScrollArea>
    </Box>
  );
}
