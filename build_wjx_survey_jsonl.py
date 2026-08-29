#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parent
POEM_DIR = ROOT / 'poems' / 'gen0'
OUT = ROOT / 'wjx_survey1.jsonl'
README = ROOT / 'wjx_jsonl_README.md'
BRANCHES = {'A': ['gen0_t1a', 'gen0_t2a', 'gen0_t3a'], 'B': ['gen0_t1b', 'gen0_t2b', 'gen0_t3b'], 'C': ['gen0_t1a', 'gen0_t2b', 'gen0_t3a']}

def norm(text: str) -> str:
    return text.replace('—', '-').replace('–', '-').replace('‘', "'").replace('’', "'").replace('“', '"').replace('”', '"').strip()

def load_poems() -> dict[str, str]:
    poems = {p.stem: norm(p.read_text(encoding='utf-8')) for p in POEM_DIR.glob('gen0_*.txt')}
    missing = {pid for ids in BRANCHES.values() for pid in ids} - set(poems)
    if missing:
        raise FileNotFoundError(f'Missing poems: {sorted(missing)}')
    return poems

def line(obj: dict) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(',', ':'))

def build(poems: dict[str, str]) -> str:
    rows: list[str] = []
    rows.append(line({'_meta': {'title': '英文十四行诗阅读与修改建议 Reading English Sonnets and Revision Suggestions', 'description': '本问卷邀请您阅读三首英文十四行诗并给出三维修改建议。预计15-25分钟。请用骰子或手机秒数随机选择分支A/B/C。\nRead three English sonnets and give revision suggestions on three dimensions. 15-25 min. Use a die or phone-seconds digit to pick branch A/B/C.'}}))
    rows.append(line({'qtype': '段落说明', 'title': '【研究说明 Study Information】\n您好!诚邀参与诗歌审美判断与修改建议研究。参与自愿,可随时退出。\nHello! You are invited to a study on poetic aesthetic judgment and revision suggestions. Participation is voluntary; you may stop anytime.\n回答仅用于学术研究;不作个人身份公开披露。Responses are for academic research only.\n部分诗歌可能由模型生成;作答期间不告知生成细节。Some poems may be model-generated; details withheld during the survey.'}))
    rows.append(line({'qtype': '单选题', 'title': '我已阅读以上说明,并同意参与本研究。\nI have read the information above and agree to participate.', 'options': ['同意,继续作答 / Agree - continue', '不同意,退出问卷 / Do not agree - exit']}))
    rows.append(line({'qtype': '单选题', 'title': '您如何描述自己在诗歌(阅读或写作)方面的经验?\nHow would you describe your experience with poetry (reading or writing)?', 'options': ['业余/日常读者 - Amateur / casual reader', '有一定基础 - Intermediate (coursework or regular reading)', '较专业 - Expert (advanced study, publication, teaching, or practice)']}))
    rows.append(line({'qtype': '单选题', 'title': '您对英文格律诗(音步、押韵等)进行评判的自信程度?\nRate your confidence evaluating English formal verse (meter/rhyme).\n1=完全不自信 not at all confident; 7=非常自信 highly confident', 'options': ['1', '2', '3', '4', '5', '6', '7']}))
    rows.append(line({'qtype': '简答题', 'title': '您进行文学阅读时最常用的主要语言是?(例如:中文、英文)\nWhat is your primary language for literary reading? (e.g., Chinese, English)'}))
    rows.append(line({'qtype': '单选题', 'title': '您是否学习或系统阅读过莎士比亚体十四行诗(Shakespearean sonnet: 14行, 韵式 ABAB CDCD EFEF GG)?\nHave you studied Shakespearean sonnets?', 'options': ['是 / Yes', '否 / No', '不确定 / Unsure']}))
    rows.append(line({'qtype': '段落说明', 'title': '【评判说明 Guidelines】请写具体、可执行的修改指令,避免空泛评价。\nPlease write specific, actionable revision instructions; avoid vague comments.\n1) Tension 张力: 冲突/对照/未解决张力。 Conflict/contrast/unresolved force.\n2) Symbol(Imagery) 象征意象: 感官意象与象征。 Concrete imagery and symbols.\n3) Rhythm 节奏韵律: 行节奏与韵式 ABAB CDCD EFEF GG。 Cadence and rhyme scheme.\n诗歌正文为英文;建议可用中文或英文。 Poems in English; suggestions may be CN/EN.'}))
    rows.append(line({'qtype': '段落说明', 'title': '【如何随机选择分支 How to choose your branch】\n本平台无法自动随机分配。请用相对客观的随机方式决定分支。\nThis platform cannot auto-assign. Use an objective random method.\n方式1 掷六面骰: 1或2=A; 3或4=B; 5或6=C。\nMethod 1 die: 1-2=A; 3-4=B; 5-6=C.\n方式2 手机秒数个位: 1-2或7-8=A; 3-4或9/0=B; 5-6=C。\nMethod 2 seconds digit: 1-2 or 7-8=A; 3-4 or 9/0=B; 5-6=C.\n请先随机,再答下面两题。勿按喜好挑选。 Draw first, then answer the next two items. Do not choose by preference.'}))
    rows.append(line({'qtype': '单选题', 'title': '您用于决定分支的随机结果是?(骰子点数或秒数个位)\nWhat random outcome did you get? (die face or seconds digit)', 'options': ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0']}))
    rows.append(line({'qtype': '单选题', 'title': '请根据上一题随机结果选择问卷分支(1-2或7-8=A; 3-4或9/0=B; 5-6=C)。\nSelect your branch from the random outcome (1-2 or 7-8=A; 3-4 or 9/0=B; 5-6=C).\n[字段名建议 survey_branch / use this item for display logic]', 'options': ['分支A / Branch A', '分支B / Branch B', '分支C / Branch C']}))
    for branch, ids in BRANCHES.items():
        for i, pid in enumerate(ids, start=1):
            poem = poems[pid]
            rows.append(line({'qtype': '段落说明', 'title': f'【分支{branch} Branch {branch}】诗歌{i} / Poem {i}\n(staff id: {pid})\n请完整阅读下列英文十四行诗,然后回答随后三题。\nPlease read the English sonnet below in full, then answer the next three items.\n---- poem begin ----\n{poem}\n---- poem end ----'}))
            rows.append(line({'qtype': '简答题', 'title': f'【分支{branch}-诗{i}】张力 Tension: 为提升本诗张力,请写可执行修改建议。\nTension: actionable suggestions to improve tension.'}))
            rows.append(line({'qtype': '简答题', 'title': f'【分支{branch}-诗{i}】象征/意象 Symbol(Imagery): 为提升象征与意象,请写可执行修改建议。\nSymbol(Imagery): actionable suggestions to improve symbolism/imagery.'}))
            rows.append(line({'qtype': '简答题', 'title': f'【分支{branch}-诗{i}】节奏/韵律 Rhythm: 为提升节奏与押韵规范,请写可执行修改建议。\nRhythm: actionable suggestions to improve rhythm/rhyme discipline.'}))
    rows.append(line({'qtype': '段落说明', 'title': '感谢您完成本问卷!您的修改建议将用于后续提示词迭代研究。\nThank you! Your revision suggestions will be used for later prompt-iteration research.'}))
    rows.append(line({'qtype': '简答题', 'title': '如有其他意见或对任务的感受,欢迎留言(选填)。\nAny other comments about the task are welcome (optional).'}))
    return '\n'.join(rows) + '\n'

def write_readme(n_lines: int) -> None:
    README.write_text(f'# 问卷星 JSONL（AI Kit / create_survey_by_json）\n\n## 结论\n\n可以。问卷星 **AI Kit** 官方推荐用 **JSONL**（每行一道题）创建问卷，接口为 `create_survey_by_json`。  \n这比网页富文本编辑器更稳，也比「导入文本」覆盖题型更全。\n\n已生成：`wjx_survey1.jsonl`（约 {n_lines} 行）。\n\n## 三种用法（按推荐度）\n\n### 1）CLI（最稳，需 API Key）\n\n1. 在问卷星账号获取 OpenAPI Key  \n2. 安装：`npm i -g wjx-cli`（或以官方文档为准）  \n3. 执行：\n\n```bash\nset WJX_API_KEY=你的密钥\nwjx survey create-by-json --file stage1/wjx_survey1.jsonl --type 1\n```\n\n### 2）网页 AI / AIKit 对话\n\n若你的「AI 添加」支持粘贴结构化题目：\n\n1. 用记事本打开 `wjx_survey1.jsonl`\n2. 全选复制，粘贴到 AI 对话框，说明：  \n   「请用这份 JSONL 调用 create_survey_by_json 创建调查问卷，不要改题目内容」\n3. 若 AI 只接受自然语言：可说「按附件 JSONL 原样创建」，或改用 CLI\n\n> 注意：网页普通「导入文本」吃的是 `.txt` DSL，**不是** JSONL。JSONL 走 AI Kit / API。\n\n### 3）Cursor + 问卷星 MCP\n\n配置 `wjx-mcp-server` 与 `WJX_API_KEY` 后，让 Agent 读取本文件并调用 `create_survey_by_json`。\n\n## JSONL 结构（本文件）\n\n| 行类型 | 字段 |\n| --- | --- |\n| 首行元数据 | `{{"_meta":{{"title","description"}}}}` |\n| 段落说明 | `{{"qtype":"段落说明","title":"..."}}` |\n| 单选 | `{{"qtype":"单选题","title":"...","options":[...]}}` |\n| 开放题 | `{{"qtype":"简答题","title":"..."}}` |\n\n诗歌正文嵌在对应「段落说明」的 `title` 里（含换行）。\n\n## 导入后仍需手动\n\n1. **显示逻辑**：第「选择问卷分支」题 → 仅显示对应「分支A/B/C」题组  \n2. **同意题跳转**：选「不同意」→ 结束问卷  \n3. 预览检查长段落/诗歌换行是否正常  \n\n显示逻辑一般**不会**写进 JSONL 创建结果。\n\n## 与 txt 导入的关系\n\n| 文件 | 用途 |\n| --- | --- |\n| `wjx_survey1_import.txt` | 网页「导入文本」 |\n| `wjx_survey1.jsonl` | AI Kit / CLI / MCP（推荐） |\n\n优先试 JSONL；若你只有网页且无 API，继续用 txt。\n', encoding='utf-8')

def main() -> int:
    poems = load_poems()
    body = build(poems)
    OUT.write_text(body, encoding='utf-8')
    n = body.count('\n')
    write_readme(n)
    print(f'Wrote {OUT} ({n} lines, {OUT.stat().st_size} bytes)')
    print(f'Wrote {README}')
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
