#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
_THIS = Path(__file__).resolve().parent
_STAGE1 = _THIS.parent
_ROOT = _STAGE1.parent
if str(_STAGE1) not in sys.path:
    sys.path.insert(0, str(_STAGE1))
from analysis.attention_metrics import DEFAULT_D, compute_attention_metrics
from analysis.latent_summary import pool_latent_bundle, poem_latent_summary
from analysis.probe_qwen import load_probe_model, run_probe
from analysis.rhyme_index import build_rhyme_index, rhyme_index_to_dict
THEME_BY_CODE = {'t1': 'autumn departure', 't2': 'urban night solitude', 't3': 'memory and water'}

def parse_poem_meta(poem_id: str) -> dict[str, str]:
    parts = poem_id.split('_')
    code = parts[1][:2] if len(parts) > 1 else ''
    variant = parts[1][2:] if len(parts) > 1 and len(parts[1]) > 2 else ''
    return {'poem_id': poem_id, 'theme_code': code, 'theme': THEME_BY_CODE.get(code, 'unknown'), 'variant': variant}

def load_manifest_themes(manifest_path: Path | None) -> dict[str, dict[str, str]]:
    if manifest_path is None or not manifest_path.is_file():
        return {}
    data = json.loads(manifest_path.read_text(encoding='utf-8'))
    out = {}
    for p in data.get('poems', []):
        out[p['id']] = {'theme': p.get('theme', ''), 'variant': p.get('variant', '')}
    return out

def ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p

