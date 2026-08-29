from __future__ import annotations
from typing import Any
import numpy as np
from .rhyme_index import RhymeIndex
DEFAULT_D = 8
EPS = 1e-12

def _layer_head_mean(attentions: tuple[Any, ...], layer_indices: list[int] | None=None) -> np.ndarray:
    mats = []
    for li, attn in enumerate(attentions):
        if layer_indices is not None and li not in layer_indices:
            continue
        a = attn.numpy() if hasattr(attn, 'numpy') else np.asarray(attn)
        mats.append(a.mean(axis=0))
    if not mats:
        raise ValueError('No attention layers selected')
    return np.mean(np.stack(mats, axis=0), axis=0)

def long_range_distribution(attn_row: np.ndarray, query_i: int, d: int=DEFAULT_D) -> np.ndarray | None:
    T = attn_row.shape[0]
    weights = np.zeros(T, dtype=np.float64)
    for j in range(0, query_i):
        if query_i - j >= d:
            weights[j] = float(attn_row[j])
    total = weights.sum()
    if total <= EPS:
        return None
    return weights / total

def entropy(p: np.ndarray) -> float:
    p = p[p > EPS]
    return float(-(p * np.log(p)).sum())

def rhyme_share(p: np.ndarray, rhyme_spans: list[tuple[int, int]], query_i: int) -> float:
    mass = 0.0
    for start, end in rhyme_spans:
        for j in range(start, end):
            if j == query_i:
                continue
            if 0 <= j < p.shape[0]:
                mass += float(p[j])
    return float(mass)

def per_query_metrics(attn_mean: np.ndarray, rhyme_index: RhymeIndex, d: int=DEFAULT_D) -> dict[str, Any]:
    entropies: list[float] = []
    shares: list[float] = []
    details: list[dict[str, Any]] = []
    for line_i, query_i in enumerate(rhyme_index.query_token_indices):
        if query_i < 0 or query_i >= attn_mean.shape[0]:
            continue
        p = long_range_distribution(attn_mean[query_i], query_i, d=d)
        if p is None:
            details.append({'line_index': line_i, 'query_token': query_i, 'entropy': None, 'rhyme_share': None, 'skipped': True})
            continue
        h = entropy(p)
        spans = rhyme_index.partner_token_spans(line_i)
        share = rhyme_share(p, spans, query_i)
        entropies.append(h)
        shares.append(share)
        details.append({'line_index': line_i, 'query_token': query_i, 'entropy': h, 'rhyme_share': share, 'partner_spans': spans, 'skipped': False})

    def _safe_mean(xs: list[float]) -> float | None:
        return float(np.mean(xs)) if xs else None

    def _safe_median(xs: list[float]) -> float | None:
        return float(np.median(xs)) if xs else None
    return {'entropy_mean': _safe_mean(entropies), 'entropy_median': _safe_median(entropies), 'rhyme_share_mean': _safe_mean(shares), 'rhyme_share_median': _safe_median(shares), 'n_queries_used': len(entropies), 'per_query': details}

def compute_attention_metrics(attentions: tuple[Any, ...], rhyme_index: RhymeIndex, d: int=DEFAULT_D) -> dict[str, Any]:
    n_layers = len(attentions)
    all_layers = list(range(n_layers))
    late_layers = list(range(max(0, n_layers - 4), n_layers))
    attn_all = _layer_head_mean(attentions, all_layers)
    attn_late = _layer_head_mean(attentions, late_layers)
    all_m = per_query_metrics(attn_all, rhyme_index, d=d)
    late_m = per_query_metrics(attn_late, rhyme_index, d=d)
    return {'d': d, 'n_layers': n_layers, 'late_layer_indices': late_layers, 'all_layers': {'entropy_mean': all_m['entropy_mean'], 'entropy_median': all_m['entropy_median'], 'rhyme_share_mean': all_m['rhyme_share_mean'], 'rhyme_share_median': all_m['rhyme_share_median'], 'n_queries_used': all_m['n_queries_used'], 'per_query': all_m['per_query']}, 'late_layers': {'entropy_mean': late_m['entropy_mean'], 'entropy_median': late_m['entropy_median'], 'rhyme_share_mean': late_m['rhyme_share_mean'], 'rhyme_share_median': late_m['rhyme_share_median'], 'n_queries_used': late_m['n_queries_used']}, 'entropy_mean': all_m['entropy_mean'], 'entropy_median': all_m['entropy_median'], 'rhyme_share_mean': all_m['rhyme_share_mean'], 'rhyme_share_median': all_m['rhyme_share_median'], 'late_entropy_mean': late_m['entropy_mean'], 'late_rhyme_share_mean': late_m['rhyme_share_mean'], 'attn_mean_all': attn_all, 'attn_mean_late': attn_late}
