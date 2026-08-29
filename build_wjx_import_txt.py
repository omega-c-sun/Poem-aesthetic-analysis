#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
ROOT = Path(__file__).resolve().parent
POEM_DIR = ROOT / 'poems' / 'gen0'
OUT = ROOT / 'wjx_survey1_import.txt'
README = ROOT / 'wjx_import_README.md'
BRANCHES = {'A': ['gen0_t1a', 'gen0_t2a', 'gen0_t3a'], 'B': ['gen0_t1b', 'gen0_t2b', 'gen0_t3b'], 'C': ['gen0_t1a', 'gen0_t2b', 'gen0_t3a']}

def norm(text: str) -> str:
    return text.replace('—', '-').replace('–', '-').replace('‘', "'").replace('’', "'").replace('“', '"').replace('”', '"').strip()

def load_poems() -> dict[str, str]:
    poems: dict[str, str] = {}
    for path in POEM_DIR.glob('gen0_*.txt'):
        poems[path.stem] = norm(path.read_text(encoding='utf-8'))
    missing = {pid for ids in BRANCHES.values() for pid in ids} - set(poems)
    if missing:
        raise FileNotFoundError(f'Missing poems: {sorted(missing)}')
    return poems

def para(text: str) -> str:
    return f'{text.strip()}\n段落说明'

def fill(q: str) -> str:
    return f'{q.strip()}________\n填空题'

def blank() -> str:
    return ''

def build(poems: dict[str, str]) -> str:
    parts: list[str] = []
    parts.append('英文十四行诗阅读与修改建议 Reading English Sonnets and Revision Suggestions')
    parts.append(blank())
    parts.append(para('本问卷邀请您阅读三首英文十四行诗(sonnet),并就三个审美维度给出具体修改建议。预计用时15-25分钟。答案无对错。\nThis questionnaire asks you to read three English sonnets and give concrete revision suggestions on three aesthetic dimensions. Estimated time: 15-25 minutes.'))
    parts.append(blank())
    parts.append(para('【研究说明 Study Information】\n您好!诚邀参与诗歌审美判断与修改建议研究。参与自愿,可随时退出。\nHello! You are invited to a study on poetic aesthetic judgment and revision suggestions. Participation is voluntary; you may stop anytime.\n回答仅用于学术研究;不作个人身份公开披露。Responses are for academic research only; no public disclosure of personal identity.\n部分诗歌可能由模型生成;作答期间不告知生成细节。Some poems may be model-generated; generation details are withheld during the survey.'))
    parts.append(blank())
    parts.append('1. 我已阅读以上说明,并同意参与本研究。\nI have read the information above and agree to participate.\nA. 同意,继续作答 / Agree - continue\nB. 不同意,退出问卷 / Do not agree - exit')
    parts.append(blank())
    parts.append('2. 您如何描述自己在诗歌(阅读或写作)方面的经验?\nHow would you describe your experience with poetry (reading or writing)?\nA. 业余/日常读者 - Amateur / casual reader\nB. 有一定基础 - Intermediate (coursework or regular reading)\nC. 较专业 - Expert (advanced study, publication, teaching, or practice)')
    parts.append(blank())
    parts.append('3. 您对英文格律诗(音步、押韵等)进行评判的自信程度?\nRate your confidence evaluating English formal verse (meter/rhyme).\n1=完全不自信 not at all confident; 7=非常自信 highly confident\nA. 1\nB. 2\nC. 3\nD. 4\nE. 5\nF. 6\nG. 7')
    parts.append(blank())
    parts.append(fill('4. 您进行文学阅读时最常用的主要语言是?(例如:中文、英文)\nWhat is your primary language for literary reading? (e.g., Chinese, English)'))
    parts.append(blank())
    parts.append('5. 您是否学习或系统阅读过莎士比亚体十四行诗(Shakespearean sonnet: 14行, 韵式 ABAB CDCD EFEF GG)?\nHave you studied Shakespearean sonnets?\nA. 是 / Yes\nB. 否 / No\nC. 不确定 / Unsure')
    parts.append(blank())
    parts.append(para('【评判说明 Guidelines】请写具体、可执行的修改指令,避免空泛评价(如"更好一点")。\nPlease write specific, actionable revision instructions; avoid vague comments (e.g., "make it better").\n1) Tension 张力: 冲突/对照/未解决张力是否支撑阅读兴趣。 Conflict/contrast/unresolved force sustaining interest.\n2) Symbol(Imagery) 象征意象: 感官意象与象征是否贴切。 Concrete imagery and symbols supporting meaning.\n3) Rhythm 节奏韵律: 行节奏与莎士比亚体韵式 ABAB CDCD EFEF GG。 Cadence and rhyme-scheme discipline.\n诗歌正文为英文;建议可用中文或英文。 Poem texts are in English; suggestions may be Chinese or English.'))
    parts.append(blank())
    parts.append(para('【如何随机选择分支 How to choose your branch】\n本平台无法自动随机分配。请您用相对客观的随机方式决定分支,例如:\nThis platform cannot auto-assign branches. Please use an objective random method, e.g.:\n方式1: 掷一枚六面骰子。1或2=分支A; 3或4=分支B; 5或6=分支C。\nMethod 1: Roll one six-sided die. 1-2=Branch A; 3-4=Branch B; 5-6=Branch C.\n方式2: 看手机秒数个位。1-2或7-8=A; 3-4或9/0=B; 5-6=C。\nMethod 2: Use the units digit of the current seconds on your phone: 1-2 or 7-8=A; 3-4 or 9/0=B; 5-6=C.\n请先完成随机,再作答下面两题,并按结果选择分支。勿按个人喜好挑选。\nComplete the random draw first, then answer the next two items. Do not choose a branch by preference.'))
    parts.append(blank())
    parts.append('6. 您用于决定分支的随机结果是?(骰子点数或秒数个位)\nWhat random outcome did you get? (die face or seconds digit)\nA. 1\nB. 2\nC. 3\nD. 4\nE. 5\nF. 6\nG. 7\nH. 8\nI. 9\nJ. 0')
    parts.append(blank())
    parts.append('7. 请根据上一题随机结果选择问卷分支(1-2或7-8=A; 3-4或9/0=B; 5-6=C)。\nSelect your branch from the random outcome (1-2 or 7-8=A; 3-4 or 9/0=B; 5-6=C).\nA. 分支A / Branch A\nB. 分支B / Branch B\nC. 分支C / Branch C')
    parts.append(blank())
    for branch, ids in BRANCHES.items():
        for i, pid in enumerate(ids, start=1):
            poem = poems[pid]
            parts.append(para(f'【分支{branch} Branch {branch}】诗歌{i} / Poem {i}\n(内部编号 staff id: {pid} - 被试无需关注)\n请完整阅读下列英文十四行诗,然后回答随后三题。\nPlease read the English sonnet below in full, then answer the next three items.\n---- poem begin ----\n{poem}\n---- poem end ----'))
            parts.append(blank())
            parts.append(fill(f'【分支{branch}-诗{i}】张力 Tension: 为提升本诗张力,请写可执行修改建议。\nTension: actionable suggestions to improve tension.'))
            parts.append(blank())
            parts.append(fill(f'【分支{branch}-诗{i}】象征/意象 Symbol(Imagery): 为提升象征与意象,请写可执行修改建议。\nSymbol(Imagery): actionable suggestions to improve symbolism/imagery.'))
            parts.append(blank())
            parts.append(fill(f'【分支{branch}-诗{i}】节奏/韵律 Rhythm: 为提升节奏与押韵规范,请写可执行修改建议。\nRhythm: actionable suggestions to improve rhythm/rhyme discipline.'))
            parts.append(blank())
    parts.append(para('感谢您完成本问卷!您的修改建议将用于后续提示词迭代研究。\nThank you! Your revision suggestions will be used for later prompt-iteration research.'))
    parts.append(blank())
    parts.append(fill('如有其他意见或对任务的感受,欢迎留言(选填)。\nAny other comments about the task are welcome (optional).'))
    parts.append(blank())
    return '\n'.join(parts).rstrip() + '\n'

