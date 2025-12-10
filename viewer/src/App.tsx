import { useState } from 'react';
import { Theme, Flex, Heading, Box, IconButton, Text } from '@radix-ui/themes';
import '@radix-ui/themes/styles.css';
import type { CarrierEntry, SchematicFile } from './types';
import { groupByLayer } from './utils';
import { useFiles, useTheme } from './hooks';
import { FileList, MainContent, InsightsSidebar } from './components';
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
            {theme === 'dark' ? (
              <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                <path d="M8 1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-1 0v-1A.5.5 0 0 1 8 1zm0 10a3 3 0 1 0 0-6 3 3 0 0 0 0 6zm6.5-2.5a.5.5 0 0 1 0 1h-1a.5.5 0 0 1 0-1h1zm-12 0a.5.5 0 0 1 0 1h-1a.5.5 0 0 1 0-1h1zm9.743-4.036a.5.5 0 0 1 0 .707l-.707.707a.5.5 0 1 1-.707-.707l.707-.707a.5.5 0 0 1 .707 0zm-8.486 6.072a.5.5 0 0 1 0 .707l-.707.707a.5.5 0 1 1-.707-.707l.707-.707a.5.5 0 0 1 .707 0zm7.779 0a.5.5 0 0 1 .707 0l.707.707a.5.5 0 1 1-.707.707l-.707-.707a.5.5 0 0 1 0-.707zm-8.486-6.072a.5.5 0 0 1 .707 0l.707.707a.5.5 0 0 1-.707.707l-.707-.707a.5.5 0 0 1 0-.707zM8 13a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-1 0v-1A.5.5 0 0 1 8 13z" />
              </svg>
            ) : (
              <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                <path d="M6 0.278a.768.768 0 0 1 .08.858 7.208 7.208 0 0 0-.878 3.46c0 4.021 3.278 7.277 7.318 7.277.527 0 1.04-.055 1.533-.16a.787.787 0 0 1 .81.316.733.733 0 0 1-.031.893A8.349 8.349 0 0 1 8.344 16C3.734 16 0 12.286 0 7.71 0 4.266 2.114 1.312 5.124.06A.752.752 0 0 1 6 .278z" />
              </svg>
            )}
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
