#!/usr/bin/env python3
from __future__ import annotations
import re
from pathlib import Path
ROOT = Path(__file__).resolve().parent
GEN0 = ROOT / 'poems' / 'gen0'
POEM_IDS = ['gen0_t1a', 'gen0_t1b', 'gen0_t2a', 'gen0_t2b', 'gen0_t3a', 'gen0_t3b']
RATING_MAP = {'gen0_t1a': 'P01', 'gen0_t1b': 'P04', 'gen0_t2a': 'P07', 'gen0_t2b': 'P10', 'gen0_t3a': 'P13', 'gen0_t3b': 'P16'}

def load_poems() -> dict[str, str]:
    poems: dict[str, str] = {}
    for pid in POEM_IDS:
        path = GEN0 / f'{pid}.txt'
        if not path.exists():
            raise FileNotFoundError(f'Missing {path}; run generate_gen0_sonnets.py first')
        poems[pid] = path.read_text(encoding='utf-8').strip() + '\n'
    return poems

def replace_fenced_after_heading(text: str, heading: str, poem: str) -> str:
    pattern = re.compile(f'(^###[^\\n]*{re.escape(heading)}[^\\n]*\\n\\n```\\n)(.*?)(\\n```)', re.M | re.S)
    new_text, n = pattern.subn(f'\\g<1>{poem.rstrip()}\\g<3>', text, count=1)
    if n != 1:
        raise RuntimeError(f'Could not locate fenced block for heading containing {heading!r}')
    return new_text

def main() -> int:
    poems = load_poems()
    survey1 = ROOT / 'survey1_feedback_draft.md'
    s1 = survey1.read_text(encoding='utf-8')
    for pid, poem in poems.items():
        s1 = replace_fenced_after_heading(s1, f'`{pid}`', poem)
    survey1.write_text(s1, encoding='utf-8')
    print(f'Updated {survey1}')
    rating = ROOT / 'survey_rating_draft.md'
    r = rating.read_text(encoding='utf-8')
    for pid, poem in poems.items():
        code = RATING_MAP[pid]
        r = replace_fenced_after_heading(r, f'{code} / {pid}', poem)
    rating.write_text(r, encoding='utf-8')
    print(f'Updated {rating}')
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