def save_heatmap(attn: np.ndarray, tokens: list[str], query_indices: list[int], out_path: Path, title: str) -> None:
    n = len(tokens)
    tick_every = max(1, n // 24)
    labels = [tok if i % tick_every == 0 else '' for i, tok in enumerate(tokens)]
    fig, ax = plt.subplots(figsize=(10, 8))
    sns.heatmap(attn, cmap='viridis', xticklabels=labels, yticklabels=labels, ax=ax, cbar=True)
    for qi in query_indices:
        if 0 <= qi < n:
            ax.axhline(qi + 0.5, color='white', linewidth=0.4, alpha=0.5)
            ax.axvline(qi + 0.5, color='white', linewidth=0.4, alpha=0.5)
    ax.set_title(title)
    ax.set_xlabel('key')
    ax.set_ylabel('query')
    fig.tight_layout()
    fig.savefig(out_path, dpi=160, bbox_inches='tight')
    plt.close(fig)

def _short_poem_label(poem_id: str) -> str:
    parts = poem_id.split('_', 1)
    return parts[1] if len(parts) > 1 else poem_id

def plot_metric_bars(df: pd.DataFrame, out_dir: Path, round_label: str) -> None:
    df = df.copy()
    df['label'] = df['poem_id'].map(_short_poem_label)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    sns.barplot(data=df, x='label', y='entropy_mean', hue='theme', ax=axes[0], dodge=False)
    axes[0].set_title(f'{round_label} long-range attention entropy (all layers)')
    axes[0].tick_params(axis='x', rotation=45)
    axes[0].legend(fontsize=7, loc='best')
    sns.barplot(data=df, x='label', y='rhyme_share_mean', hue='theme', ax=axes[1], dodge=False)
    axes[1].set_title(f'{round_label} rhyme-partner attention share (all layers)')
    axes[1].tick_params(axis='x', rotation=45)
    axes[1].legend(fontsize=7, loc='best')
    fig.tight_layout()
    fig.savefig(out_dir / f'{round_label}_entropy_rhyme_share.png', dpi=160, bbox_inches='tight')
    plt.close(fig)

def plot_pca(bundle: dict[str, Any], out_path: Path, round_label: str) -> None:
    coords = np.asarray(bundle['pca_2d'])
    ids = bundle['poem_ids']
    themes = bundle['themes']
    theme_set = sorted(set(themes))
    colors = sns.color_palette('Set2', n_colors=max(len(theme_set), 1))
    theme_color = {t: colors[i] for i, t in enumerate(theme_set)}
    fig, ax = plt.subplots(figsize=(6.5, 5))
    for i, pid in enumerate(ids):
        ax.scatter(coords[i, 0], coords[i, 1], color=theme_color[themes[i]], s=80)
        ax.text(coords[i, 0], coords[i, 1], _short_poem_label(pid), fontsize=8)
    handles = [plt.Line2D([0], [0], marker='o', color='w', markerfacecolor=theme_color[t], label=t, markersize=8) for t in theme_set]
    ax.legend(handles=handles, fontsize=8, title='theme')
    ax.set_xlabel('PC1')
    ax.set_ylabel('PC2')
    ax.set_title(f'{round_label} latent PCA (last-layer line-final mean-pool)')
    fig.tight_layout()
    fig.savefig(out_path, dpi=160, bbox_inches='tight')
    plt.close(fig)

def plot_cosine(bundle: dict[str, Any], out_path: Path, round_label: str) -> None:
    labels = [_short_poem_label(p) for p in bundle['poem_ids']]
    fig, ax = plt.subplots(figsize=(6, 5))
    sns.heatmap(np.asarray(bundle['cosine']), xticklabels=labels, yticklabels=labels, cmap='coolwarm', vmin=-1, vmax=1, ax=ax, annot=True, fmt='.2f')
    ax.set_title(f'{round_label} pooled latent cosine')
    fig.tight_layout()
    fig.savefig(out_path, dpi=160, bbox_inches='tight')
    plt.close(fig)

def select_viz_layers(n_layers: int) -> list[tuple[str, int]]:
    return [('early', 0), ('mid', n_layers // 2), ('late', n_layers - 1)]

def infer_round_label(poems_dir: Path, poem_paths: list[Path]) -> str:
    name = poems_dir.name
    if name.startswith('gen'):
        return name
    if poem_paths:
        stem = poem_paths[0].stem
        if '_' in stem:
            return stem.split('_', 1)[0]
    return 'gen'

def main() -> int:
    parser = argparse.ArgumentParser(description='Attention / latent snapshot for a generation round')
    parser.add_argument('--poems-dir', type=Path, default=_STAGE1 / 'poems' / 'gen0', help='Directory of poem .txt files (e.g. poems/gen0 or poems/gen1)')
    parser.add_argument('--out', type=Path, default=None, help='Output directory (default: analysis/outputs/<round>)')
    parser.add_argument('--glob', type=str, default=None, help='Poem filename glob (default: <round>_*.txt or *.txt)')
    parser.add_argument('--model', type=str, default=None, help='Override HF model id')
    parser.add_argument('--d', type=int, default=DEFAULT_D, help='Long-range distance threshold')
    parser.add_argument('--manifest', type=Path, default=None, help='Optional poem manifest JSON for theme labels')
    parser.add_argument('--max-poems', type=int, default=None, help='Limit poems (debug)')
    args = parser.parse_args()
    poems_dir: Path = args.poems_dir
    round_guess = poems_dir.name if poems_dir.name.startswith('gen') else 'gen'
    pattern = args.glob or (f'{round_guess}_*.txt' if round_guess.startswith('gen') else '*.txt')
    poem_paths = sorted(poems_dir.glob(pattern))
    if not poem_paths and args.glob is None:
        poem_paths = sorted(poems_dir.glob('*.txt'))
    if args.max_poems is not None:
        poem_paths = poem_paths[:args.max_poems]
    if not poem_paths:
        print(f'No poems found in {poems_dir} (pattern={pattern})', file=sys.stderr)
        return 1
    round_label = infer_round_label(poems_dir, poem_paths)
    out_dir = ensure_dir(args.out or _THIS / 'outputs' / round_label)
    per_poem_dir = ensure_dir(out_dir / 'per_poem')
    fig_dir = ensure_dir(out_dir / 'figures')
    manifest_path = args.manifest
    if manifest_path is None:
        candidate = _STAGE1 / 'poems' / f'{round_label}_manifest.json'
        manifest_path = candidate if candidate.is_file() else None
    manifest_meta = load_manifest_themes(manifest_path)
    probe = load_probe_model(args.model)
    rows: list[dict[str, Any]] = []
    pooled_ids: list[str] = []
    pooled_themes: list[str] = []
    pooled_vecs: list[np.ndarray] = []
    poem_records: list[dict[str, Any]] = []
    for path in poem_paths:
        poem_id = path.stem
        text = path.read_text(encoding='utf-8')
        meta = parse_poem_meta(poem_id)
        if poem_id in manifest_meta:
            meta['theme'] = manifest_meta[poem_id].get('theme') or meta['theme']
            meta['variant'] = manifest_meta[poem_id].get('variant') or meta['variant']
        print(f'[run] Probing {poem_id}...')
        out = run_probe(probe, poem_id, text)
        rhyme = build_rhyme_index(out.text, probe.tokenizer, out.input_ids.tolist())
        metrics = compute_attention_metrics(out.attentions, rhyme, d=args.d)
        latent = poem_latent_summary(out.hidden_states, rhyme.query_token_indices)
        metrics_json = {k: v for k, v in metrics.items() if k not in ('attn_mean_all', 'attn_mean_late')}
        latent_json = {k: v for k, v in latent.items() if k != 'pooled_last_line_final'}
        poem_out = ensure_dir(per_poem_dir / poem_id)
        (poem_out / 'tokens.json').write_text(json.dumps({'tokens': out.tokens, 'input_ids': out.input_ids.tolist(), 'n_tokens': len(out.tokens)}, ensure_ascii=False, indent=2), encoding='utf-8')
        (poem_out / 'rhyme_index.json').write_text(json.dumps(rhyme_index_to_dict(rhyme), ensure_ascii=False, indent=2), encoding='utf-8')
        (poem_out / 'metrics.json').write_text(json.dumps(metrics_json, ensure_ascii=False, indent=2), encoding='utf-8')
        (poem_out / 'latent.json').write_text(json.dumps(latent_json, ensure_ascii=False, indent=2), encoding='utf-8')
        for tag, li in select_viz_layers(out.n_layers):
            attn = out.attentions[li].mean(dim=0).numpy()
            np.savez_compressed(poem_out / f'attn_headmean_{tag}_L{li}.npz', attn=attn.astype(np.float32))
            save_heatmap(attn, out.tokens, rhyme.query_token_indices, fig_dir / f'{poem_id}_attn_{tag}_L{li}.png', title=f'{poem_id} head-mean attention ({tag} L{li})')
        row = {'poem_id': poem_id, 'theme': meta['theme'], 'variant': meta['variant'], 'n_tokens': len(out.tokens), 'n_lines': len(rhyme.lines), 'entropy_mean': metrics['entropy_mean'], 'entropy_median': metrics['entropy_median'], 'rhyme_share_mean': metrics['rhyme_share_mean'], 'rhyme_share_median': metrics['rhyme_share_median'], 'late_entropy_mean': metrics['late_entropy_mean'], 'late_rhyme_share_mean': metrics['late_rhyme_share_mean'], 'rhyme_coverage': rhyme.rhyme_coverage, 'phoneme_agree_pairs': rhyme.phoneme_agree_pairs, 'phoneme_pair_total': rhyme.phoneme_pair_total, 'embed_line_final_var_mean': latent.get('embed_line_final_var_mean'), 'mid_line_final_var_mean': latent.get('mid_line_final_var_mean'), 'last_line_final_var_mean': latent.get('last_line_final_var_mean'), 'last_line_final_mean_norm': latent.get('last_line_final_mean_norm')}
        rows.append(row)
        poem_records.append({'poem_id': poem_id, 'path': str(path), 'n_tokens': len(out.tokens), 'theme': meta['theme'], 'variant': meta['variant']})
        pooled = latent.get('pooled_last_line_final')
        if pooled is not None:
            pooled_ids.append(poem_id)
            pooled_themes.append(meta['theme'])
            pooled_vecs.append(np.asarray(pooled))
        del out, metrics
    df = pd.DataFrame(rows)
    csv_path = out_dir / f'{round_label}_metrics.csv'
    df.to_csv(csv_path, index=False)
    print(f'[run] Wrote {csv_path}')
    plot_metric_bars(df, fig_dir, round_label)
    if pooled_vecs:
        bundle = pool_latent_bundle(pooled_ids, pooled_themes, pooled_vecs)
        np.savez_compressed(out_dir / 'latent_summary.npz', poem_ids=np.array(bundle['poem_ids']), themes=np.array(bundle['themes']), pooled=bundle['pooled'], cosine=bundle['cosine'], pca_2d=bundle['pca_2d'])
        plot_pca(bundle, fig_dir / f'{round_label}_latent_pca.png', round_label)
        plot_cosine(bundle, fig_dir / f'{round_label}_latent_cosine.png', round_label)
    manifest = {'created_utc': datetime.now(timezone.utc).isoformat(), 'round': round_label, 'model_name': probe.model_name, 'device': probe.device, 'd': args.d, 'n_layers': probe.n_layers, 'n_heads': probe.n_heads, 'aggregation': {'primary': 'mean over all layers and heads', 'late': 'mean over last 4 layers and all heads', 'queries': 'line-final tokens (14)', 'rhyme_keys': 'Shakespearean partner line-end token spans'}, 'poems_dir': str(poems_dir), 'poems': poem_records, 'outputs': {'metrics_csv': str(csv_path), 'figures_dir': str(fig_dir), 'per_poem_dir': str(per_poem_dir)}}
    (out_dir / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'[run] Done. Artifacts under {out_dir}')
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
