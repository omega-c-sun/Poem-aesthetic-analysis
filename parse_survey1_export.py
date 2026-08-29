#!/usr/bin/env python3
from __future__ import annotations
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parent
DEFAULT_XLSX = Path('c:\\Users\\孙行知\\Downloads\\379305445_按序号_英文十四行诗阅读与修改建议 Reading English Sonnets  Revision Suggestions_6_6.xlsx')
OUT_DIR = ROOT / 'iteration' / 'survey1'
BRANCH_POEMS = {'A': ['gen0_t1a', 'gen0_t2a', 'gen0_t3a'], 'B': ['gen0_t1b', 'gen0_t2b', 'gen0_t3b'], 'C': ['gen0_t1a', 'gen0_t2b', 'gen0_t3a']}
DIMS = ('tension', 'symbol', 'rhythm')

def find_col(columns: list[str], *needles: str) -> str:
    for c in columns:
        if all((n.lower() in str(c).lower() for n in needles)):
            return c
    raise KeyError(f'No column matching {needles}')

def find_cols_containing(columns: list[str], needle: str) -> list[str]:
    return [c for c in columns if needle.lower() in str(c).lower()]

def parse_branch(val: object) -> str | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    s = str(val).strip()
    if s in {'1', '1.0'}:
        return 'A'
    if s in {'2', '2.0'}:
        return 'B'
    if s in {'3', '3.0'}:
        return 'C'
    m = re.search('分支\\s*([ABC])|Branch\\s*([ABC])', s, re.I)
    if m:
        return (m.group(1) or m.group(2)).upper()
    for letter in ('A', 'B', 'C'):
        if f'分支{letter}' in s or f'Branch {letter}' in s or f'Branch{letter}' in s:
            return letter
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

def is_substantive(text: str) -> bool:
    t = text.strip()
    if not t or t in {'/', '同上', '同第二', '（空）', '(空)'}:
        return False
    if t.startswith('同第二'):
        return False
    if len(t) < 8 and t in {'没什么要改的', '没法改吧'}:
        return False
    return True

def clean_text(val: object) -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ''
    return str(val).strip()

