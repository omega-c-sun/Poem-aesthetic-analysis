#!/usr/bin/env python3
from __future__ import annotations
import json
import sys
import time
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from poem_generation import API_URL, BASE_SYSTEM, MODEL, TEMPERATURE, THEMES, VARIANTS, call_deepseek, extract_fourteen_lines, gen1_system, load_api_key, user_prompt
ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / 'poems' / 'rating_stimuli'
MANIFEST = ROOT / 'poems' / 'rating_stimuli_manifest.json'

def generate_one(api_key: str, *, round_label: str, system: str, theme_key: str, theme: str, variant: str, prompt_version: str) -> dict:
    poem_id = f'rate_{round_label}_{theme_key}{variant}'
    up = user_prompt(theme, variant)
    print(f'Generating {poem_id} ...')
    last_err: Exception | None = None
    for attempt in range(1, 4):
        try:
            raw, api_meta = call_deepseek(api_key, system, up)
            lines = extract_fourteen_lines(raw)
            if not lines:
                raise ValueError(f'parse fail: {raw[:200]!r}')
            text = '\n'.join(lines) + '\n'
            out_file = OUT_DIR / f'{poem_id}.txt'
            out_file.write_text(text, encoding='utf-8')
            print(f'  wrote {out_file.name}')
            return {'id': poem_id, 'round': round_label, 'theme': theme, 'variant': variant, 'prompt_version': prompt_version, 'method': 'fresh_api_generation_for_likert_survey', 'model': api_meta.get('model', MODEL), 'temperature': TEMPERATURE, 'created_utc': datetime.now(timezone.utc).isoformat(), 'system_prompt': system, 'user_prompt': up, 'api_id': api_meta.get('id'), 'usage': api_meta.get('usage'), 'attempts': attempt, 'path': str(out_file.relative_to(ROOT)), 'text': text, 'lines': lines}
        except (urllib.error.HTTPError, urllib.error.URLError, KeyError, ValueError, TimeoutError) as e:
            last_err = e
            print(f'  attempt {attempt} failed: {e}', file=sys.stderr)
            time.sleep(1.5 * attempt)
    raise RuntimeError(f'Failed {poem_id}: {last_err}')

def main() -> int:
    api_key = load_api_key()
    if not api_key:
        print('DEEPSEEK_API_KEY missing', file=sys.stderr)
        return 1
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    records: list[dict] = []
    gen1_sys = gen1_system()
    for theme_key, theme in THEMES:
        for variant in VARIANTS:
            records.append(generate_one(api_key, round_label='gen0', system=BASE_SYSTEM, theme_key=theme_key, theme=theme, variant=variant, prompt_version='base_gen0'))
            time.sleep(0.4)
            records.append(generate_one(api_key, round_label='gen1', system=gen1_sys, theme_key=theme_key, theme=theme, variant=variant, prompt_version='prompt_v1'))
            time.sleep(0.4)
    manifest = {'generated_utc': datetime.now(timezone.utc).isoformat(), 'purpose': 'Likert rating survey stimuli (fresh generation; not poems/gen0 or poems/gen1)', 'api_url': API_URL, 'model': MODEL, 'temperature': TEMPERATURE, 'n_poems': len(records), 'poems': records}
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Wrote {MANIFEST} ({len(records)} poems)')
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
