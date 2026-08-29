from __future__ import annotations
from typing import Any
import numpy as np

def _as_np(x: Any) -> np.ndarray:
    if hasattr(x, 'numpy'):
        return x.numpy()
    return np.asarray(x)

def layer_indices_for_poem(n_hidden_states: int) -> dict[str, int]:
    last = n_hidden_states - 1
    mid = max(1, n_hidden_states // 2)
    return {'embed': 0, 'mid': mid, 'last': last}

def line_final_vectors(hidden_layer: np.ndarray, query_token_indices: list[int]) -> np.ndarray:
    vecs = []
    T = hidden_layer.shape[0]
    for qi in query_token_indices:
        if 0 <= qi < T:
            vecs.append(hidden_layer[qi])
    if not vecs:
        return np.zeros((0, hidden_layer.shape[-1]), dtype=np.float64)
    return np.stack(vecs, axis=0).astype(np.float64)

def summarize_line_finals(vecs: np.ndarray) -> dict[str, float]:
    if vecs.size == 0:
        return {'line_final_var_mean': float('nan'), 'line_final_mean_norm': float('nan'), 'n_line_finals': 0}
    var_mean = float(vecs.var(axis=0).mean())
    mean_norm = float(np.linalg.norm(vecs.mean(axis=0)))
    return {'line_final_var_mean': var_mean, 'line_final_mean_norm': mean_norm, 'n_line_finals': int(vecs.shape[0])}

def poem_latent_summary(hidden_states: tuple[Any, ...], query_token_indices: list[int]) -> dict[str, Any]:
    hs = [_as_np(h) for h in hidden_states]
    idxs = layer_indices_for_poem(len(hs))
    out: dict[str, Any] = {'layer_indices': idxs}
    pooled = None
    for name, li in idxs.items():
        vecs = line_final_vectors(hs[li], query_token_indices)
        stats = summarize_line_finals(vecs)
        out[f'{name}_line_final_var_mean'] = stats['line_final_var_mean']
        out[f'{name}_line_final_mean_norm'] = stats['line_final_mean_norm']
        if name == 'last':
            pooled = vecs.mean(axis=0) if vecs.size else np.zeros(hs[li].shape[-1])
            out['pooled_last_line_final'] = pooled.astype(np.float32)
    out['n_line_finals'] = len(query_token_indices)
    return out

def cosine_matrix(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms = np.maximum(norms, 1e-12)
    x = vectors / norms
    return x @ x.T

def pca_2d(vectors: np.ndarray) -> np.ndarray:
    if vectors.shape[0] == 0:
        return np.zeros((0, 2), dtype=np.float64)
    x = vectors.astype(np.float64)
    x = x - x.mean(axis=0, keepdims=True)
    try:
        _, _, vt = np.linalg.svd(x, full_matrices=False)
        comps = vt[:2].T
        proj = x @ comps
    except np.linalg.LinAlgError:
        proj = np.zeros((x.shape[0], 2), dtype=np.float64)
    if proj.shape[1] == 1:
        proj = np.concatenate([proj, np.zeros((proj.shape[0], 1))], axis=1)
    return proj[:, :2]

def pool_latent_bundle(poem_ids: list[str], themes: list[str], pooled_vectors: list[np.ndarray]) -> dict[str, Any]:
    mat = np.stack(pooled_vectors, axis=0)
    return {'poem_ids': poem_ids, 'themes': themes, 'pooled': mat.astype(np.float32), 'cosine': cosine_matrix(mat).astype(np.float32), 'pca_2d': pca_2d(mat).astype(np.float32)}
