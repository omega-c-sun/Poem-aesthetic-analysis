#!/usr/bin/env python3
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
ROOT = Path(__file__).resolve().parent
LIKERT_DIR = ROOT / 'iteration' / 'survey2_likert'
OUT_DIR = ROOT / 'analysis' / 'outputs' / 'integrated'
FIG_DIR = ROOT / 'figures'
GEN0_CSV = ROOT / 'analysis' / 'outputs' / 'gen0' / 'gen0_metrics.csv'
GEN1_CSV = ROOT / 'analysis' / 'outputs' / 'gen1' / 'gen1_metrics.csv'
C_GEN0 = '#0072B2'
C_GEN1 = '#D55E00'
DIMS = ('tension', 'symbol', 'rhythm')

def topsis_closeness(X: np.ndarray, weights: np.ndarray | None=None) -> np.ndarray:
    X = np.asarray(X, dtype=float)
    n, m = X.shape
    w = np.full(m, 1.0 / m) if weights is None else np.asarray(weights, dtype=float)
    denom = np.sqrt((X ** 2).sum(axis=0))
    denom = np.where(denom == 0, 1.0, denom)
    R = X / denom
    V = R * w
    ideal = V.max(axis=0)
    anti = V.min(axis=0)
    d_pos = np.sqrt(((V - ideal) ** 2).sum(axis=1))
    d_neg = np.sqrt(((V - anti) ** 2).sum(axis=1))
    return d_neg / (d_pos + d_neg)

def bootstrap_ci(x: np.ndarray, n_boot: int=5000, alpha: float=0.05) -> tuple[float, float]:
    rng = np.random.default_rng(42)
    x = np.asarray(x, dtype=float)
    means = [rng.choice(x, size=len(x), replace=True).mean() for _ in range(n_boot)]
    lo = float(np.percentile(means, 100 * alpha / 2))
    hi = float(np.percentile(means, 100 * (1 - alpha / 2)))
    return (lo, hi)

def wilcoxon_report(x: np.ndarray) -> dict:
    x = np.asarray(x, dtype=float)
    try:
        stat, p = stats.wilcoxon(x, zero_method='wilcox', alternative='two-sided')
    except ValueError:
        stat, p = (np.nan, np.nan)
    return {'n': int(len(x)), 'mean': float(np.mean(x)), 'median': float(np.median(x)), 'wilcoxon_stat': None if stat != stat else float(stat), 'p_value': None if p != p else float(p), 'ci95': [round(v, 4) for v in bootstrap_ci(x)]}

def setup_mpl() -> None:
    plt.rcParams.update({'font.family': 'serif', 'font.serif': ['Times New Roman', 'DejaVu Serif'], 'font.size': 10, 'axes.labelsize': 10, 'axes.titlesize': 11, 'axes.spines.top': False, 'axes.spines.right': False, 'figure.dpi': 160, 'savefig.dpi': 220, 'savefig.bbox': 'tight', 'pdf.fonttype': 42})

def plot_dimension_bars(poem: pd.DataFrame, out_path: Path) -> None:
    labels = poem['lineage'].tolist()
    x = np.arange(len(labels))
    w = 0.18
    fig, ax = plt.subplots(figsize=(7.4, 3.35))
    pal = ['#0072B2', '#E69F00', '#009E73', '#CC79A7']
    series = [('tension_g0', 'Tension gen0'), ('tension_g1', 'Tension gen1'), ('symbol_g0', 'Symbol gen0'), ('symbol_g1', 'Symbol gen1'), ('rhythm_g0', 'Rhythm gen0'), ('rhythm_g1', 'Rhythm gen1')]
    dims = [('tension', pal[0]), ('symbol', pal[1]), ('rhythm', pal[2])]
    for i, (dim, color) in enumerate(dims):
        ax.bar(x + (i - 1) * w - w / 4, poem[f'{dim}_g0'], w / 2, color=color, alpha=0.45, label=f'{dim.title()} gen0')
        ax.bar(x + (i - 1) * w + w / 4, poem[f'{dim}_g1'], w / 2, color=color, alpha=1.0, label=f'{dim.title()} gen1')
    ax.set_xticks(x, labels)
    ax.set_xlabel('Poem lineage')
    ax.set_ylabel('Mean Likert (1–7)')
    ax.set_ylim(1, 7)
    ax.legend(frameon=False, ncol=3, fontsize=7, loc='upper center', bbox_to_anchor=(0.5, 1.22))
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)

