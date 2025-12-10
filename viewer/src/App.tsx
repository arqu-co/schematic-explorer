import { useState } from 'react';
import { Theme, Flex, Heading, Box, IconButton, Text } from '@radix-ui/themes';
import '@radix-ui/themes/styles.css';
import type { CarrierEntry, SchematicFile } from './types';
import { groupByLayer } from './utils';
import { useFiles, useTheme } from './hooks';
import { FileList, MainContent, InsightsSidebar, ThemeToggleIcon } from './components';
import './App.css';

function App() {
  const { files, selectedFile, loading, error, selectFile } = useFiles();
  const { theme, toggleTheme } = useTheme();
  const [activeTab, setActiveTab] = useState('tower');
  const [highlightEntry, setHighlightEntry] = useState<CarrierEntry | null>(null);

  const handleCellClick = (entry: CarrierEntry) => {
    setHighlightEntry(entry);
    setActiveTab('excel');
  };

  const handleFileSelect = (file: SchematicFile) => {
    selectFile(file);
    setHighlightEntry(null);
    setActiveTab('tower');
  };

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
            <ThemeToggleIcon theme={theme} />
          </IconButton>
        </Flex>

        <Flex gap="4" className="app-content">
          <FileList files={files} selectedFile={selectedFile} onFileSelect={handleFileSelect} />

          {selectedFile && (
            <MainContent
              entries={selectedFile.entries}
              layers={layers}
              stem={selectedFile.stem}
              activeTab={activeTab}
              onTabChange={setActiveTab}
              highlightEntry={highlightEntry}
              onCellClick={handleCellClick}
            />
          )}

          <InsightsSidebar insights={selectedFile?.insights ?? null} />
        </Flex>
      </Box>
    </Theme>
  );
}

export default App;
