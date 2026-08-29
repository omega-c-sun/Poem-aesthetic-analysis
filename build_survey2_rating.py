#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parent
GEN1 = ROOT / 'poems' / 'gen1'
OUT_MD = ROOT / 'survey2_rating_paste.md'
OUT_JSONL = ROOT / 'wjx_survey2_rating.jsonl'
OUT_MAP = ROOT / 'survey2_blind_map.json'
BRANCHES = {'1': ('P01', 'gen1_t1a'), '2': ('P02', 'gen1_t1b'), '3': ('P03', 'gen1_t2a'), '4': ('P04', 'gen1_t2b'), '5': ('P05', 'gen1_t3a'), '6': ('P06', 'gen1_t3b')}
THEMES = {'t1a': 'autumn departure', 't1b': 'autumn departure', 't2a': 'urban night solitude', 't2b': 'urban night solitude', 't3a': 'memory and water', 't3b': 'memory and water'}

def load_poem(poem_id: str) -> str:
    path = GEN1 / f'{poem_id}.txt'
    if not path.exists():
        raise FileNotFoundError(path)
    return path.read_text(encoding='utf-8').strip()

def jline(obj: dict) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(',', ':'))

def build_jsonl() -> str:
    rows: list[str] = []
    rows.append(jline({'_meta': {'title': '英文十四行诗审美评分 Reading English Sonnets - Aesthetic Rating', 'description': '请阅读一首英文十四行诗,并在 Tension / Symbol(Imagery) / Rhythm 三维上打分(1-7)。\nRead one English sonnet and rate three dimensions (1-7). Blind study; ~3-5 minutes.\n请用六面骰子随机选择分支 1-6。'}}))
    rows.append(jline({'qtype': '段落说明', 'title': '【研究说明】参与自愿;数据仅用于学术研究。部分诗歌可能由模型生成。\nVoluntary academic study. Some poems may be model-generated.'}))
    rows.append(jline({'qtype': '单选题', 'title': '我同意参与本研究。I agree to participate.', 'options': ['同意 / Agree', '不同意 / Do not agree']}))
    rows.append(jline({'qtype': '单选题', 'title': '诗歌经验 How would you describe your poetry experience?\n1=业余 Amateur; 2=有一定基础 Intermediate; 3=较专业 Expert', 'options': ['业余/日常读者 Amateur', '有一定基础 Intermediate', '较专业 Expert']}))
    rows.append(jline({'qtype': '单选题', 'title': '英文格律诗评判自信(1-7)\nConfidence evaluating English formal verse (1-7)', 'options': ['1', '2', '3', '4', '5', '6', '7']}))
    rows.append(jline({'qtype': '段落说明', 'title': '评分维度: Tension 张力; Symbol(Imagery) 象征/意象; Rhythm 节奏/韵律(含 ABAB CDCD EFEF GG)。1=很弱, 7=优秀。\nRate 1=very weak ... 7=excellent.'}))
    rows.append(jline({'qtype': '段落说明', 'title': '【随机选分支】请掷一枚六面骰子,点数几就选分支几(1→分支1 … 6→分支6)。也可用手机秒数个位:1-6对应分支;若为0/7/8/9请再掷/再看一次直到1-6。勿按个人喜好挑选。\nRoll a six-sided die: face N → Branch N. Or use seconds digit 1-6 (retry if 0/7/8/9). Do not choose by preference.'}))
    rows.append(jline({'qtype': '单选题', 'title': '您的骰子点数/随机结果是? What die face / random outcome did you get?', 'options': ['1', '2', '3', '4', '5', '6']}))
    rows.append(jline({'qtype': '单选题', 'title': '请选择与上一题相同的评分分支 Select the matching rating branch', 'options': ['分支1 / Branch 1', '分支2 / Branch 2', '分支3 / Branch 3', '分支4 / Branch 4', '分支5 / Branch 5', '分支6 / Branch 6']}))
    for branch, (code, poem_id) in BRANCHES.items():
        text = load_poem(poem_id)
        rows.append(jline({'qtype': '段落说明', 'title': f'【分支{branch}】请阅读下面这首诗,然后回答随后三题。\n[Branch {branch}] Read the sonnet, then answer the next three items.\n{text}'}))
        for dim_cn in ('张力 Tension', '象征/意象 Symbol(Imagery)', '节奏/韵律 Rhythm'):
            rows.append(jline({'qtype': '单选题', 'title': f'【分支{branch}】{dim_cn} (1-7)', 'options': ['1', '2', '3', '4', '5', '6', '7']}))
    rows.append(jline({'qtype': '简答题', 'title': '其他意见(选填) Any other comments (optional)'}))
    return '\n'.join(rows) + '\n'

def build_md(blind_map: dict) -> str:
    lines = ['# Survey 2 — Aesthetic Rating (gen1 only, 6×1)', '', 'Blind Likert 1–7. Each respondent rates **one gen1** sonnet.', '', '## Branch design', '', '| Die | Branch | Display | Internal ID | Theme |', '| --- | --- | --- | --- | --- |']
    for branch, (code, poem_id) in BRANCHES.items():
        key = poem_id.replace('gen1_', '')
        theme = THEMES.get(key, '')
        lines.append(f'| {branch} | 分支{branch} | {code} | `{poem_id}` | {theme} |')
    lines += ['', 'Random: six-sided die face = branch number.', '', '## Staff blind map (do not show participants)', '', '```json', json.dumps(blind_map, ensure_ascii=False, indent=2), '```', '', '## Import', '', 'Use `wjx_survey2_rating.jsonl`. Set display logic per branch; disagree→end.', '', '## Poems (gen1)', '']
    for branch, (code, poem_id) in BRANCHES.items():
        lines.append(f'### Branch {branch} / {code} ← `{poem_id}`')
        lines.append('```')
        lines.append(load_poem(poem_id))
        lines.append('```')
        lines.append('')
    return '\n'.join(lines)

def main() -> int:
    blind_map = {'design': '6_branches_x_1_gen1_poem', 'randomization': 'six_sided_die_face_equals_branch', 'generation': 'gen1_only', 'branches': {b: {'display': code, 'internal': pid} for b, (code, pid) in BRANCHES.items()}}
    for _, pid in BRANCHES.values():
        load_poem(pid)
    OUT_JSONL.write_text(build_jsonl(), encoding='utf-8')
    OUT_MD.write_text(build_md(blind_map), encoding='utf-8')
    OUT_MAP.write_text(json.dumps(blind_map, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Wrote {OUT_JSONL}')
    print(f'Wrote {OUT_MD}')
    print(f'Wrote {OUT_MAP}')
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