def plot_topsis(poem: pd.DataFrame, out_path: Path) -> None:
    labels = poem['lineage'].tolist()
    x = np.arange(len(labels))
    w = 0.36
    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.15))
    axes[0].bar(x - w / 2, poem['C_g0'], w, label='gen0', color=C_GEN0)
    axes[0].bar(x + w / 2, poem['C_g1'], w, label='gen1', color=C_GEN1)
    axes[0].set_xticks(x, labels)
    axes[0].set_xlabel('Poem lineage')
    axes[0].set_ylabel('TOPSIS $C$')
    axes[0].set_ylim(0, 1)
    axes[0].legend(frameon=False)
    axes[0].set_title('A')
    colors = [C_GEN1 if v >= 0 else C_GEN0 for v in poem['d_C']]
    axes[1].axhline(0, color='#666666', linewidth=0.8)
    axes[1].bar(x, poem['d_C'], color=colors)
    axes[1].set_xticks(x, labels)
    axes[1].set_xlabel('Poem lineage')
    axes[1].set_ylabel('$\\Delta C$ (gen1 $-$ gen0)')
    axes[1].set_title('B')
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)

def plot_scatter(poem: pd.DataFrame, out_path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.15))
    axes[0].scatter(poem['d_entropy'], poem['d_C'], color=C_GEN0, s=50)
    for _, r in poem.iterrows():
        axes[0].annotate(r['lineage'], (r['d_entropy'], r['d_C']), fontsize=8, xytext=(4, 4), textcoords='offset points')
    axes[0].axhline(0, color='#666', lw=0.6)
    axes[0].axvline(0, color='#666', lw=0.6)
    axes[0].set_xlabel('$\\Delta$ entropy')
    axes[0].set_ylabel('$\\Delta C$')
    axes[0].set_title('A')
    axes[1].scatter(poem['d_rhyme'], poem['d_C'], color=C_GEN1, s=50)
    for _, r in poem.iterrows():
        axes[1].annotate(r['lineage'], (r['d_rhyme'], r['d_C']), fontsize=8, xytext=(4, 4), textcoords='offset points')
    axes[1].axhline(0, color='#666', lw=0.6)
    axes[1].axvline(0, color='#666', lw=0.6)
    axes[1].set_xlabel('$\\Delta$ rhyme-share')
    axes[1].set_ylabel('$\\Delta C$')
    axes[1].set_title('B')
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)

