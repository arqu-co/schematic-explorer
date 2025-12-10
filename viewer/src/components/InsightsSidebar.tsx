/**
 * Insights sidebar component.
 */

import { Heading, Box, Flex, Badge, Text } from '@radix-ui/themes';
import Markdown from 'react-markdown';

interface InsightsPanelProps {
  insights: string | null;
}

function InsightsPanel({ insights }: InsightsPanelProps) {
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

interface InsightsSidebarProps {
  insights: string | null;
}

export function InsightsSidebar({ insights }: InsightsSidebarProps) {
  return (
    <Box className="sidebar-right">
      <Heading size="3" mb="2">
        Insights
      </Heading>
      <InsightsPanel insights={insights} />
    </Box>
  );
}
