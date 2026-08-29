#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parent
STIMULI_DIR = ROOT / 'poems' / 'rating_stimuli'
MANIFEST = ROOT / 'poems' / 'rating_stimuli_manifest.json'
OUT_JSONL = ROOT / 'wjx_survey_likert.jsonl'
OUT_MD = ROOT / 'survey_likert_paste.md'
OUT_WJX_MD = ROOT / 'wenjuanxing_survey_likert_paste.md'
OUT_MAP = ROOT / 'survey_likert_blind_map.json'
THEMES = {'t1a': 'autumn departure', 't1b': 'autumn departure', 't2a': 'urban night solitude', 't2b': 'urban night solitude', 't3a': 'memory and water', 't3b': 'memory and water'}
BRANCHES = {'1': ('t1a', 'P01', 'P02'), '2': ('t1b', 'P03', 'P04'), '3': ('t2a', 'P05', 'P06'), '4': ('t2b', 'P07', 'P08'), '5': ('t3a', 'P09', 'P10'), '6': ('t3b', 'P11', 'P12')}
LIKERT_OPTS = ['1', '2', '3', '4', '5', '6', '7']

def poem_path(round_label: str, lineage: str) -> Path:
    return STIMULI_DIR / f'rate_{round_label}_{lineage}.txt'

def load_poem(round_label: str, lineage: str) -> str:
    path = poem_path(round_label, lineage)
    if not path.exists():
        raise FileNotFoundError(f'Missing {path}. Run: python generate_rating_stimuli.py')
    return path.read_text(encoding='utf-8').strip()

def jline(obj: dict) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(',', ':'))

def consent_and_background() -> list[str]:
    rows: list[str] = []
    rows.append(jline({'_meta': {'title': '英文十四行诗审美评分 Reading English Sonnets — Aesthetic Rating (Likert)', 'description': '请阅读两首英文十四行诗,在 Tension / Symbol(Imagery) / Rhythm 三维上各打 1-7 分。\nRead two sonnets and rate each on three 1-7 Likert scales. Blind study; ~8-12 min.\n请用六面骰子随机选择分支 1-6。'}}))
    rows.append(jline({'qtype': '段落说明', 'title': '【研究说明】参与自愿;数据仅用于学术研究。部分诗歌可能由模型生成。\n您将阅读两首诗并打分(1=很弱,7=优秀),不是写修改建议。\nVoluntary academic study. Rate poems 1-7; do NOT write revision suggestions.'}))
    rows.append(jline({'qtype': '单选题', 'title': '我同意参与本研究。I agree to participate.', 'options': ['同意 / Agree', '不同意 / Do not agree']}))
    rows.append(jline({'qtype': '单选题', 'title': '诗歌经验 How would you describe your poetry experience?\n1=业余 Amateur; 2=有一定基础 Intermediate; 3=较专业 Expert', 'options': ['业余/日常读者 Amateur', '有一定基础 Intermediate', '较专业 Expert']}))
    rows.append(jline({'qtype': '单选题', 'title': '英文格律诗评判自信(1-7)\nConfidence evaluating English formal verse (1-7)', 'options': LIKERT_OPTS}))
    rows.append(jline({'qtype': '单选题', 'title': '文学阅读主要语言 Primary language for literary reading', 'options': ['中文 Chinese', '英文 English', '其他 Other']}))
    rows.append(jline({'qtype': '单选题', 'title': '是否学习过莎士比亚体十四行诗? Have you studied Shakespearean sonnets?', 'options': ['是 Yes', '否 No']}))
    rows.append(jline({'qtype': '段落说明', 'title': '【评分说明】每首诗分别打三分: Tension 张力; Symbol(Imagery) 象征/意象; Rhythm 节奏/韵律(含 ABAB CDCD EFEF GG)。1=很弱, 7=优秀。\nRate EACH poem separately: Tension, Symbol(Imagery), Rhythm. 1=very weak, 7=excellent.'}))
    rows.append(jline({'qtype': '段落说明', 'title': '【随机选分支】掷六面骰: 点数 N → 分支 N (1-6)。秒数个位 1-6 亦可; 0/7/8/9 重掷。\n勿按喜好挑选。Roll die → Branch N. Do not choose by preference.'}))
    rows.append(jline({'qtype': '单选题', 'title': '骰子点数/随机结果? Die face / random outcome?', 'options': ['1', '2', '3', '4', '5', '6']}))
    rows.append(jline({'qtype': '单选题', 'title': '请选择对应评分分支 Select your rating branch', 'options': [f'分支{b} / Branch {b}' for b in BRANCHES]}))
    return rows

