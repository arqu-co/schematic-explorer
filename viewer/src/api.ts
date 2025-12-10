/**
 * API path constants for the Schematic Explorer viewer.
 */

// =============================================================================
// API Base Paths
// =============================================================================

/**
 * API paths for accessing server endpoints.
 */
export const API_PATHS = {
  /** Base path for file listing */
  FILES: '/api/files',

  /** Base path for extracted data files */
  DATA: '/api/data',

  /** Base path for input Excel files */
  INPUT: '/api/input',
} as const;

// =============================================================================
// API URL Builders
// =============================================================================

/**
 * Build URL for fetching extracted JSON data.
 */
export function getDataUrl(filename: string): string {
  return `${API_PATHS.DATA}/${filename}`;
}

/**
 * Build URL for fetching insights text file.
 */
export function getInsightsUrl(stem: string): string {
  return `${API_PATHS.DATA}/${stem}_insights.txt`;
}

/**
 * Build URL for fetching input Excel file.
 */
export function getInputExcelUrl(stem: string): string {
  return `${API_PATHS.INPUT}/${stem}.xlsx`;
}
