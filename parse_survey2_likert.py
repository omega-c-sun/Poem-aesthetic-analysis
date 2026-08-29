#!/usr/bin/env python3
from __future__ import annotations
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parent
DEFAULT_XLSX = Path('c:\\Users\\孙行知\\Downloads\\381340228_按序号_英文十四行诗审美评分 Reading English Sonnets — Aesthetic Rating_12_12.xlsx')
OUT_DIR = ROOT / 'iteration' / 'survey2_likert'
BRANCH_LINEAGE = {'1': 't1a', '2': 't1b', '3': 't2a', '4': 't2b', '5': 't3a', '6': 't3b'}
THEMES = {'t1a': 'autumn departure', 't1b': 'autumn departure', 't2a': 'urban night solitude', 't2b': 'urban night solitude', 't3a': 'memory and water', 't3b': 'memory and water'}
DIMS = ('tension', 'symbol', 'rhythm')

def find_col(columns: list[str], *needles: str) -> str:
    for c in columns:
        cl = str(c).lower()
        if all((n.lower() in cl for n in needles)):
            return c
    raise KeyError(f'No column matching {needles}')

def parse_branch(val: object) -> str | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    s = str(val).strip()
    if s in {'1', '1.0', '2', '2.0', '3', '3.0', '4', '4.0', '5', '5.0', '6', '6.0'}:
        return str(int(float(s)))
    m = re.search('分支\\s*(\\d)|Branch\\s*(\\d)', s, re.I)
    if m:
        return m.group(1) or m.group(2)
    return None

def parse_expertise(val: object) -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return 'unknown'
    s = str(val).strip()
    if s in {'1', '1.0'}:
        return 'amateur'
    if s in {'2', '2.0'}:
        return 'intermediate'
    if s in {'3', '3.0'}:
        return 'expert'
    if 'Expert' in s or '较专业' in s:
        return 'expert'
    if 'Intermediate' in s or '有一定基础' in s:
        return 'intermediate'
    if 'Amateur' in s or '业余' in s:
        return 'amateur'
    return s[:80]

def to_int_score(val: object) -> int | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    try:
        return int(float(val))
    except (TypeError, ValueError):
        s = str(val).strip()
        m = re.search('[1-7]', s)
        return int(m.group(0)) if m else None

def locate_xlsx() -> Path:
    if DEFAULT_XLSX.exists():
        return DEFAULT_XLSX
    downloads = Path('c:\\Users\\孙行知\\Downloads')
    cands = sorted(downloads.glob('*Aesthetic Rating*.xlsx'), key=lambda p: p.stat().st_mtime)
    if not cands:
        raise FileNotFoundError(DEFAULT_XLSX)
    return cands[-1]

def main() -> int:
    xlsx = locate_xlsx()
    df = pd.read_excel(xlsx)
    cols = list(df.columns)
    col_agree = find_col(cols, 'agree to participate')
    col_expertise = find_col(cols, 'experience with poetry')
    col_confidence = find_col(cols, 'confidence') if any(('confidence' in str(c).lower() for c in cols)) else find_col(cols, '自信')
    col_branch = find_col(cols, 'matching rating branch')

    def matrix_col(item: str, dim_needle: str) -> str:
        for c in cols:
            s = str(c)
            if s.startswith(f'{item}、') or s.startswith(f'{item}.'):
                if dim_needle.lower() in s.lower():
                    return c
        raise KeyError(f'No matrix column for item {item} / {dim_needle}')
    q7 = {d: matrix_col('7', {'tension': 'Tension', 'symbol': 'Symbol', 'rhythm': 'Rhythm'}[d]) for d in DIMS}
    q8 = {d: matrix_col('8', {'tension': 'Tension', 'symbol': 'Symbol', 'rhythm': 'Rhythm'}[d]) for d in DIMS}
    respondents: list[dict] = []
    long_rows: list[dict] = []
    for i, row in df.iterrows():
        branch = parse_branch(row[col_branch])
        lineage = BRANCH_LINEAGE.get(branch or '', '')
        expertise = parse_expertise(row[col_expertise])
        conf = to_int_score(row[col_confidence])
        scores = {'gen0': {d: to_int_score(row[q7[d]]) for d in DIMS}, 'gen1': {d: to_int_score(row[q8[d]]) for d in DIMS}}
        rec = {'row_index': int(i) + 1, 'branch': branch, 'lineage': lineage, 'theme': THEMES.get(lineage, ''), 'expertise': expertise, 'formal_verse_confidence': conf, 'consent': str(row[col_agree]), 'scores': scores}
        respondents.append(rec)
        for rnd, block in scores.items():
            if all((v is not None for v in block.values())):
                long_rows.append({'respondent': rec['row_index'], 'branch': branch, 'lineage': lineage, 'theme': rec['theme'], 'round': rnd, 'poem_id': f'{rnd}_{lineage}' if lineage else '', 'expertise': expertise, 'tension': block['tension'], 'symbol': block['symbol'], 'rhythm': block['rhythm']})
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    long_df = pd.DataFrame(long_rows)
    long_df.to_csv(OUT_DIR / 'ratings_long.csv', index=False)
    branch_counts = defaultdict(int)
    expertise_counts = defaultdict(int)
    for r in respondents:
        branch_counts[r.get('branch') or '?'] += 1
        expertise_counts[r.get('expertise') or '?'] += 1
    meta = {'parsed_utc': datetime.now(timezone.utc).isoformat(), 'source_xlsx': str(xlsx), 'n_responses': len(df), 'instrument_type': 'likert_rating', 'coding': {'item_7': 'gen0 of selected lineage (first matrix)', 'item_8': 'gen1 of selected lineage (second matrix)', 'branch_lineage': BRANCH_LINEAGE, 'note': 'WJX titles do not name generation round. Mapping uses item order under the paired gen0-then-gen1 rating design.'}, 'branch_counts': dict(branch_counts), 'expertise_counts': dict(expertise_counts)}
    (OUT_DIR / 'parse_meta.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
    (OUT_DIR / 'respondents.json').write_text(json.dumps(respondents, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(meta, ensure_ascii=False, indent=2))
    print(f'Wrote {OUT_DIR}')
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