def likert_block(branch: str, poem_label: str, poem_code: str, text: str) -> list[str]:
    rows: list[str] = []
    rows.append(jline({'qtype': '段落说明', 'title': f'【分支{branch} · {poem_code}】请阅读下面这首诗,然后回答随后三题(1-7打分)。\n[Branch {branch} · {poem_code}] Read the sonnet, then rate the next three items.\n{text}'}))
    for dim in ('张力 Tension', '象征/意象 Symbol(Imagery)', '节奏/韵律 Rhythm'):
        rows.append(jline({'qtype': '单选题', 'title': f'【分支{branch} · {poem_code}】{dim} 评分 (1-7)', 'options': LIKERT_OPTS}))
    return rows

def build_jsonl() -> str:
    rows = consent_and_background()
    for branch, (lineage, code0, code1) in BRANCHES.items():
        text0 = load_poem('gen0', lineage)
        text1 = load_poem('gen1', lineage)
        rows.extend(likert_block(branch, 'Poem A', code0, text0))
        rows.extend(likert_block(branch, 'Poem B', code1, text1))
    rows.append(jline({'qtype': '简答题', 'title': '其他意见(选填) Any other comments (optional)'}))
    return '\n'.join(rows) + '\n'

def build_blind_map() -> dict:
    branches = {}
    for branch, (lineage, code0, code1) in BRANCHES.items():
        branches[branch] = {'lineage': lineage, 'theme': THEMES[lineage], 'poems': [{'display': code0, 'internal': f'rate_gen0_{lineage}', 'round': 'gen0', 'prompt_version': 'base_gen0', 'stimuli_file': f'rate_gen0_{lineage}.txt'}, {'display': code1, 'internal': f'rate_gen1_{lineage}', 'round': 'gen1', 'prompt_version': 'prompt_v1', 'stimuli_file': f'rate_gen1_{lineage}.txt'}]}
    return {'design': '6_branches_x_2_poems_gen0_gen1_likert', 'randomization': 'six_sided_die_face_equals_branch', 'stimuli_source': 'poems/rating_stimuli/ (fresh API generation, not poems/gen0|gen1)', 'instrument': 'likert_1_7_tension_symbol_rhythm', 'branches': branches}

def build_md(blind_map: dict) -> str:
    lines = ['# Survey — Likert Aesthetic Rating (fresh stimuli)', '', 'Each respondent: **one branch** → **two poems** (gen0 + gen1, same theme/variant) → **6 Likert scores**.', '', '## Branch map', '', '| Branch | Lineage | Poem A (blind) | Poem B (blind) | Theme |', '| --- | --- | --- | --- | --- |']
    for branch, (lineage, c0, c1) in BRANCHES.items():
        lines.append(f'| {branch} | {lineage} | {c0} | {c1} | {THEMES[lineage]} |')
    lines += ['', '## Staff blind map', '', '```json', json.dumps(blind_map, ensure_ascii=False, indent=2), '```', '', '## Import', '', '1. `python generate_rating_stimuli.py` — regenerate poems from prompts', '2. `python build_survey_likert.py` — build JSONL', '3. Import `wjx_survey_likert.jsonl` via WJX AI Kit', '4. Set display logic: branch N → only show branch N poem blocks + Likert items', '5. **Verify**: rating items are 1-7单选题, NOT 简答题/文字反馈', '', '## Poems', '']
    for branch, (lineage, c0, c1) in BRANCHES.items():
        lines.append(f'### Branch {branch} ({lineage})')
        lines.append(f'#### {c0} — rate_gen0_{lineage}')
        lines.append('```')
        lines.append(load_poem('gen0', lineage))
        lines.append('```')
        lines.append(f'#### {c1} — rate_gen1_{lineage}')
        lines.append('```')
        lines.append(load_poem('gen1', lineage))
        lines.append('```')
        lines.append('')
    return '\n'.join(lines)

