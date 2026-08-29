#!/usr/bin/env python3
from __future__ import annotations
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parent
DEFAULT_XLSX = Path('c:\\Users\\孙行知\\Downloads\\380723239_按序号_英文十四行诗审美评分 Reading English Sonnets — Aesthetic Rating_10_10.xlsx')
OUT_DIR = ROOT / 'iteration' / 'survey2'
BLIND_MAP = ROOT / 'survey2_blind_map.json'
BRANCH_POEMS = {'1': 'gen1_t1a', '2': 'gen1_t1b', '3': 'gen1_t2a', '4': 'gen1_t2b', '5': 'gen1_t3a', '6': 'gen1_t3b'}
DIMS = ('tension', 'symbol', 'rhythm')

def find_col(columns: list[str], *needles: str) -> str:
    for c in columns:
        if all((n.lower() in str(c).lower() for n in needles)):
            return c
    raise KeyError(f'No column matching {needles}')

def parse_branch(val: object) -> str | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    s = str(val).strip()
    if s in {'1', '1.0'}:
        return '1'
    if s in {'2', '2.0'}:
        return '2'
    if s in {'3', '3.0'}:
        return '3'
    if s in {'4', '4.0'}:
        return '4'
    if s in {'5', '5.0'}:
        return '5'
    if s in {'6', '6.0'}:
        return '6'
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

def clean_text(val: object) -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ''
    return str(val).strip()

def is_substantive(text: str) -> bool:
    t = text.strip()
    if not t or t in {'/', '同上', '同第二', '（空）', '(空)'}:
        return False
    if t.startswith('同第二'):
        return False
    if len(t) < 8 and t in {'没什么要改的', '没法改吧'}:
        return False
    return True

def detect_instrumentation(columns: list[str]) -> dict:
    cols_l = [str(c).lower() for c in columns]
    has_likert_branch = any(('分支' in c and '1-7' in c for c in cols_l))
    has_feedback = any(('actionable suggestions' in c for c in cols_l))
    return {'has_likert_ratings': has_likert_branch, 'has_textual_feedback': has_feedback, 'instrument_type': 'textual_feedback' if has_feedback and (not has_likert_branch) else 'likert_rating' if has_likert_branch else 'unknown'}

