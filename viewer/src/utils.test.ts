/**
 * Tests for utility functions.
 */

import { describe, it, expect } from 'vitest';
import {
  parseLimit,
  formatCurrency,
  formatPercent,
  hexToRgba,
  groupByLayer,
  parseRange,
  sanitizeHtml,
} from './utils';
import { createCarrierEntry } from './test-utils';

describe('parseLimit', () => {
  it('parses millions correctly', () => {
    expect(parseLimit('$50M')).toBe(50_000_000);
    expect(parseLimit('$100M')).toBe(100_000_000);
    expect(parseLimit('50M')).toBe(50_000_000);
  });

  it('parses thousands correctly', () => {
    expect(parseLimit('$500K')).toBe(500_000);
    expect(parseLimit('250K')).toBe(250_000);
  });

  it('parses billions correctly', () => {
    expect(parseLimit('$1B')).toBe(1_000_000_000);
    expect(parseLimit('2B')).toBe(2_000_000_000);
  });

  it('handles plain numbers', () => {
    expect(parseLimit('$1000')).toBe(1000);
    expect(parseLimit('500')).toBe(500);
  });

  it('handles invalid input', () => {
    expect(parseLimit('')).toBe(0);
    expect(parseLimit('invalid')).toBe(0);
  });
});

describe('formatCurrency', () => {
  it('formats positive values', () => {
    expect(formatCurrency(1000000)).toBe('$1,000,000');
    expect(formatCurrency(50000)).toBe('$50,000');
  });

  it('formats null/undefined as em dash', () => {
    expect(formatCurrency(null)).toBe('—');
    expect(formatCurrency(undefined)).toBe('—');
  });

  it('formats zero', () => {
    expect(formatCurrency(0)).toBe('$0');
  });
});

describe('formatPercent', () => {
  it('formats decimal percentages', () => {
    expect(formatPercent(0.25)).toBe('25.0%');
    expect(formatPercent(0.5)).toBe('50.0%');
    expect(formatPercent(1)).toBe('100.0%');
  });

  it('formats null/undefined as em dash', () => {
    expect(formatPercent(null)).toBe('—');
    expect(formatPercent(undefined)).toBe('—');
  });
});

describe('hexToRgba', () => {
  it('converts hex to rgba', () => {
    expect(hexToRgba('FF0000', 0.5)).toBe('rgba(255, 0, 0, 0.5)');
    expect(hexToRgba('00FF00', 0.3)).toBe('rgba(0, 255, 0, 0.3)');
  });

  it('handles ARGB format (Excel)', () => {
    expect(hexToRgba('FFFF0000', 0.5)).toBe('rgba(255, 0, 0, 0.5)');
  });

  it('returns transparent for null', () => {
    expect(hexToRgba(null)).toBe('transparent');
  });

  it('uses default alpha of 0.3', () => {
    expect(hexToRgba('FF0000')).toBe('rgba(255, 0, 0, 0.3)');
  });
});

describe('groupByLayer', () => {
  it('groups entries by layer limit', () => {
    const entries = [
      createCarrierEntry({ layer_limit: '$50M', carrier: 'Carrier A', premium: 100000 }),
      createCarrierEntry({ layer_limit: '$50M', carrier: 'Carrier B', premium: 200000 }),
      createCarrierEntry({ layer_limit: '$25M', carrier: 'Carrier C', premium: 50000 }),
    ];

    const layers = groupByLayer(entries);

    expect(layers).toHaveLength(2);
    // Sorted by limit (highest first)
    expect(layers[0].limit).toBe('$50M');
    expect(layers[0].entries).toHaveLength(2);
    expect(layers[0].totalPremium).toBe(300000);

    expect(layers[1].limit).toBe('$25M');
    expect(layers[1].entries).toHaveLength(1);
    expect(layers[1].totalPremium).toBe(50000);
  });

  it('handles empty entries', () => {
    expect(groupByLayer([])).toEqual([]);
  });
});

describe('parseRange', () => {
  it('parses single cell reference', () => {
    const result = parseRange('B5');
    expect(result).toEqual({ startCol: 1, startRow: 4, endCol: 1, endRow: 4 });
  });

  it('parses range reference', () => {
    const result = parseRange('B5:D7');
    expect(result).toEqual({ startCol: 1, startRow: 4, endCol: 3, endRow: 6 });
  });

  it('parses reference with sheet name', () => {
    const result = parseRange('Sheet1!B5:D7');
    expect(result).toEqual({ startCol: 1, startRow: 4, endCol: 3, endRow: 6 });
  });

  it('handles multi-letter columns', () => {
    const result = parseRange('AA1');
    expect(result).toEqual({ startCol: 26, startRow: 0, endCol: 26, endRow: 0 });
  });

  it('returns null for invalid range', () => {
    expect(parseRange('invalid')).toBeNull();
    expect(parseRange('')).toBeNull();
  });
});

describe('sanitizeHtml', () => {
  it('preserves safe HTML elements', () => {
    const html = '<table><tr><td>Data</td></tr></table>';
    const result = sanitizeHtml(html);
    // DOMPurify normalizes HTML structure (adds tbody)
    expect(result).toContain('<table>');
    expect(result).toContain('<tr>');
    expect(result).toContain('<td>Data</td>');
    expect(result).toContain('</table>');
  });

  it('removes script tags', () => {
    const html = '<div>Safe</div><script>alert("xss")</script>';
    expect(sanitizeHtml(html)).toBe('<div>Safe</div>');
  });

  it('removes event handlers', () => {
    const html = '<div onclick="alert(1)">Click</div>';
    expect(sanitizeHtml(html)).toBe('<div>Click</div>');
  });

  it('removes javascript: URLs', () => {
    const html = '<a href="javascript:alert(1)">Link</a>';
    expect(sanitizeHtml(html)).toBe('<a>Link</a>');
  });

  it('handles empty string', () => {
    expect(sanitizeHtml('')).toBe('');
  });

  it('preserves table styling attributes', () => {
    // Use complete table structure so td is valid
    const html = '<table><tr><td style="background-color: red;">Cell</td></tr></table>';
    const result = sanitizeHtml(html);
    expect(result).toContain('style=');
    expect(result).toContain('background-color');
  });
});
