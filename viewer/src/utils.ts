/**
 * Utility functions for the Schematic Explorer viewer.
 */

import DOMPurify from 'dompurify';
import type { CarrierEntry, Layer } from './types';

// =============================================================================
// Numeric Constants
// =============================================================================

const THOUSAND = 1_000;
const MILLION = 1_000_000;
const BILLION = 1_000_000_000;

// =============================================================================
// Limit Parsing
// =============================================================================

/**
 * Parse a limit string (e.g., "$50M", "$500K") to a numeric value.
 * Used for sorting layers by limit.
 */
export function parseLimit(limit: string): number {
  const cleaned = limit.replace('$', '').replace(',', '').toUpperCase();
  let multiplier = 1;
  let value = cleaned;
  if (cleaned.endsWith('M')) {
    multiplier = MILLION;
    value = cleaned.slice(0, -1);
  } else if (cleaned.endsWith('K')) {
    multiplier = THOUSAND;
    value = cleaned.slice(0, -1);
  } else if (cleaned.endsWith('B')) {
    multiplier = BILLION;
    value = cleaned.slice(0, -1);
  }
  return parseFloat(value) * multiplier || 0;
}

// =============================================================================
// Formatting
// =============================================================================

/**
 * Format a number as USD currency (e.g., $1,234,567).
 */
export function formatCurrency(value: number | null | undefined): string {
  if (value === null || value === undefined) return '—';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(value);
}

/**
 * Format a decimal as a percentage (e.g., 0.25 -> "25.0%").
 */
export function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) return '—';
  return `${(value * 100).toFixed(1)}%`;
}

// =============================================================================
// Color Conversion
// =============================================================================

/**
 * Convert a hex color to rgba with optional alpha.
 * Handles Excel's ARGB format (FFRRGGBB) by stripping the FF prefix.
 */
export function hexToRgba(hex: string | null, alpha: number = 0.3): string {
  if (!hex) return 'transparent';
  const cleanHex = hex.startsWith('FF') && hex.length === 8 ? hex.slice(2) : hex;
  const r = parseInt(cleanHex.slice(0, 2), 16);
  const g = parseInt(cleanHex.slice(2, 4), 16);
  const b = parseInt(cleanHex.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

// =============================================================================
// Data Grouping
// =============================================================================

/**
 * Group carrier entries by their layer limit.
 * Returns layers sorted by limit (highest first).
 */
export function groupByLayer(entries: CarrierEntry[]): Layer[] {
  const layerMap = new Map<string, CarrierEntry[]>();

  entries.forEach((entry) => {
    const existing = layerMap.get(entry.layer_limit) || [];
    existing.push(entry);
    layerMap.set(entry.layer_limit, existing);
  });

  return Array.from(layerMap.entries())
    .map(([limit, entries]) => ({
      limit,
      entries,
      totalPremium: entries.reduce((sum, e) => sum + (e.premium || 0), 0),
    }))
    .sort((a, b) => parseLimit(b.limit) - parseLimit(a.limit));
}

// =============================================================================
// Excel Range Parsing
// =============================================================================

/**
 * Convert Excel column letters to 1-indexed number (A=1, B=2, etc.).
 */
function colToNum(col: string): number {
  let num = 0;
  for (let i = 0; i < col.length; i++) {
    num = num * 26 + col.charCodeAt(i) - 64;
  }
  return num;
}

/**
 * Convert 1-indexed column number to Excel column letters (1=A, 2=B, 27=AA, etc.).
 */
export function numToCol(num: number): string {
  let col = '';
  while (num > 0) {
    const rem = (num - 1) % 26;
    col = String.fromCharCode(65 + rem) + col;
    num = Math.floor((num - 1) / 26);
  }
  return col;
}

/**
 * Parse an Excel range string into 0-indexed coordinates.
 * Handles formats like "B5", "B5:D7", "Sheet1!B5:D7".
 */
export function parseRange(
  range: string
): { startCol: number; startRow: number; endCol: number; endRow: number } | null {
  // Parse ranges like "B5", "B5:D7", "Sheet1!B5:D7"
  const cellPart = range.includes('!') ? range.split('!')[1] : range;
  const match = cellPart.match(/^([A-Z]+)(\d+)(?::([A-Z]+)(\d+))?$/i);
  if (!match) return null;

  // Convert to 0-indexed for HTML table access
  const startCol = colToNum(match[1].toUpperCase()) - 1;
  const startRow = parseInt(match[2]) - 1;
  const endCol = match[3] ? colToNum(match[3].toUpperCase()) - 1 : startCol;
  const endRow = match[4] ? parseInt(match[4]) - 1 : startRow;

  return { startCol, startRow, endCol, endRow };
}

// =============================================================================
// HTML Sanitization
// =============================================================================

/**
 * Sanitize HTML to prevent XSS attacks.
 * Allows safe elements (tables, divs, spans) and styling attributes.
 */
export function sanitizeHtml(html: string): string {
  return DOMPurify.sanitize(html, {
    ALLOWED_TAGS: [
      'table',
      'thead',
      'tbody',
      'tr',
      'th',
      'td',
      'div',
      'span',
      'p',
      'br',
      'strong',
      'em',
      'b',
      'i',
      'a',
      'colgroup',
      'col',
    ],
    ALLOWED_ATTR: ['style', 'class', 'id', 'colspan', 'rowspan', 'width', 'height'],
  });
}
