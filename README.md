# Poem Aesthetic Analysis

AI 生成莎士比亚十四行诗的审美调查与 TOPSIS 分析。

## 目录结构

```
poems/              gen0/gen1 诗歌与盲评刺激材料
iteration/          三轮问卷解析结果（survey1, survey2, survey2_likert）
analysis/           注意力/韵律探针模块与 integrated 输出
figures/            图表数据
*.py                生成、解析、分析入口脚本
wjx_*.jsonl         问卷星问卷配置
```

## 流水线

gen0 → Survey1（文本, N=6）→ gen1 → Survey2a（文本, N=10）→ Survey2b（Likert, N=12）→ TOPSIS

## 环境

```bash
pip install -r requirements.txt
```

复制 `.env.example` 为 `.env`，填入 `DEEPSEEK_API_KEY`（仅重新生成诗歌时需要）。

## 主要结果文件

- `iteration/survey2_likert/ratings_long.csv` — Likert 原始评分
- `analysis/outputs/integrated/topsis_by_lineage.csv` — TOPSIS 按谱系汇总

## 重新运行分析

```bash
python run_survey2_likert_analysis.py
python analysis/run_gen0_snapshot.py
```
