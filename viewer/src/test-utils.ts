/**
 * Test utilities and factory functions for creating type-safe test data.
 */

import type { CarrierEntry, SchematicFile } from './types';

/**
 * Default CarrierEntry values for testing.
 */
export const defaultCarrierEntry: CarrierEntry = {
  layer_limit: '$50M',
  layer_description: '',
  carrier: 'Test Carrier',
  participation_pct: null,
  premium: null,
  premium_share: null,
  terms: null,
  policy_number: null,
  excel_range: 'A1',
  col_span: 1,
  row_span: 1,
  fill_color: null,
  attachment_point: null,
};

/**
 * Create a CarrierEntry with custom values merged with defaults.
 * Provides type-safe partial object creation without `as` casts.
 */
export function createCarrierEntry(overrides: Partial<CarrierEntry> = {}): CarrierEntry {
  return { ...defaultCarrierEntry, ...overrides };
}

/**
 * Default SchematicFile values for testing.
 */
export const defaultSchematicFile: SchematicFile = {
  name: 'test.json',
  stem: 'test',
  entries: [],
  insights: null,
};

/**
 * Create a SchematicFile with custom values merged with defaults.
 */
export function createSchematicFile(overrides: Partial<SchematicFile> = {}): SchematicFile {
  return { ...defaultSchematicFile, ...overrides };
}
