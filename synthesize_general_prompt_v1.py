#!/usr/bin/env python3
from __future__ import annotations
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
API_URL = 'https://api.deepseek.com/chat/completions'
MODEL = 'deepseek-chat'
ROOT = Path(__file__).resolve().parent
GRADIENTS = ROOT / 'iteration' / 'survey1' / 'gradients_by_poem.json'
OUT_DIR = ROOT / 'iteration' / 'survey1'
OUT_JSON = OUT_DIR / 'prompt_v1.json'
OUT_TXT = OUT_DIR / 'prompt_v1_system_addendum.txt'
DISTILL_SYSTEM = 'You distill human poetry-revision feedback into GENERAL generative principles.\nOutput MUST be valid JSON only (no markdown fences).\nSchema:\n{\n  "tension": ["principle1", "principle2", ...],\n  "symbol": ["...", ...],\n  "rhythm": ["...", ...],\n  "system_addendum": "A concise English paragraph (or short bullet list) to APPEND to a sonnet-generation system prompt."\n}\nHard rules:\n- Principles must be theme-agnostic and reusable across different poem themes.\n- Do NOT quote specific lines from any reviewed poem.\n- Do NOT give rewrite recipes of the form "change this line from A to B" tied to one poem.\n- Do NOT mention particular poem IDs or prior drafts.\n- Form/genre is FIXED elsewhere (Shakespearean sonnet); do not change the form.\n- Prefer actionable craft guidance on Tension, Symbol/Imagery, and Rhythm.\n- Write principles and system_addendum in clear English.\n- Ignore non-actionable comments (praise-only, jokes, "nothing to change").'

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

def collect_feedback_corpus(gradients: dict) -> str:
    chunks: list[str] = []
    for poem_id, g in sorted(gradients.items()):
        for dim in ('tension', 'symbol', 'rhythm'):
            for it in g['dimensions'][dim]['items']:
                text = (it.get('text') or '').strip()
                if not text or text in {'/', '同上', '（空）', '(空)'}:
                    continue
                chunks.append(f"[{dim} | expertise={it.get('expertise')} | from_poem={poem_id}]\n{text}")
    return '\n\n'.join(chunks)

def call_deepseek_json(api_key: str, user: str) -> dict:
    payload = {'model': MODEL, 'temperature': 0.3, 'max_tokens': 1200, 'messages': [{'role': 'system', 'content': DISTILL_SYSTEM}, {'role': 'user', 'content': user}]}
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(API_URL, data=data, headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {api_key}'}, method='POST')
    with urllib.request.urlopen(req, timeout=180) as resp:
        body = json.loads(resp.read().decode('utf-8'))
    content = body['choices'][0]['message']['content'].strip()
    content = re.sub('^```(?:json)?\\s*', '', content)
    content = re.sub('\\s*```$', '', content)
    return (json.loads(content), body)

def main() -> int:
    api_key = load_api_key()
    if not api_key:
        print('DEEPSEEK_API_KEY missing', file=sys.stderr)
        return 1
    gradients = json.loads(GRADIENTS.read_text(encoding='utf-8'))
    corpus = collect_feedback_corpus(gradients)
    user = f'Distill the following human feedback (from a first survey on Shakespearean sonnets) into general generative principles. Remember: generation will ONLY vary the theme; the form stays Shakespearean sonnet.\n\nFEEDBACK CORPUS:\n{corpus}'
    print('Distilling general prompt_v1 via DeepSeek...')
    distilled, raw = call_deepseek_json(api_key, user)
    addendum = distilled.get('system_addendum', '').strip()
    if not addendum:
        raise RuntimeError('Empty system_addendum from distill model')
    record = {'version': 'prompt_v1', 'created_utc': datetime.now(timezone.utc).isoformat(), 'method': 'general_textual_gradient_distillation', 'model': raw.get('model', MODEL), 'api_id': raw.get('id'), 'usage': raw.get('usage'), 'form_fixed': 'Shakespearean sonnet (14 lines, ABAB CDCD EFEF GG, approx iambic pentameter)', 'varies_at_generation': ['theme', 'variant_tone_note'], 'principles': {'tension': distilled.get('tension', []), 'symbol': distilled.get('symbol', []), 'rhythm': distilled.get('rhythm', [])}, 'system_addendum': addendum, 'generation_contract': 'At generation time, use BASE sonnet system prompt + system_addendum; user message only supplies Theme (+ optional variant note). Do NOT attach previous poem text or poem-specific patch instructions.', 'source_gradients': str(GRADIENTS.relative_to(ROOT)), 'n_feedback_chunks': corpus.count('\n\n') + 1 if corpus else 0}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    OUT_TXT.write_text(addendum + '\n', encoding='utf-8')
    print(f'Wrote {OUT_JSON}')
    print(f'Wrote {OUT_TXT}')
    print('--- system_addendum ---')
    print(addendum)
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
