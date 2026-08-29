from __future__ import annotations
import numpy as np
import pandas as pd

def topsis_closeness(matrix: np.ndarray, weights: np.ndarray | None=None) -> np.ndarray:
    x = np.asarray(matrix, dtype=float)
    if x.ndim != 2 or x.shape[1] < 1:
        raise ValueError('matrix must be 2-D with >=1 criterion')
    n, m = x.shape
    if weights is None:
        w = np.ones(m) / m
    else:
        w = np.asarray(weights, dtype=float)
        w = w / w.sum()
    denom = np.sqrt((x ** 2).sum(axis=0))
    denom = np.where(denom == 0, 1.0, denom)
    r = x / denom
    v = r * w
    ideal = v.max(axis=0)
    anti = v.min(axis=0)
    d_pos = np.sqrt(((v - ideal) ** 2).sum(axis=1))
    d_neg = np.sqrt(((v - anti) ** 2).sum(axis=1))
    return d_neg / (d_pos + d_neg + 1e-12)

def poem_topsis_table(ratings: pd.DataFrame, *, id_col: str='poem_id', dim_cols: tuple[str, ...]=('tension', 'symbol', 'rhythm')) -> pd.DataFrame:
    agg = ratings.groupby(id_col, as_index=False)[list(dim_cols)].mean()
    c = topsis_closeness(agg[list(dim_cols)].to_numpy())
    agg['topsis_c'] = np.round(c, 4)
    return agg
