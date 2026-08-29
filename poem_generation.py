from __future__ import annotations
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
API_URL = 'https://api.deepseek.com/chat/completions'
MODEL = 'deepseek-chat'
TEMPERATURE = 0.85
MAX_TOKENS = 800
ROOT = Path(__file__).resolve().parent
BASE_SYSTEM = 'You are a careful formal poet. Write exactly one Shakespearean sonnet in English.\nHard requirements:\n- Exactly 14 lines of verse (no title; prefer no blank lines between stanzas).\n- Rhyme scheme ABAB CDCD EFEF GG.\n- Approximate iambic pentameter when possible.\n- Output ONLY the 14 lines of the poem. No preamble, no commentary, no quotes, no markdown.'
THEMES = [('t1', 'autumn departure'), ('t2', 'urban night solitude'), ('t3', 'memory and water')]
VARIANTS = ('a', 'b')

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

def load_prompt_v1_addendum() -> str:
    path = ROOT / 'iteration' / 'survey1' / 'prompt_v1.json'
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding='utf-8'))['system_addendum'].strip()

def gen1_system() -> str:
    addendum = load_prompt_v1_addendum()
    return BASE_SYSTEM + '\n\nAesthetic principles from human textual-gradient feedback (general; theme-agnostic):\n' + addendum
