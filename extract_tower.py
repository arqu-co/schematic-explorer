#!/usr/bin/env python3
"""
Insurance Tower Diagram Extractor CLI

Usage:
    python extract_tower.py "input/Sample Tower BC.xlsx"
    python extract_tower.py "input/Sample Tower SM.xlsx" --sheet "BOUND Property Tower"
    python extract_tower.py "input/Sample Tower BC.xlsx" --format html --output output/tower.html
"""

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from tower_extractor import (
    extract_tower_data,
    to_dataframe,
    render_ascii_tower,
    render_html,
)


def main():
    parser = argparse.ArgumentParser(
        description='Extract structured data from insurance tower Excel diagrams'
    )
    parser.add_argument('filepath', help='Path to the Excel file')
    parser.add_argument('--sheet', '-s', help='Sheet name (uses active sheet if not specified)')
    parser.add_argument('--output', '-o', help='Output file (supports .json, .csv, .html)')
    parser.add_argument('--format', '-f', choices=['json', 'csv', 'table', 'tower', 'html'],
                        default='table', help='Output format')
    parser.add_argument('--width', '-w', type=int, default=100,
                        help='Width for tower visualization (default: 100)')

    args = parser.parse_args()
    entries, layer_summaries = extract_tower_data(args.filepath, args.sheet)

    if not entries:
        print("No carrier data found in the file.")
        return

    # Determine format from output extension if not specified
    fmt = args.format
    if args.output:
        ext = Path(args.output).suffix.lower()
        if ext == '.html' and fmt == 'table':
            fmt = 'html'
        elif ext == '.json' and fmt == 'table':
            fmt = 'json'
        elif ext == '.csv' and fmt == 'table':
            fmt = 'csv'

    output_content = None

    if fmt == 'json':
        output_content = json.dumps([asdict(e) for e in entries], indent=2)

    elif fmt == 'csv':
        df = to_dataframe(entries)
        output_content = df.to_csv(index=False)

    elif fmt == 'tower':
        output_content = render_ascii_tower(entries, width=args.width)

    elif fmt == 'html':
        title = Path(args.filepath).stem
        output_content = render_html(entries, title=f"Insurance Tower - {title}")

    else:  # table format
        df = to_dataframe(entries)
        display_cols = ['layer_limit', 'carrier', 'participation_pct', 'premium', 'layer_description']
        available_cols = [c for c in display_cols if c in df.columns]
        print(df[available_cols].to_string(index=False))
        print(f"\nTotal: {len(entries)} carrier entries across {df['layer_limit'].nunique()} layers")
        return

    # Output to file or stdout
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(output_content)
        print(f"Saved {len(entries)} entries to {args.output}")
    else:
        print(output_content)


if __name__ == '__main__':
    main()
