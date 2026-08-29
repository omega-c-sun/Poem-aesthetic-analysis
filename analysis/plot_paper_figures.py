from __future__ import annotations
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
_THIS = Path(__file__).resolve().parent
_STAGE1 = _THIS.parent
_OUT = _STAGE1 / 'figures'
GEN0_CSV = _THIS / 'outputs' / 'gen0' / 'gen0_metrics.csv'
GEN1_CSV = _THIS / 'outputs' / 'gen1' / 'gen1_metrics.csv'
FEEDBACK_CSV = _THIS / 'outputs' / 'integrated' / 'feedback_gen0_vs_gen1.csv'
TOPSIS_CSV = _THIS / 'outputs' / 'integrated' / 'topsis_by_lineage.csv'
LONG_CSV = _STAGE1 / 'iteration' / 'survey2_likert' / 'ratings_long.csv'
WIDE_CSV = _THIS / 'outputs' / 'integrated' / 'ratings_rater_wide.csv'
C_GEN0 = '#0072B2'
C_GEN1 = '#D55E00'
C_ZERO = '#666666'
DIM_COLORS = {'tension': '#0072B2', 'symbol': '#E69F00', 'rhythm': '#009E73'}

def _setup_mpl() -> None:
    plt.rcParams.update({'font.family': 'serif', 'font.serif': ['Times New Roman', 'DejaVu Serif'], 'font.size': 10, 'axes.labelsize': 10, 'axes.titlesize': 11, 'xtick.labelsize': 9, 'ytick.labelsize': 9, 'legend.fontsize': 9, 'axes.spines.top': False, 'axes.spines.right': False, 'figure.dpi': 160, 'savefig.dpi': 220, 'savefig.bbox': 'tight', 'pdf.fonttype': 42})

def load_paired() -> pd.DataFrame:
    g0 = pd.read_csv(GEN0_CSV)
    g1 = pd.read_csv(GEN1_CSV)
    g0['lineage'] = g0['poem_id'].str.replace('^gen0_', '', regex=True)
    g1['lineage'] = g1['poem_id'].str.replace('^gen1_', '', regex=True)
    paired = g0.merge(g1, on=['lineage', 'theme', 'variant'], suffixes=('_g0', '_g1'))
    paired['d_entropy'] = paired['entropy_mean_g1'] - paired['entropy_mean_g0']
    paired['d_rhyme'] = paired['rhyme_share_mean_g1'] - paired['rhyme_share_mean_g0']
    return paired.sort_values('lineage')

def plot_grouped_bars(paired: pd.DataFrame, out_path: Path) -> None:
    labels = paired['lineage'].tolist()
    x = np.arange(len(labels))
    w = 0.36
    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.15))
    axes[0].bar(x - w / 2, paired['entropy_mean_g0'], w, label='gen0', color=C_GEN0)
    axes[0].bar(x + w / 2, paired['entropy_mean_g1'], w, label='gen1', color=C_GEN1)
    axes[0].set_ylabel('Long-range entropy')
    axes[0].set_xticks(x, labels)
    axes[0].set_xlabel('Poem lineage')
    axes[0].set_title('A')
    axes[1].bar(x - w / 2, paired['rhyme_share_mean_g0'], w, label='gen0', color=C_GEN0)
    axes[1].bar(x + w / 2, paired['rhyme_share_mean_g1'], w, label='gen1', color=C_GEN1)
    axes[1].set_ylabel('Rhyme-partner share')
    axes[1].set_xticks(x, labels)
    axes[1].set_xlabel('Poem lineage')
    axes[1].set_title('B')
    handles, labels_ = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels_, frameon=False, loc='center left', bbox_to_anchor=(1.01, 0.52))
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)

