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
OUT_DIR = ROOT / 'poems' / 'gen0'
MANIFEST_PATH = ROOT / 'poems' / 'gen0_manifest.json'
THEMES = [('t1', 'autumn departure'), ('t2', 'urban night solitude'), ('t3', 'memory and water')]
VARIANTS = ('a', 'b')
SYSTEM_PROMPT = 'You are a careful formal poet. Write exactly one Shakespearean sonnet in English.\nHard requirements:\n- Exactly 14 lines of verse (no title, no blank line between stanzas unless needed for readability; prefer no blank lines).\n- Rhyme scheme ABAB CDCD EFEF GG.\n- Approximate iambic pentameter when possible.\n- Output ONLY the 14 lines of the poem. No preamble, no commentary, no quotes, no markdown.'

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
        if re.match('^(sonnet|title|theme)\\b', ln, re.I):
            continue
        if re.match('^\\d+[\\.)]\\s*', ln):
            ln = re.sub('^\\d+[\\.)]\\s*', '', ln)
        cleaned.append(ln)
    if len(cleaned) >= 14:
        return cleaned[:14]
    return None

def call_deepseek(api_key: str, theme: str, variant: str) -> tuple[str, dict]:
    payload = {'model': MODEL, 'temperature': TEMPERATURE, 'max_tokens': MAX_TOKENS, 'messages': [{'role': 'system', 'content': SYSTEM_PROMPT}, {'role': 'user', 'content': user_prompt(theme, variant)}]}
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(API_URL, data=data, headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {api_key}'}, method='POST')
    with urllib.request.urlopen(req, timeout=120) as resp:
        body = json.loads(resp.read().decode('utf-8'))
    content = body['choices'][0]['message']['content']
    meta = {'id': body.get('id'), 'model': body.get('model', MODEL), 'usage': body.get('usage')}
    return (content, meta)

def generate_one(api_key: str, poem_id: str, theme: str, variant: str, retries: int=3) -> dict:
    last_err: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            raw, api_meta = call_deepseek(api_key, theme, variant)
            lines = extract_fourteen_lines(raw)
            if not lines:
                raise ValueError(f'Could not parse 14 lines (attempt {attempt}): {raw[:200]!r}')
            text = '\n'.join(lines) + '\n'
            return {'id': poem_id, 'theme': theme, 'variant': variant, 'model': api_meta.get('model', MODEL), 'temperature': TEMPERATURE, 'created_utc': datetime.now(timezone.utc).isoformat(), 'system_prompt': SYSTEM_PROMPT, 'user_prompt': user_prompt(theme, variant), 'api_id': api_meta.get('id'), 'usage': api_meta.get('usage'), 'attempts': attempt, 'text': text, 'lines': lines}
        except (urllib.error.HTTPError, urllib.error.URLError, KeyError, ValueError, TimeoutError) as e:
            last_err = e
            if isinstance(e, urllib.error.HTTPError):
                detail = e.read().decode('utf-8', errors='replace')
                print(f'HTTP {e.code} on {poem_id} attempt {attempt}: {detail}', file=sys.stderr)
            else:
                print(f'Error on {poem_id} attempt {attempt}: {e}', file=sys.stderr)
            time.sleep(1.5 * attempt)
    raise RuntimeError(f'Failed to generate {poem_id}: {last_err}')

def main() -> int:
    api_key = os.environ.get('DEEPSEEK_API_KEY', '').strip()
    if not api_key:
        env_path = ROOT / '.env'
        if env_path.exists():
            for line in env_path.read_text(encoding='utf-8').splitlines():
                if line.strip().startswith('DEEPSEEK_API_KEY='):
                    api_key = line.split('=', 1)[1].strip().strip('"').strip("'")
                    break
    if not api_key:
        print('DEEPSEEK_API_KEY is not set. Export it or put it in stage1/.env', file=sys.stderr)
        return 1
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    records: list[dict] = []
    for theme_key, theme in THEMES:
        for variant in VARIANTS:
            poem_id = f'gen0_{theme_key}{variant}'
            print(f'Generating {poem_id} ({theme}, variant {variant})...')
            rec = generate_one(api_key, poem_id, theme, variant)
            out_file = OUT_DIR / f'{poem_id}.txt'
            out_file.write_text(rec['text'], encoding='utf-8')
            print(f'  wrote {out_file}')
            records.append({k: v for k, v in rec.items() if k != 'text'})
            records[-1]['path'] = str(out_file.relative_to(ROOT))
            records[-1]['text'] = rec['text']
    manifest = {'generated_utc': datetime.now(timezone.utc).isoformat(), 'model': MODEL, 'temperature': TEMPERATURE, 'api_url': API_URL, 'poems': records}
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Wrote manifest {MANIFEST_PATH}')
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
