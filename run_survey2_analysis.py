#!/usr/bin/env python3
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats
ROOT = Path(__file__).resolve().parent
SURVEY1_GRAD = ROOT / 'iteration' / 'survey1' / 'gradients_by_poem.json'
SURVEY2_DIR = ROOT / 'iteration' / 'survey2'
OUT_DIR = ROOT / 'analysis' / 'outputs' / 'integrated'
FIG_DIR = ROOT / 'figures'
GEN0_CSV = ROOT / 'analysis' / 'outputs' / 'gen0' / 'gen0_metrics.csv'
GEN1_CSV = ROOT / 'analysis' / 'outputs' / 'gen1' / 'gen1_metrics.csv'
PAIRED_CSV = FIG_DIR / 'attn_metrics_paired.csv'

def run_parse() -> None:
    subprocess.run([sys.executable, str(ROOT / 'parse_survey2_export.py')], check=True)

def load_paired_attention() -> pd.DataFrame:
    g0 = pd.read_csv(GEN0_CSV)
    g1 = pd.read_csv(GEN1_CSV)
    g0['lineage'] = g0['poem_id'].str.replace('^gen0_', '', regex=True)
    g1['lineage'] = g1['poem_id'].str.replace('^gen1_', '', regex=True)
    paired = g0.merge(g1, on=['lineage', 'theme', 'variant'], suffixes=('_g0', '_g1'))
    paired['d_entropy'] = paired['entropy_mean_g1'] - paired['entropy_mean_g0']
    paired['d_rhyme'] = paired['rhyme_share_mean_g1'] - paired['rhyme_share_mean_g0']
    paired['d_phoneme_pairs'] = paired['phoneme_agree_pairs_g1'] - paired['phoneme_agree_pairs_g0']
    return paired.sort_values('lineage')

def wilcoxon_report(x: np.ndarray) -> dict:
    x = np.asarray(x, dtype=float)
    if len(x) < 3:
        return {'n': len(x), 'mean': float(x.mean()), 'note': 'too few pairs for test'}
    try:
        stat, p = stats.wilcoxon(x, zero_method='wilcox', alternative='two-sided')
    except ValueError:
        stat, p = (np.nan, np.nan)
    return {'n': len(x), 'mean': round(float(x.mean()), 6), 'median': round(float(np.median(x)), 6), 'wilcoxon_stat': float(stat) if stat == stat else None, 'p_value': round(float(p), 4) if p == p else None}

def bootstrap_ci(x: np.ndarray, n_boot: int=5000, alpha: float=0.05) -> tuple[float, float]:
    rng = np.random.default_rng(42)
    x = np.asarray(x, dtype=float)
    means = [rng.choice(x, size=len(x), replace=True).mean() for _ in range(n_boot)]
    lo = float(np.percentile(means, 100 * alpha / 2))
    hi = float(np.percentile(means, 100 * (1 - alpha / 2)))
    return (round(lo, 4), round(hi, 4))

def feedback_metrics(gradients_path: Path, generation: str) -> pd.DataFrame:
    data = json.loads(gradients_path.read_text(encoding='utf-8'))
    rows = []
    for poem_id, g in data.items():
        lineage = poem_id.replace(f'{generation}_', '')
        dims = g.get('dimensions', g)
        dim_block = dims if 'tension' in dims else g.get('dimensions', {})
        for dim in ('tension', 'symbol', 'rhythm'):
            d = dim_block[dim]
            items = d.get('items', [])
            char_lens = [len(it.get('text', '')) for it in items] or [0]
            rows.append({'poem_id': poem_id, 'lineage': lineage, 'generation': generation, 'dimension': dim, 'n_feedback': d['n'], 'n_substantive': d.get('n_substantive', sum((1 for it in items if it.get('text')))), 'mean_char_length': d.get('mean_char_length') or round(float(np.mean(char_lens)), 1)})
    return pd.DataFrame(rows)

def poem_level_feedback(grad_df: pd.DataFrame) -> pd.DataFrame:
    return grad_df.groupby(['poem_id', 'lineage', 'generation'], as_index=False).agg(total_feedback=('n_feedback', 'sum'), total_substantive=('n_substantive', 'sum'), mean_char_length=('mean_char_length', 'mean'))

def correlate_feedback_attention(fb_gen1: pd.DataFrame, paired: pd.DataFrame) -> pd.DataFrame:
    m = fb_gen1.merge(paired, on='lineage')
    rows = []
    for col in ('d_entropy', 'd_rhyme', 'd_phoneme_pairs'):
        for fb_col in ('total_substantive', 'mean_char_length'):
            if m[fb_col].std() == 0 or m[col].std() == 0:
                r, p = (np.nan, np.nan)
            else:
                r, p = stats.spearmanr(m[fb_col], m[col])
            rows.append({'attention_delta': col, 'feedback_metric': fb_col, 'spearman_r': round(float(r), 4) if r == r else None, 'p_value': round(float(p), 4) if p == p else None, 'n': len(m)})
    return pd.DataFrame(rows)

