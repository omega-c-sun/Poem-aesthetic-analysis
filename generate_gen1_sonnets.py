#!/usr/bin/env python3
from __future__ import annotations
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
API_URL = 'https://api.deepseek.com/chat/completions'
MODEL = 'deepseek-chat'
TEMPERATURE = 0.85
MAX_TOKENS = 800
ROOT = Path(__file__).resolve().parent
PROMPT_V1 = ROOT / 'iteration' / 'survey1' / 'prompt_v1.json'
OUT_DIR = ROOT / 'poems' / 'gen1'
MANIFEST_PATH = ROOT / 'poems' / 'gen1_manifest.json'
THEMES = [('t1', 'autumn departure'), ('t2', 'urban night solitude'), ('t3', 'memory and water')]
VARIANTS = ('a', 'b')
BASE_SYSTEM = 'You are a careful formal poet. Write exactly one Shakespearean sonnet in English.\nHard requirements:\n- Exactly 14 lines of verse (no title; prefer no blank lines between stanzas).\n- Rhyme scheme ABAB CDCD EFEF GG.\n- Approximate iambic pentameter when possible.\n- Output ONLY the 14 lines of the poem. No preamble, no commentary, no quotes, no markdown.'

def load_api_key() -> str:
    key = os.environ.get('DEEPSEEK_API_KEY', '').strip()
    if key:
        return key
    env_path = ROOT / '.env'
    if env_path.exists():
        for line in env_path.read_text(encoding='utf-8').splitlines():
            if line.strip().startswith('DEEPSEEK_API_KEY='):
                return line.split('=', 1)[1].strip().strip('"').strip("'")
    return ''

def user_prompt(theme: str, variant: str) -> str:
    angle = {'a': 'Favor a reflective, restrained tone.', 'b': 'Favor a slightly more dramatic volta in the sestet.'}[variant]
    return f'Theme: {theme}.\nVariant note: {angle}\nWrite one original Shakespearean sonnet on this theme.'

def extract_fourteen_lines(text: str) -> list[str] | None:
    raw = text.strip()
    raw = re.sub('^```(?:\\w+)?\\s*', '', raw)
    raw = re.sub('\\s*```$', '', raw)
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    cleaned: list[str] = []
    for ln in lines:
        if re.match('^(sonnet|title|theme|revised)\\b', ln, re.I):
            continue
        if re.match('^\\d+[\\.)]\\s*', ln):
            ln = re.sub('^\\d+[\\.)]\\s*', '', ln)
        cleaned.append(ln)
    if len(cleaned) >= 14:
        return cleaned[:14]
    return None

def call_deepseek(api_key: str, system: str, user: str) -> tuple[str, dict]:
    payload = {'model': MODEL, 'temperature': TEMPERATURE, 'max_tokens': MAX_TOKENS, 'messages': [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}]}
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(API_URL, data=data, headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {api_key}'}, method='POST')
    with urllib.request.urlopen(req, timeout=180) as resp:
        body = json.loads(resp.read().decode('utf-8'))
    content = body['choices'][0]['message']['content']
    meta = {'id': body.get('id'), 'model': body.get('model', MODEL), 'usage': body.get('usage')}
    return (content, meta)

def main() -> int:
    api_key = load_api_key()
    if not api_key:
        print('DEEPSEEK_API_KEY missing', file=sys.stderr)
        return 1
    if not PROMPT_V1.exists():
        print(f'Missing {PROMPT_V1}; run synthesize_general_prompt_v1.py first', file=sys.stderr)
        return 1
    prompt_v1 = json.loads(PROMPT_V1.read_text(encoding='utf-8'))
    addendum = prompt_v1['system_addendum'].strip()
    system = BASE_SYSTEM + '\n\nAesthetic principles from human textual-gradient feedback (general; theme-agnostic):\n' + addendum
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    records = []
    for theme_key, theme in THEMES:
        for variant in VARIANTS:
            poem_id = f'gen1_{theme_key}{variant}'
            parent_id = f'gen0_{theme_key}{variant}'
            up = user_prompt(theme, variant)
            print(f'Generating {poem_id} (theme={theme}, general prompt_v1)...')
            last_err: Exception | None = None
            rec = None
            for attempt in range(1, 4):
                try:
                    raw, api_meta = call_deepseek(api_key, system, up)
                    lines = extract_fourteen_lines(raw)
                    if not lines:
                        raise ValueError(f'parse fail: {raw[:200]!r}')
                    text = '\n'.join(lines) + '\n'
                    out_file = OUT_DIR / f'{poem_id}.txt'
                    out_file.write_text(text, encoding='utf-8')
                    rec = {'id': poem_id, 'corresponds_to_gen0_id': parent_id, 'theme': theme, 'variant': variant, 'prompt_version': 'prompt_v1', 'method': 'general_prompt_plus_theme_only', 'model': api_meta.get('model', MODEL), 'temperature': TEMPERATURE, 'created_utc': datetime.now(timezone.utc).isoformat(), 'system_prompt': system, 'user_prompt': up, 'api_id': api_meta.get('id'), 'usage': api_meta.get('usage'), 'attempts': attempt, 'path': str(out_file.relative_to(ROOT)), 'text': text, 'lines': lines}
                    print(f'  wrote {out_file}')
                    break
                except (urllib.error.HTTPError, urllib.error.URLError, KeyError, ValueError, TimeoutError) as e:
                    last_err = e
                    if isinstance(e, urllib.error.HTTPError):
                        detail = e.read().decode('utf-8', errors='replace')
                        print(f'HTTP {e.code} attempt {attempt}: {detail}', file=sys.stderr)
                    else:
                        print(f'Error attempt {attempt}: {e}', file=sys.stderr)
                    time.sleep(1.5 * attempt)
            if rec is None:
                raise RuntimeError(f'Failed {poem_id}: {last_err}')
            records.append(rec)
            time.sleep(0.4)
    manifest = {'generated_utc': datetime.now(timezone.utc).isoformat(), 'model': MODEL, 'temperature': TEMPERATURE, 'api_url': API_URL, 'prompt_version': 'prompt_v1', 'method': 'general_textual_gradient; user message = theme(+variant) only; no prior poem patching', 'source_prompt': str(PROMPT_V1.relative_to(ROOT)), 'poems': records}
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Wrote {MANIFEST_PATH} ({len(records)} poems)')
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