def write_readme() -> None:
    README.write_text('# 问卷星文本导入说明 (Survey 1)\n\n## 文件\n\n- `wjx_survey1_import.txt`：可导入问卷星的纯文本问卷\n- 本说明：导入步骤与导入后必做设置\n\n## 导入步骤\n\n1. 打开 [问卷星](https://www.wjx.cn) → 创建问卷 → 问卷调查\n2. 选择 **导入文本** / **从文本创建**\n3. 用记事本打开 `wjx_survey1_import.txt`，全选复制\n4. 粘贴到左侧文本框 → 右侧预览题型是否正确\n5. 确认生成后进入编辑页，再点保存/完成编辑\n\n若右侧把「段落说明」识别错了：点该题 → 改题型为「段落说明」。  \n若开放题不是多行：点填空题 → 改为多行文本。\n\n## 导入后必做：显示逻辑\n\n文本导入**不会**自动建立分支显示逻辑。请手动设置：\n\n- 控制题：第 7 题「选择问卷分支」(字段可记为 `survey_branch`)\n- 当选 **分支A** → 仅显示所有标题含「分支A」的诗歌说明与三道开放题\n- 当选 **分支B** → 仅显示「分支B」题组\n- 当选 **分支C** → 仅显示「分支C」题组\n- 结束语始终显示\n\n路径：题目 → 逻辑设置 / 显示逻辑 / 题目关联\n\n## 骰子/随机规则（已写进问卷）\n\n| 随机结果 | 分支 |\n| --- | --- |\n| 1, 2（或秒数 7, 8） | A |\n| 3, 4（或秒数 9, 0） | B |\n| 5, 6 | C |\n\n第 6 题记录随机结果，第 7 题选分支，便于事后核对是否按规则选择。\n\n## 同意题跳转\n\n第 1 题选「不同意」→ 设置跳转到问卷结束。\n\n## 若导入仍异常\n\n- 用 Chrome，勿用异常插件\n- 先只导入前 5 题测试识别\n- 诗歌段过长时可改为插图（保留题干开放题）\n', encoding='utf-8')

def main() -> int:
    poems = load_poems()
    OUT.write_text(build(poems), encoding='utf-8')
    write_readme()
    print(f'Wrote {OUT}')
    print(f'Wrote {README}')
    print(f'Chars: {OUT.stat().st_size}')
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