def plot_deltas(paired: pd.DataFrame, out_path: Path) -> None:
    labels = paired['lineage'].tolist()
    x = np.arange(len(labels))
    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.15))
    axes[0].axhline(0, color=C_ZERO, linewidth=0.8)
    axes[0].bar(x, paired['d_entropy'], color=[C_GEN1 if v >= 0 else C_GEN0 for v in paired['d_entropy']])
    axes[0].set_ylabel('$\\Delta$ entropy (gen1 $-$ gen0)')
    axes[0].set_xticks(x, labels)
    axes[0].set_xlabel('Poem lineage')
    axes[0].set_title('A')
    axes[1].axhline(0, color=C_ZERO, linewidth=0.8)
    axes[1].bar(x, paired['d_rhyme'], color=[C_GEN1 if v >= 0 else C_GEN0 for v in paired['d_rhyme']])
    axes[1].set_ylabel('$\\Delta$ rhyme-share (gen1 $-$ gen0)')
    axes[1].set_xticks(x, labels)
    axes[1].set_xlabel('Poem lineage')
    axes[1].set_title('B')
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)

def plot_feedback_comparison(out_path: Path) -> None:
    if not FEEDBACK_CSV.exists():
        return
    fb = pd.read_csv(FEEDBACK_CSV).sort_values('lineage')
    labels = fb['lineage'].tolist()
    x = np.arange(len(labels))
    w = 0.36
    fig, ax = plt.subplots(figsize=(7.4, 3.2))
    ax.bar(x - w / 2, fb['substantive_gen0'], w, label='gen0 (Survey 1)', color=C_GEN0)
    ax.bar(x + w / 2, fb['substantive_gen1'], w, label='gen1 (Survey 2a)', color=C_GEN1)
    ax.set_xticks(x, labels)
    ax.set_xlabel('Poem lineage')
    ax.set_ylabel('Substantive feedback items')
    ax.legend(frameon=False, loc='upper right')
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)

def _lineage_sd(long_df: pd.DataFrame) -> pd.DataFrame:
    g = long_df.groupby(['lineage', 'round'], as_index=False).agg(tension_sd=('tension', 'std'), symbol_sd=('symbol', 'std'), rhythm_sd=('rhythm', 'std'))
    return g

def plot_likert_panels(poem: pd.DataFrame, long_df: pd.DataFrame | None, out_path: Path) -> None:
    labels = poem['lineage'].tolist()
    x = np.arange(len(labels))
    w = 0.36
    sd = None
    if long_df is not None and (not long_df.empty):
        sd = _lineage_sd(long_df)
    fig, axes = plt.subplots(1, 3, figsize=(7.6, 2.85), sharey=True)
    for ax, dim, title in zip(axes, ('tension', 'symbol', 'rhythm'), ('A  Tension', 'B  Symbol', 'C  Rhythm')):
        y0, y1 = (poem[f'{dim}_g0'].to_numpy(), poem[f'{dim}_g1'].to_numpy())
        e0 = e1 = None
        if sd is not None:
            s0 = sd[sd['round'] == 'gen0'].set_index('lineage').reindex(labels)
            s1 = sd[sd['round'] == 'gen1'].set_index('lineage').reindex(labels)
            e0 = s0[f'{dim}_sd'].fillna(0).to_numpy()
            e1 = s1[f'{dim}_sd'].fillna(0).to_numpy()
        ax.bar(x - w / 2, y0, w, yerr=e0, capsize=2, label='gen0', color=C_GEN0, error_kw={'linewidth': 0.8})
        ax.bar(x + w / 2, y1, w, yerr=e1, capsize=2, label='gen1', color=C_GEN1, error_kw={'linewidth': 0.8})
        ax.set_xticks(x, labels, rotation=0)
        ax.set_ylim(1, 8.0)
        ax.set_title(title, loc='left', fontsize=10)
        ax.set_xlabel('Lineage')
    axes[0].set_ylabel('Mean Likert (1–7)')
    handles, labels_ = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels_, frameon=False, loc='center left', bbox_to_anchor=(1.01, 0.52))
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)