def main() -> int:
    subprocess.run([sys.executable, str(ROOT / 'parse_survey2_likert.py')], check=True)
    setup_mpl()
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    long_df = pd.read_csv(LIKERT_DIR / 'ratings_long.csv')
    meta = json.loads((LIKERT_DIR / 'parse_meta.json').read_text(encoding='utf-8'))
    agg = long_df.groupby(['lineage', 'round', 'theme'], as_index=False).agg(n=('respondent', 'nunique'), tension=('tension', 'mean'), symbol=('symbol', 'mean'), rhythm=('rhythm', 'mean'), tension_sd=('tension', 'std'), symbol_sd=('symbol', 'std'), rhythm_sd=('rhythm', 'std')).sort_values(['lineage', 'round'])
    order = agg.copy()
    C = topsis_closeness(order[list(DIMS)].to_numpy())
    order['C'] = C
    g0 = order[order['round'] == 'gen0'].set_index('lineage')
    g1 = order[order['round'] == 'gen1'].set_index('lineage')
    poem = pd.DataFrame({'lineage': sorted(g0.index)})
    poem['theme'] = poem['lineage'].map(g0['theme'])
    poem['n'] = poem['lineage'].map(g0['n']).astype(int)
    for dim in DIMS:
        poem[f'{dim}_g0'] = poem['lineage'].map(g0[dim])
        poem[f'{dim}_g1'] = poem['lineage'].map(g1[dim])
        poem[f'd_{dim}'] = poem[f'{dim}_g1'] - poem[f'{dim}_g0']
    poem['C_g0'] = poem['lineage'].map(g0['C'])
    poem['C_g1'] = poem['lineage'].map(g1['C'])
    poem['d_C'] = poem['C_g1'] - poem['C_g0']
    attn0 = pd.read_csv(GEN0_CSV)
    attn1 = pd.read_csv(GEN1_CSV)
    attn0['lineage'] = attn0['poem_id'].str.replace('^gen0_', '', regex=True)
    attn1['lineage'] = attn1['poem_id'].str.replace('^gen1_', '', regex=True)
    poem = poem.merge(attn0[['lineage', 'entropy_mean', 'rhyme_share_mean']].rename(columns={'entropy_mean': 'entropy_g0', 'rhyme_share_mean': 'rhyme_g0'}), on='lineage').merge(attn1[['lineage', 'entropy_mean', 'rhyme_share_mean']].rename(columns={'entropy_mean': 'entropy_g1', 'rhyme_share_mean': 'rhyme_g1'}), on='lineage')
    poem['d_entropy'] = poem['entropy_g1'] - poem['entropy_g0']
    poem['d_rhyme'] = poem['rhyme_g1'] - poem['rhyme_g0']
    wide = long_df.pivot_table(index=['respondent', 'lineage', 'expertise'], columns='round', values=list(DIMS), aggfunc='first')
    wide.columns = [f'{a}_{b}' for a, b in wide.columns]
    wide = wide.reset_index()
    wide['comp_g0'] = wide[['tension_gen0', 'symbol_gen0', 'rhythm_gen0']].mean(axis=1)
    wide['comp_g1'] = wide[['tension_gen1', 'symbol_gen1', 'rhythm_gen1']].mean(axis=1)
    wide['d_comp'] = wide['comp_g1'] - wide['comp_g0']
    tests = {'poem_d_C': wilcoxon_report(poem['d_C'].to_numpy()), 'poem_d_tension': wilcoxon_report(poem['d_tension'].to_numpy()), 'poem_d_symbol': wilcoxon_report(poem['d_symbol'].to_numpy()), 'poem_d_rhythm': wilcoxon_report(poem['d_rhythm'].to_numpy()), 'rater_d_composite': wilcoxon_report(wide['d_comp'].to_numpy())}
    corr_rows = []
    for att, lab in (('d_entropy', 'd_entropy'), ('d_rhyme', 'd_rhyme')):
        r, p = stats.spearmanr(poem[att], poem['d_C'])
        corr_rows.append({'x': lab, 'y': 'd_C', 'spearman_r': float(r), 'p_value': float(p), 'n': int(len(poem))})
        r2, p2 = stats.spearmanr(poem[att.replace('d_', '') + '_g1'] if False else poem[att], poem['C_g1'])
        r2, p2 = stats.spearmanr(poem['entropy_g1' if att == 'd_entropy' else 'rhyme_g1'], poem['C_g1'])
        corr_rows.append({'x': 'entropy_g1' if att == 'd_entropy' else 'rhyme_g1', 'y': 'C_g1', 'spearman_r': float(r2), 'p_value': float(p2), 'n': int(len(poem))})
    exp_tests = {}
    for grp, sub in wide.groupby('expertise'):
        exp_tests[str(grp)] = {'n': int(len(sub)), 'mean_d_comp': float(sub['d_comp'].mean())}
    poem.to_csv(OUT_DIR / 'topsis_by_lineage.csv', index=False)
    order.to_csv(OUT_DIR / 'topsis_units.csv', index=False)
    wide.to_csv(OUT_DIR / 'ratings_rater_wide.csv', index=False)
    summary = {'survey2_likert_meta': meta, 'means': {'tension_g0': float(poem['tension_g0'].mean()), 'tension_g1': float(poem['tension_g1'].mean()), 'symbol_g0': float(poem['symbol_g0'].mean()), 'symbol_g1': float(poem['symbol_g1'].mean()), 'rhythm_g0': float(poem['rhythm_g0'].mean()), 'rhythm_g1': float(poem['rhythm_g1'].mean()), 'C_g0': float(poem['C_g0'].mean()), 'C_g1': float(poem['C_g1'].mean()), 'd_C': float(poem['d_C'].mean()), 'n_lineages_C_up': int((poem['d_C'] > 0).sum())}, 'tests': tests, 'spearman': corr_rows, 'expertise_d_comp': exp_tests, 'lineages': poem.to_dict(orient='records')}
    (OUT_DIR / 'likert_topsis_summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=float), encoding='utf-8')
    (LIKERT_DIR / 'SUMMARY.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=float), encoding='utf-8')
    subprocess.run([sys.executable, str(ROOT / 'analysis' / 'plot_paper_figures.py')], check=True)
    print(poem.round(4).to_string(index=False))
    print(json.dumps({'tests': tests, 'means': summary['means'], 'spearman': corr_rows, 'expertise': exp_tests}, indent=2, default=float))
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