def likert_item_block(branch: str, code: str, prefix: str) -> list[str]:
    return [f'### 单选 1–7 · `{prefix}_tension`', '', '```', f'【分支{branch} · {code}】张力 Tension（1–7）', f'[Branch {branch} · {code}] Tension (1–7)', '', '1 = 很弱 / very weak    7 = 优秀 / excellent', '```', '', '选项：`1` `2` `3` `4` `5` `6` `7`', '', f'### 单选 1–7 · `{prefix}_symbol`', '', '```', f'【分支{branch} · {code}】象征/意象 Symbol (Imagery)（1–7）', f'[Branch {branch} · {code}] Symbol (Imagery) (1–7)', '```', '', '选项：`1` `2` `3` `4` `5` `6` `7`', '', f'### 单选 1–7 · `{prefix}_rhythm`', '', '```', f'【分支{branch} · {code}】节奏/韵律 Rhythm（1–7）', f'[Branch {branch} · {code}] Rhythm (1–7)', '```', '', '选项：`1` `2` `3` `4` `5` `6` `7`', '']

def poem_section(branch: str, code: str, round_label: str, lineage: str, internal: str) -> list[str]:
    text = load_poem(round_label, lineage)
    prefix = f'b{branch}_{code.lower()}'
    lines = [f'### 分支 {branch} · {code}（工作人员：`{internal}`）', '', '**段落说明标题：**', '', '```', f'【分支{branch} · {code}】请阅读下面这首诗，然后回答随后三题（1–7 打分）。', f'[Branch {branch} · {code}] Please read the sonnet below, then rate the next three items (1–7).', '```', '', '**诗歌正文（仅英文）：**', '', '```', text, '```', '']
    lines.extend(likert_item_block(branch, code, prefix))
    return lines

