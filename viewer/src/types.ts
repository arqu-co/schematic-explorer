/**
 * Type definitions for the Schematic Explorer viewer.
 */

/**
 * Represents a single carrier's participation in an insurance layer.
 * Maps directly to the Python CarrierEntry dataclass from the extractor.
 */
export interface CarrierEntry {
  /** Layer limit (e.g., "$50M") */
  layer_limit: string;
  /** Layer description (e.g., "Primary", "Excess") */
  layer_description: string;
  /** Original carrier/insurer name from spreadsheet (e.g., "ACE American") */
  carrier: string;
  /** Participation percentage as decimal (0.25 = 25%) */
  participation_pct: number | null;
  /** Premium amount in dollars */
  premium: number | null;
  /** Premium share amount */
  premium_share: number | null;
  /** Terms and conditions text */
  terms: string | null;
  /** Policy number if available */
  policy_number: string | null;
  /** Excel cell reference (e.g., "B5" or "B5:D7") */
  excel_range: string;
  /** Column span in Excel */
  col_span: number;
  /** Row span in Excel */
  row_span: number;
  /** Background color from Excel as hex (e.g., "FF0000") */
  fill_color: string | null;
  /** Attachment point (e.g., "$50M xs. $25M") */
  attachment_point: string | null;
  /** Resolved canonical carrier name (e.g., "Chubb" for "ACE American") */
  canonical_carrier: string | null;
}

/**
 * Represents a schematic file with extracted carrier data.
 */
export interface SchematicFile {
  /** Full filename (e.g., "tower.json") */
  name: string;
  /** Filename without extension */
  stem: string;
  /** Extracted carrier entries */
  entries: CarrierEntry[];
  /** AI verification insights as markdown */
  insights: string | null;
}

/**
 * Represents a grouped layer with aggregated data for display.
 * Used for Tower View grouping of carriers by layer.
 */
export interface Layer {
  /** Layer limit (e.g., "$50M") */
  limit: string;
  /** Carrier entries in this layer */
  entries: CarrierEntry[];
  /** Sum of all carrier premiums in this layer */
  totalPremium: number;
}