def main() -> int:
    xlsx = Path(DEFAULT_XLSX)
    if not xlsx.exists():
        downloads = Path('c:\\Users\\孙行知\\Downloads')
        cands = sorted(downloads.glob('*Revision Suggestions*.xlsx'), key=lambda p: p.stat().st_mtime)
        if not cands:
            raise FileNotFoundError(xlsx)
        xlsx = cands[-1]
    df = pd.read_excel(xlsx)
    cols = list(df.columns)
    col_agree = find_col(cols, 'agree to participate')
    col_expertise = find_col(cols, 'experience with poetry')
    col_confidence = find_col(cols, 'confidence evaluating')
    col_lang = find_col(cols, 'primary language')
    col_sonnet = find_col(cols, 'studied shakespearean')
    col_branch = find_col(cols, 'select your branch')
    tension_cols = find_cols_containing(cols, 'tension:')
    symbol_cols = find_cols_containing(cols, 'symbol(imagery)')
    rhythm_cols = find_cols_containing(cols, 'rhythm:')
    tension_cols = sorted(tension_cols, key=lambda c: cols.index(c))
    symbol_cols = sorted(symbol_cols, key=lambda c: cols.index(c))
    rhythm_cols = sorted(rhythm_cols, key=lambda c: cols.index(c))
    if not len(tension_cols) == len(symbol_cols) == len(rhythm_cols) >= 3:
        raise RuntimeError(f'Expected >=3 poem slots; got T={len(tension_cols)} S={len(symbol_cols)} R={len(rhythm_cols)}')
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
        rec = {'row_index': int(i) + 1, 'branch': branch, 'expertise': expertise, 'formal_verse_confidence': conf_n, 'primary_language': clean_text(row[col_lang]), 'studied_sonnet': clean_text(row[col_sonnet]), 'consent': clean_text(row[col_agree]), 'poems': []}
        if branch not in BRANCH_POEMS:
            rec['error'] = f'unparsed branch: {row[col_branch]!r}'
            respondents.append(rec)
            continue
        poem_ids = BRANCH_POEMS[branch]
        for slot, poem_id in enumerate(poem_ids):
            fb = {'tension': clean_text(row[tension_cols[slot]]), 'symbol': clean_text(row[symbol_cols[slot]]), 'rhythm': clean_text(row[rhythm_cols[slot]])}
            rec['poems'].append({'poem_id': poem_id, 'slot': slot + 1, 'feedback': fb})
            for dim in DIMS:
                if fb[dim]:
                    by_poem[poem_id][dim].append({'respondent': rec['row_index'], 'branch': branch, 'expertise': expertise, 'text': fb[dim]})
        respondents.append(rec)
    gradients: dict[str, dict] = {}
    for poem_id, dim_map in sorted(by_poem.items()):
        synth = {}
        for dim in DIMS:
            items = dim_map[dim]
            bullets_all = []
            bullets_actionable = []
            for it in items:
                tag = it['expertise']
                line = f"- ({tag}) {it['text']}"
                bullets_all.append(line)
                if is_substantive(it['text']):
                    bullets_actionable.append(line)
            use_bullets = bullets_actionable or bullets_all
            synth[dim] = {'n': len(items), 'n_substantive': len(bullets_actionable), 'items': items, 'aggregated_prompt_block': '\n'.join(use_bullets) if use_bullets else '(no feedback)'}
        n_raters = len({it['respondent'] for d in DIMS for it in dim_map[d]})
        gradients[poem_id] = {'poem_id': poem_id, 'n_respondents_with_text': n_raters, 'dimensions': synth, 'user_prompt_addon': f"Revise the previous Shakespearean sonnet using the following human textual-gradient feedback. Keep exactly 14 lines and rhyme scheme ABAB CDCD EFEF GG. Output ONLY the 14 lines.\n\n=== Tension ===\n{synth['tension']['aggregated_prompt_block']}\n\n=== Symbol (Imagery) ===\n{synth['symbol']['aggregated_prompt_block']}\n\n=== Rhythm ===\n{synth['rhythm']['aggregated_prompt_block']}\n"}
    branch_counts = defaultdict(int)
    expertise_counts = defaultdict(int)
    for r in respondents:
        branch_counts[r.get('branch') or '?'] += 1
        expertise_counts[r.get('expertise') or '?'] += 1
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    meta = {'parsed_utc': datetime.now(timezone.utc).isoformat(), 'source_xlsx': str(xlsx), 'n_responses': len(df), 'branch_counts': dict(branch_counts), 'expertise_counts': dict(expertise_counts), 'branch_poem_map': BRANCH_POEMS, 'note': 'Export had 3 poem slots after branch select; poem IDs inferred from survey_branch via BRANCH_POEMS.'}
    (OUT_DIR / 'parse_meta.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
    (OUT_DIR / 'respondents.json').write_text(json.dumps(respondents, ensure_ascii=False, indent=2), encoding='utf-8')
    (OUT_DIR / 'gradients_by_poem.json').write_text(json.dumps(gradients, ensure_ascii=False, indent=2), encoding='utf-8')
    lines = ['# Survey 1 feedback synthesis', '', f'- Source: `{xlsx.name}`', f'- N responses: **{len(df)}**', f'- Branches: {dict(branch_counts)}', f'- Expertise: {dict(expertise_counts)}', '']
    for poem_id, g in gradients.items():
        lines.append(f'## {poem_id}')
        lines.append(f"Respondents with text: {g['n_respondents_with_text']}")
        for dim in DIMS:
            lines.append(f'### {dim}')
            lines.append(g['dimensions'][dim]['aggregated_prompt_block'])
            lines.append('')
    (OUT_DIR / 'gradients_summary.md').write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps(meta, ensure_ascii=False, indent=2))
    print(f'Wrote {OUT_DIR}')
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