def plot_dim_means(poem: pd.DataFrame, out_path: Path) -> None:
    dims = ['Tension', 'Symbol', 'Rhythm']
    keys = ['tension', 'symbol', 'rhythm']
    g0 = np.array([poem[f'{k}_g0'].mean() for k in keys])
    g1 = np.array([poem[f'{k}_g1'].mean() for k in keys])
    e0 = np.array([poem[f'{k}_g0'].sem() for k in keys])
    e1 = np.array([poem[f'{k}_g1'].sem() for k in keys])
    x = np.arange(len(dims))
    w = 0.36
    fig, ax = plt.subplots(figsize=(4.8, 3.2))
    ax.bar(x - w / 2, g0, w, yerr=e0, capsize=3, label='gen0', color=C_GEN0, error_kw={'linewidth': 0.9})
    ax.bar(x + w / 2, g1, w, yerr=e1, capsize=3, label='gen1', color=C_GEN1, error_kw={'linewidth': 0.9})
    ax.set_xticks(x, dims)
    ax.set_ylim(1, 8.0)
    ax.set_ylabel('Mean Likert (1–7)')
    ax.legend(frameon=False, loc='center left', bbox_to_anchor=(1.02, 0.5))
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
    axes[1].axhline(0, color=C_ZERO, linewidth=0.8)
    axes[1].bar(x, poem['d_C'], color=C_GEN1)
    axes[1].set_xticks(x, labels)
    axes[1].set_xlabel('Poem lineage')
    axes[1].set_ylabel('$\\Delta C$ (gen1 $-$ gen0)')
    axes[1].set_title('B')
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)

def plot_scatter(poem: pd.DataFrame, out_path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.25))
    pairs = [(axes[0], 'd_entropy', '$\\Delta$ entropy', C_GEN0, 'A'), (axes[1], 'd_rhyme', '$\\Delta$ rhyme-share', C_GEN1, 'B')]
    for ax, col, xlab, color, title in pairs:
        ax.scatter(poem[col], poem['d_C'], color=color, s=55, zorder=3)
        for _, r in poem.iterrows():
            ax.annotate(r['lineage'], (r[col], r['d_C']), fontsize=8, xytext=(4, 4), textcoords='offset points')
        rho, p = stats.spearmanr(poem[col], poem['d_C'])
        ax.axhline(0, color=C_ZERO, lw=0.6)
        ax.axvline(0, color=C_ZERO, lw=0.6)
        ax.set_xlabel(xlab)
        ax.set_ylabel('$\\Delta C$')
        ax.set_title(title)
        ax.text(0.04, 0.96, f'$\\rho={rho:.2f}$, $p={p:.2f}$', transform=ax.transAxes, va='top', ha='left', fontsize=9)
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)

def plot_expertise(wide: pd.DataFrame, out_path: Path) -> None:
    order = ['amateur', 'intermediate', 'expert']
    present = [g for g in order if g in set(wide['expertise'])]
    means = [wide.loc[wide['expertise'] == g, 'd_comp'].mean() for g in present]
    ns = [int((wide['expertise'] == g).sum()) for g in present]
    fig, ax = plt.subplots(figsize=(4.4, 3.15))
    ax.bar(present, means, color=[C_GEN0, C_GEN1, '#009E73'][:len(present)])
    ax.axhline(0, color=C_ZERO, lw=0.7)
    ax.set_ylabel('Mean $\\Delta$ composite (gen1 $-$ gen0)')
    for i, (m, n) in enumerate(zip(means, ns)):
        ax.text(i, m + 0.03 * np.sign(m + 1e-09), f'$n$={n}', ha='center', va='bottom', fontsize=9)
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)

def main() -> int:
    _setup_mpl()
    _OUT.mkdir(parents=True, exist_ok=True)
    paired = load_paired()
    plot_grouped_bars(paired, _OUT / 'attn_entropy_rhyme_share.png')
    plot_deltas(paired, _OUT / 'attn_delta.png')
    plot_feedback_comparison(_OUT / 'feedback_gen0_gen1.png')
    placeholder = _OUT / 'topsis_scores_placeholder.png'
    if placeholder.exists():
        placeholder.unlink()
    if TOPSIS_CSV.exists():
        poem = pd.read_csv(TOPSIS_CSV).sort_values('lineage')
        long_df = pd.read_csv(LONG_CSV) if LONG_CSV.exists() else None
        plot_likert_panels(poem, long_df, _OUT / 'likert_dimensions.png')
        plot_dim_means(poem, _OUT / 'likert_dim_means.png')
        plot_topsis(poem, _OUT / 'topsis_scores.png')
        plot_scatter(poem, _OUT / 'topsis_vs_attention.png')
        if WIDE_CSV.exists():
            plot_expertise(pd.read_csv(WIDE_CSV), _OUT / 'expertise_delta.png')
    print(f'Wrote figures to {_OUT}')
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
