export interface CarrierEntry {
  layer_limit: string;
  layer_description: string;
  carrier: string;
  participation_pct: number | null;
  premium: number | null;
  premium_share: number | null;
  terms: string | null;
  policy_number: string | null;
  excel_range: string;
  col_span: number;
  row_span: number;
  fill_color: string | null;
  attachment_point: string | null;
}

export interface SchematicFile {
  name: string;
  stem: string;
  entries: CarrierEntry[];
  insights: string | null;
}

export interface Layer {
  limit: string;
  entries: CarrierEntry[];
  totalPremium: number;
}
