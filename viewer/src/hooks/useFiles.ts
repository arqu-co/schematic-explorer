/**
 * Custom hook for managing schematic files state.
 */

import { useState, useEffect, useCallback } from 'react';
import type { SchematicFile, CarrierEntry } from '../types';
import { API_PATHS, getDataUrl, getInsightsUrl } from '../api';

interface UseFilesReturn {
  /** List of loaded schematic files */
  files: SchematicFile[];
  /** Currently selected file */
  selectedFile: SchematicFile | null;
  /** Loading state */
  loading: boolean;
  /** Error message if loading failed */
  error: string | null;
  /** Select a file */
  selectFile: (file: SchematicFile) => void;
}

/**
 * Hook for loading and managing schematic files.
 *
 * Fetches the file index and loads all schematic data on mount.
 */
export function useFiles(): UseFilesReturn {
  const [files, setFiles] = useState<SchematicFile[]>([]);
  const [selectedFile, setSelectedFile] = useState<SchematicFile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        const indexRes = await fetch(API_PATHS.FILES);
        if (!indexRes.ok) throw new Error('Failed to load file index');
        const fileList: string[] = await indexRes.json();

        const loaded: SchematicFile[] = await Promise.all(
          fileList.map(async (name) => {
            const stem = name.replace('.json', '');
            const [jsonRes, insightsRes] = await Promise.all([
              fetch(getDataUrl(name)),
              fetch(getInsightsUrl(stem)).catch(() => null),
            ]);

            const entries: CarrierEntry[] = jsonRes.ok ? await jsonRes.json() : [];
            const insights = insightsRes?.ok ? await insightsRes.text() : null;

            return { name, stem, entries, insights };
          })
        );

        const validFiles = loaded.filter((f) => f.entries.length > 0);
        setFiles(validFiles);
        if (validFiles.length > 0) {
          setSelectedFile(validFiles[0]);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load data');
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  const selectFile = useCallback((file: SchematicFile) => {
    setSelectedFile(file);
  }, []);

  return {
    files,
    selectedFile,
    loading,
    error,
    selectFile,
  };
}