def build_wjx_paste_md(blind_map: dict) -> str:
    lines = ['# 问卷星粘贴包 — Likert 审美评分 / Aesthetic Rating (Likert)', '', '用途 / Purpose：对 **两首** 英文十四行诗做盲测 **1–7 Likert 评分**（Tension / Symbol / Rhythm）。', '结构：**6 个分支 × 每人评 2 首**（同主题变体；盲码 P01–P12）；骰子点数 = 分支号。', '', '**双语规则：** 除诗歌正文外，说明与题干为中英双语。诗歌仅英文。', '对被试 **不显示** gen0/gen1、`rate_*` 等内部编号。', '', '**重要：** 本卷是 **打分**，不是写修改建议。题型必须是 **单选题 1–7**。', '', '配套 JSONL：[`wjx_survey_likert.jsonl`](wjx_survey_likert.jsonl)  ', '内部映射：[`survey_likert_blind_map.json`](survey_likert_blind_map.json)  ', '诗稿来源：`poems/rating_stimuli/`（prompt 重新生成，非旧 gen0/gen1 文件）', '', '---', '', '## 0. 分支分配（工作人员用）', '', '| 骰子 | 分支 | 诗 A（盲码） | 诗 B（盲码） | 内部 ID A | 内部 ID B | 主题 |', '| --- | --- | --- | --- | --- | --- | --- |']
    for branch, (lineage, c0, c1) in BRANCHES.items():
        lines.append(f'| {branch} | 分支{branch} | {c0} | {c1} | `rate_gen0_{lineage}` | `rate_gen1_{lineage}` | {THEMES[lineage]} |')
    lines += ['', '**整卷顺序：** 知情同意 → 背景 → 评分说明 → 骰子说明 → 记录点数 → 选分支 →', '（显示逻辑）对应 **2 首诗** + **6 道** 1–7 量表 → 结束选填。', '', '**显示逻辑：** 选「分支 N」时，仅显示该分支的两段诗歌说明 + 六道 1–7 题。', '', '---', '', '## 1. 问卷标题', '', '```', '英文十四行诗审美评分', 'Reading English Sonnets — Aesthetic Rating (Likert)', '```', '', '**问卷说明：**', '', '```', '本问卷请您阅读两首英文十四行诗，并在三个维度上分别打分（1–7）。', '预计用时约 8–12 分钟。答案无对错。请用六面骰子随机决定分支（1–6），勿按喜好挑选。', '', 'Please read TWO English sonnets and rate each on three dimensions (1–7).', 'Estimated time: about 8–12 minutes. There are no right or wrong answers.', 'Roll a six-sided die to choose your branch (1–6); do not choose by preference.', '```', '', '---', '', '## 2. 知情同意 / Informed Consent', '', '### 段落说明', '', '```', '研究说明 / Study Information', '```', '', '```', '您好！诚邀参与一项关于诗歌审美评分的学术研究。', 'Hello! You are invited to an academic study on aesthetic rating of poetry.', '', '【任务 / Task】', '您将阅读 2 首英文十四行诗，对每首分别就「张力 Tension」「象征/意象 Symbol (Imagery)」「节奏/韵律 Rhythm」打 1–7 分。', '请勿写修改建议，只需打分。', '', 'You will read 2 English sonnets and rate EACH on Tension, Symbol (Imagery), and Rhythm (1–7).', 'Do NOT write revision suggestions — only numeric ratings.', '', '【时间 / Duration】约 8–12 分钟。 / Approximately 8–12 minutes.', '', '【自愿 / Voluntary】参与完全自愿；可随时停止。 / Participation is voluntary.', '', '【数据 / Data】仅用于学术研究。 / For academic research only.', '', '【说明 / Note】部分诗歌可能由模型生成；作答期间不告知生成细节。', 'Some poems may be model-generated; technical details are withheld.', '```', '', '### 单选（必填）· `consent_agree`', '', '```', '我同意参与本研究。', 'I agree to participate in this study.', '```', '', '选项：', '', '```', '同意 / Agree', '不同意 / Do not agree', '```', '', '逻辑：选「不同意」→ 结束问卷。', '', '---', '', '## 3. 背景与专长 / Background', '', '### 单选 · `expertise_level`', '', '```', '您如何描述自己在诗歌（阅读或写作）方面的经验？', 'How would you describe your experience with poetry (reading or writing)?', '```', '', '```', '业余/日常读者 Amateur', '有一定基础 Intermediate', '较专业 Expert', '```', '', '### 单选 1–7 · `formal_verse_confidence`', '', '```', '您对英文格律诗（音步、押韵等）进行评判的自信程度？', '1 = 完全不自信，7 = 非常自信', '', 'Rate your confidence evaluating English formal verse (meter/rhyme).', '1 = not at all confident; 7 = highly confident', '```', '', '选项：`1` `2` `3` `4` `5` `6` `7`', '', '### 单选 · `primary_language`', '', '```', '文学阅读主要语言 Primary language for literary reading', '```', '', '```', '中文 Chinese', '英文 English', '其他 Other', '```', '', '### 单选 · `studied_sonnet`', '', '```', '是否学习或系统阅读过莎士比亚体十四行诗（14 行，韵式 ABAB CDCD EFEF GG）？', 'Have you studied Shakespearean sonnets?', '```', '', '```', '是 Yes', '否 No', '```', '', '---', '', '## 4. 评分维度说明 / Rating guidelines', '', '### 段落说明', '', '```', '请先阅读评分说明 / Please read the rating guidelines', '', '对下面每首诗，请在三个维度上打分：1 = 很弱，7 = 优秀。', 'Rate EACH poem on three dimensions: 1 = very weak, 7 = excellent.', '', '1）张力 Tension — 冲突、对照或未解决的张力是否支撑阅读兴趣。', '   Conflict, contrast, or unresolved force that sustains interest.', '', '2）象征/意象 Symbol (Imagery) — 具体感官意象与象征是否丰富、贴切。', '   Concrete sensory images and symbols that support meaning.', '', '3）节奏/韵律 Rhythm — 诗行节奏与莎士比亚体韵式 ABAB CDCD EFEF GG 的规范程度。', '   Line cadence and Shakespearean rhyme-scheme discipline.', '```', '', '---', '', '## 5. 随机分支 / Random branch', '', '### 段落说明', '', '```', '【如何选择分支 / How to choose your branch】', '', '请掷一枚六面骰子：点数是几，就选「分支几」（1→分支1 … 6→分支6）。', '也可用手机秒数个位 1–6；若为 0/7/8/9，请再看一次直到得到 1–6。', '请勿按个人喜好挑选。', '', 'Roll a six-sided die: face N → Branch N.', 'Or use the seconds digit 1–6 (retry if 0/7/8/9).', 'Do not choose a branch by preference.', '```', '', '### 单选 · `die_face`', '', '```', '您的骰子点数/随机结果是？', 'What die face / random outcome did you get?', '```', '', '选项：`1` `2` `3` `4` `5` `6`', '', '### 单选 · `survey_branch`（显示逻辑控制题）', '', '```', '请选择与上一题相同的评分分支。', 'Select the matching rating branch.', '```', '', '```', '分支1 / Branch 1', '分支2 / Branch 2', '分支3 / Branch 3', '分支4 / Branch 4', '分支5 / Branch 5', '分支6 / Branch 6', '```', '', '---', '', '## 6. 诗歌与评分题（每分支 2 首；显示逻辑）', '', '每分支结构：', '1. 段落说明 + 诗 A 正文 → 三道 1–7', '2. 段落说明 + 诗 B 正文 → 三道 1–7', '']
    for branch, (lineage, c0, c1) in BRANCHES.items():
        lines.append(f'---')
        lines.append('')
        lines.append(f'## 分支 {branch}（主题 / theme: {THEMES[lineage]}）')
        lines.append('')
        lines.extend(poem_section(branch, c0, 'gen0', lineage, f'rate_gen0_{lineage}'))
        lines.extend(poem_section(branch, c1, 'gen1', lineage, f'rate_gen1_{lineage}'))
    lines += ['---', '', '## 7. 结束 / Closing', '', '### 简答题（选填）· `comments`', '', '```', '如有其他意见或对任务的感受，欢迎留言（选填）。', 'Any other comments about the task are welcome (optional).', '```', '', '---', '', '## 8. 导入与发布检查清单 / Import checklist', '', '1. 优先用 `wjx_survey_likert.jsonl` 通过 AI Kit / CLI 创建问卷。', '2. 设置显示逻辑：分支 N → 仅分支 N 的 2 首诗 + 6 道评分题。', '3. 「不同意」→ 跳转结束。', '4. **预览必查：** 评分题为单选 1–7，**没有**「写修改建议」开放题（除最后选填）。', '5. 每个分支尽量多收几份（建议 ≥5–8），便于后续均值 / TOPSIS。', '6. 导出 Excel 后列名应含 `评分 (1-7)` 或选项 1–7，而非 `actionable suggestions`。', '', '## 9. 重新生成诗稿与问卷', '', '```bash', 'python stage1/generate_rating_stimuli.py', 'python stage1/build_survey_likert.py', '```', '']
    return '\n'.join(lines)

def main() -> int:
    if not MANIFEST.exists():
        raise SystemExit('Missing rating stimuli. Run: python generate_rating_stimuli.py')
    blind_map = build_blind_map()
    for branch, (lineage, _, _) in BRANCHES.items():
        load_poem('gen0', lineage)
        load_poem('gen1', lineage)
    OUT_JSONL.write_text(build_jsonl(), encoding='utf-8')
    OUT_MD.write_text(build_md(blind_map), encoding='utf-8')
    OUT_WJX_MD.write_text(build_wjx_paste_md(blind_map), encoding='utf-8')
    OUT_MAP.write_text(json.dumps(blind_map, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Wrote {OUT_JSONL}')
    print(f'Wrote {OUT_MD}')
    print(f'Wrote {OUT_WJX_MD}')
    print(f'Wrote {OUT_MAP}')
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
