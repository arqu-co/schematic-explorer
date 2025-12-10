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

            // Handle both formats:
            // - Flat array: [...entries]
            // - Wrapped object: { entries: [...], verification: {...} }
            let entries: CarrierEntry[] = [];
            let insights: string | null = null;

            if (jsonRes.ok) {
              const data = await jsonRes.json();
              if (Array.isArray(data)) {
                // Flat array format (no verification)
                entries = data;
              } else if (data.entries) {
                // Wrapped format with verification
                entries = data.entries;
                // Use verification summary as insights if no markdown insights file exists
                if (data.verification?.summary) {
                  insights = `**Verification Score:** ${Math.round((data.verification.score || 0) * 100)}%\n\n${data.verification.summary}`;
                  if (data.verification.issues?.length > 0) {
                    insights += '\n\n**Issues:**\n' + data.verification.issues.map((i: string) => `- ${i}`).join('\n');
                  }
                }
              }
            }

            // Markdown insights file takes precedence if it exists
            const mdInsights = insightsRes?.ok ? await insightsRes.text() : null;
            if (mdInsights) {
              insights = mdInsights;
            }

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