def main() -> int:
    xlsx = Path(DEFAULT_XLSX)
    if not xlsx.exists():
        downloads = Path('c:\\Users\\孙行知\\Downloads')
        cands = sorted(downloads.glob('*Aesthetic Rating*.xlsx'), key=lambda p: p.stat().st_mtime)
        if not cands:
            raise FileNotFoundError(xlsx)
        xlsx = cands[-1]
    df = pd.read_excel(xlsx)
    cols = list(df.columns)
    instr = detect_instrumentation(cols)
    col_agree = find_col(cols, 'agree to participate')
    col_expertise = find_col(cols, 'experience with poetry')
    col_confidence = find_col(cols, 'confidence evaluating')
    col_lang = find_col(cols, 'primary language')
    col_sonnet = find_col(cols, 'studied shakespearean')
    col_branch = find_col(cols, 'select your branch')
    tension_col = find_col(cols, 'tension:')
    symbol_col = find_col(cols, 'symbol(imagery)')
    rhythm_col = find_col(cols, 'rhythm:')
    comment_col = find_col(cols, 'other comments')
    respondents = []
    by_poem: dict[str, dict[str, list[dict]]] = defaultdict(lambda: {d: [] for d in DIMS})
    for i, row in df.iterrows():
        branch = parse_branch(row[col_branch])
        expertise = parse_expertise(row[col_expertise])
        conf = row[col_confidence]
        try:
            conf_n = int(float(conf))
        except (TypeError, ValueError):
            conf_n = None
        poem_id = BRANCH_POEMS.get(branch or '', '')
        fb = {'tension': clean_text(row[tension_col]), 'symbol': clean_text(row[symbol_col]), 'rhythm': clean_text(row[rhythm_col])}
        rec = {'row_index': int(i) + 1, 'branch': branch, 'poem_id': poem_id, 'display_code': f'P0{branch}' if branch else None, 'expertise': expertise, 'formal_verse_confidence': conf_n, 'primary_language': clean_text(row[col_lang]), 'studied_sonnet': clean_text(row[col_sonnet]), 'consent': clean_text(row[col_agree]), 'feedback': fb, 'comments': clean_text(row[comment_col]), 'char_lengths': {d: len(fb[d]) for d in DIMS}, 'substantive': {d: is_substantive(fb[d]) for d in DIMS}}
        respondents.append(rec)
        if poem_id:
            for dim in DIMS:
                if fb[dim]:
                    by_poem[poem_id][dim].append({'respondent': rec['row_index'], 'branch': branch, 'expertise': expertise, 'text': fb[dim], 'substantive': is_substantive(fb[dim]), 'char_length': len(fb[dim])})
    gradients: dict[str, dict] = {}
    for poem_id, dim_map in sorted(by_poem.items()):
        synth = {}
        for dim in DIMS:
            items = dim_map[dim]
            bullets = [f"- ({it['expertise']}) {it['text']}" for it in items if it['text']]
            synth[dim] = {'n': len(items), 'n_substantive': sum((1 for it in items if it['substantive'])), 'mean_char_length': round(sum((it['char_length'] for it in items)) / len(items), 1) if items else 0, 'items': items, 'aggregated_prompt_block': '\n'.join(bullets) if bullets else '(no feedback)'}
        gradients[poem_id] = {'poem_id': poem_id, 'n_respondents': len({it['respondent'] for d in DIMS for it in dim_map[d]}), 'dimensions': synth}
    branch_counts = defaultdict(int)
    expertise_counts = defaultdict(int)
    poem_counts = defaultdict(int)
    for r in respondents:
        branch_counts[r.get('branch') or '?'] += 1
        expertise_counts[r.get('expertise') or '?'] += 1
        if r.get('poem_id'):
            poem_counts[r['poem_id']] += 1
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    meta = {'parsed_utc': datetime.now(timezone.utc).isoformat(), 'source_xlsx': str(xlsx), 'n_responses': len(df), 'instrumentation': instr, 'branch_counts': dict(branch_counts), 'poem_counts': dict(poem_counts), 'expertise_counts': dict(expertise_counts), 'branch_poem_map': BRANCH_POEMS, 'note': "Export titled 'Aesthetic Rating' but columns are textual-gradient feedback (not 1-7 Likert). TOPSIS cannot be computed from this file."}
    (OUT_DIR / 'parse_meta.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
    (OUT_DIR / 'respondents.json').write_text(json.dumps(respondents, ensure_ascii=False, indent=2), encoding='utf-8')
    (OUT_DIR / 'gradients_by_poem.json').write_text(json.dumps(gradients, ensure_ascii=False, indent=2), encoding='utf-8')
    lines = ['# Survey 2 feedback synthesis (gen1)', '', f'- Source: `{xlsx.name}`', f'- N responses: **{len(df)}**', f"- Instrumentation: **{instr['instrument_type']}** (no Likert ratings in export)", f'- Branches: {dict(branch_counts)}', f'- Poems: {dict(poem_counts)}', f'- Expertise: {dict(expertise_counts)}', '']
    for poem_id, g in gradients.items():
        lines.append(f'## {poem_id}')
        lines.append(f"Respondents: {g['n_respondents']}")
        for dim in DIMS:
            d = g['dimensions'][dim]
            lines.append(f"### {dim} (n={d['n']}, substantive={d['n_substantive']}, avg_len={d['mean_char_length']})")
            lines.append(d['aggregated_prompt_block'])
            lines.append('')
    (OUT_DIR / 'gradients_summary.md').write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps(meta, ensure_ascii=False, indent=2))
    print(f'Wrote {OUT_DIR}')
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