def df_to_md_table(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    lines = ['| ' + ' | '.join(cols) + ' |', '| ' + ' | '.join(['---'] * len(cols)) + ' |']
    for _, row in df.iterrows():
        lines.append('| ' + ' | '.join((str(row[c]) for c in cols)) + ' |')
    return '\n'.join(lines)

def build_report(meta: dict, attn_tests: dict, fb_compare: pd.DataFrame, corr: pd.DataFrame, paired: pd.DataFrame) -> str:
    lines = ['# Stage 1 Integrated Analysis Report', '', '## Data integration', '', f"- Survey 2 source: `{Path(meta['source_xlsx']).name}`", f"- N = **{meta['n_responses']}** respondents", f"- Branch coverage: {meta['branch_counts']}", f"- Poem coverage: {meta['poem_counts']}", f"- Expertise: {meta['expertise_counts']}", '', '### Instrumentation note', '', meta['note'], '', 'The deployed export contains **textual revision feedback** on gen1 poems, not blind 1–7 Likert ratings. Therefore **TOPSIS aesthetic scores (RQ1 primary DV) cannot be estimated** from this file. Results below use (a) attention-metric paired comparisons gen0→gen1 and (b) second-round feedback descriptives.', '', '## Attention metrics (gen0 → gen1, n=6 lineages)', '', '| Lineage | Δ entropy | Δ rhyme-share | Δ phoneme-agree pairs |', '| --- | ---: | ---: | ---: |']
    for _, r in paired.iterrows():
        lines.append(f"| {r['lineage']} | {r['d_entropy']:+.4f} | {r['d_rhyme']:+.4f} | {int(r['d_phoneme_pairs']):+d} |")
    lines.extend(['', '### Inferential tests (Wilcoxon signed-rank, two-sided)', '', f"- Δ entropy: {attn_tests['d_entropy']}", f"- Δ rhyme-share: {attn_tests['d_rhyme']}", f"- Δ phoneme-agree pairs: {attn_tests['d_phoneme_pairs']}", '', 'Directional pattern is **mixed** and not significant at α=.05 with n=6 pairs (entropy rose on 4/6 lineages; rhyme-share fell on 5/6). This does not support H2 as stated.', '', '## Gen1 feedback (Survey 2)', '', df_to_md_table(fb_compare), '', '## Exploratory: feedback volume vs attention Δ (Spearman, n=6)', '', df_to_md_table(corr), '', '## Conclusions (preliminary)', '', '1. **Intervention chain completed:** gen0 → textual-gradient prompt → gen1; attention logged for both rounds.', '2. **RQ1 (TOPSIS):** Pending — re-field blind Likert rating survey or recover correct export.', '3. **RQ2 (attention mediation):** Descriptively, gen1 does not show uniform rhyme-attention redistribution; inferential power is low (n=6). Mediation untestable without TOPSIS DV.', '4. **RQ3 (expertise moderation):** Survey 2 includes 2 expert-level self-reports (intermediate=7, amateur=1, expert=2); insufficient for confirmatory moderated mediation.', '5. **Qualitative:** Gen1 feedback remains detailed and actionable across all six poems, suggesting further iteration (gen2) is feasible; rhythm/rhyme issues are still frequently cited.', '', '## Recommended next steps', '', '1. Deploy correct Survey 2 Likert instrument (`wjx_survey2_rating.jsonl`) for gen0+gen1 blind rating.', '2. Optionally distill Survey 2 feedback → `prompt_v2` and generate gen2.', '3. Re-run TOPSIS + mediation once Likert data exist.', ''])
    return '\n'.join(lines)

def main() -> int:
    run_parse()
    meta = json.loads((SURVEY2_DIR / 'parse_meta.json').read_text(encoding='utf-8'))
    paired = load_paired_attention()
    paired.to_csv(PAIRED_CSV, index=False)
    attn_tests = {'d_entropy': {**wilcoxon_report(paired['d_entropy'].to_numpy()), 'ci95': bootstrap_ci(paired['d_entropy'].to_numpy())}, 'd_rhyme': {**wilcoxon_report(paired['d_rhyme'].to_numpy()), 'ci95': bootstrap_ci(paired['d_rhyme'].to_numpy())}, 'd_phoneme_pairs': {**wilcoxon_report(paired['d_phoneme_pairs'].to_numpy()), 'ci95': bootstrap_ci(paired['d_phoneme_pairs'].to_numpy())}}
    fb0 = feedback_metrics(SURVEY1_GRAD, 'gen0')
    fb1 = feedback_metrics(SURVEY2_DIR / 'gradients_by_poem.json', 'gen1')
    fb0_poem = poem_level_feedback(fb0)
    fb1_poem = poem_level_feedback(fb1)
    cmp = fb0_poem.rename(columns={'total_feedback': 'fb_count_gen0', 'total_substantive': 'substantive_gen0', 'mean_char_length': 'chars_gen0'}).merge(fb1_poem.rename(columns={'total_feedback': 'fb_count_gen1', 'total_substantive': 'substantive_gen1', 'mean_char_length': 'chars_gen1'}), on='lineage', how='outer')
    cmp['delta_substantive'] = cmp['substantive_gen1'] - cmp['substantive_gen0']
    corr = correlate_feedback_attention(fb1_poem, paired)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    summary = {'survey2_meta': meta, 'attention_tests': attn_tests, 'paired_attention': paired[['lineage', 'd_entropy', 'd_rhyme', 'd_phoneme_pairs']].to_dict(orient='records'), 'feedback_comparison_by_lineage': cmp.to_dict(orient='records'), 'feedback_attention_correlation': corr.to_dict(orient='records')}
    (OUT_DIR / 'stage1_summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    cmp.to_csv(OUT_DIR / 'feedback_gen0_vs_gen1.csv', index=False)
    corr.to_csv(OUT_DIR / 'feedback_attention_corr.csv', index=False)
    report = build_report(meta, attn_tests, cmp, corr, paired)
    (OUT_DIR / 'ANALYSIS_REPORT.md').write_text(report, encoding='utf-8')
    (ROOT / 'iteration' / 'survey2' / 'ANALYSIS_REPORT.md').write_text(report, encoding='utf-8')
    subprocess.run([sys.executable, str(ROOT / 'analysis' / 'plot_paper_figures.py')], check=True)
    print(report)
    print(f'\nWrote {OUT_DIR}')
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
