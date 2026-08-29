from __future__ import annotations
import re
import string
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any
SHAKESPEAREAN_PAIRS: tuple[tuple[int, int], ...] = ((0, 2), (1, 3), (4, 6), (5, 7), (8, 10), (9, 11), (12, 13))
_WORD_RE = re.compile("[A-Za-z]+(?:'[A-Za-z]+)?")

@dataclass
class LineEndInfo:
    line_index: int
    line_text: str
    end_word: str
    word_char_start: int
    word_char_end: int
    token_start: int | None
    token_end: int | None
    phones: list[str] | None
    oov: bool

@dataclass
class RhymeIndex:
    lines: list[str]
    line_ends: list[LineEndInfo]
    partner_of: dict[int, int]
    rhyme_coverage: float
    phoneme_agree_pairs: int
    phoneme_pair_total: int
    query_token_indices: list[int] = field(default_factory=list)

    def partner_token_spans(self, line_index: int) -> list[tuple[int, int]]:
        partner = self.partner_of.get(line_index)
        if partner is None:
            return []
        info = self.line_ends[partner]
        if info.token_start is None or info.token_end is None:
            return []
        return [(info.token_start, info.token_end)]

@lru_cache(maxsize=1)
def _cmu_dict() -> dict[str, list[list[str]]]:
    import cmudict
    return cmudict.dict()

def normalize_word(word: str) -> str:
    w = word.strip().lower()
    w = w.translate(str.maketrans('', '', string.punctuation.replace("'", '')))
    w = w.strip("'")
    w = w.replace('’', "'").replace('‘', "'")
    return w

def lookup_phones(word: str) -> list[str] | None:
    key = normalize_word(word)
    if not key:
        return None
    entries = _cmu_dict().get(key)
    if not entries:
        return None
    return list(entries[0])

def rhyme_tail(phones: list[str] | None) -> tuple[str, ...] | None:
    if not phones:
        return None
    last_vowel = -1
    last_stress = -1
    for i, p in enumerate(phones):
        if p[-1:].isdigit():
            last_vowel = i
            if p[-1] in '12':
                last_stress = i
    start = last_stress if last_stress >= 0 else last_vowel
    if start < 0:
        return None
    return tuple(phones[start:])

def phones_rhyme(a: list[str] | None, b: list[str] | None) -> bool:
    ta, tb = (rhyme_tail(a), rhyme_tail(b))
    return ta is not None and ta == tb

def _line_end_word(line: str) -> tuple[str, int, int]:
    matches = list(_WORD_RE.finditer(line))
    if not matches:
        cleaned = line.strip()
        return (cleaned, 0, len(line))
    m = matches[-1]
    return (m.group(0), m.start(), m.end())

def _build_char_token_map(tokenizer: Any, text: str, input_ids: list[int]) -> list[tuple[int, int] | None]:
    try:
        enc = tokenizer(text, return_offsets_mapping=True, add_special_tokens=True, return_tensors=None)
        offsets = enc.get('offset_mapping')
        if offsets is not None:
            return [tuple(o) if o != (0, 0) or i == 0 else (0, 0) for i, o in enumerate(offsets)]
    except Exception:
        pass
    mapping: list[tuple[int, int] | None] = []
    cursor = 0
    built = ''
    for tid in input_ids:
        piece = tokenizer.decode([tid], skip_special_tokens=False)
        if piece in ('', tokenizer.pad_token, getattr(tokenizer, 'bos_token', None), getattr(tokenizer, 'eos_token', None)):
            if not built and piece:
                mapping.append(None)
                continue
            mapping.append(None)
            continue
        search = piece.replace('▁', ' ').replace('Ġ', ' ').replace('Ċ', '\n')
        idx = text.find(search, cursor)
        if idx < 0:
            search2 = search.lstrip()
            idx = text.find(search2, cursor) if search2 else -1
            if idx < 0:
                mapping.append(None)
                continue
            search = search2
        mapping.append((idx, idx + len(search)))
        cursor = idx + len(search)
        built += search
    return mapping

def _token_span_for_chars(char_token_map: list[tuple[int, int] | None], abs_start: int, abs_end: int) -> tuple[int, int] | None:
    hits = [i for i, off in enumerate(char_token_map) if off is not None and (not (off[1] <= abs_start or off[0] >= abs_end))]
    if not hits:
        return None
    return (hits[0], hits[-1] + 1)

def build_rhyme_index(text: str, tokenizer: Any, input_ids: list[int]) -> RhymeIndex:
    text = text.replace('\r\n', '\n')
    if not text.endswith('\n'):
        text = text + '\n'
    raw_lines = text.rstrip('\n').split('\n')
    lines = [ln for ln in raw_lines if ln.strip() != '']
    if len(lines) > 14:
        lines = lines[:14]
    line_abs: list[tuple[str, int]] = []
    search_from = 0
    for ln in lines:
        idx = text.find(ln, search_from)
        if idx < 0:
            idx = search_from
        line_abs.append((ln, idx))
        search_from = idx + len(ln)
    char_token_map = _build_char_token_map(tokenizer, text, input_ids)
    line_ends: list[LineEndInfo] = []
    for i, (ln, abs_line_start) in enumerate(line_abs):
        word, rel_s, rel_e = _line_end_word(ln)
        abs_s, abs_e = (abs_line_start + rel_s, abs_line_start + rel_e)
        span = _token_span_for_chars(char_token_map, abs_s, abs_e)
        phones = lookup_phones(word)
        line_ends.append(LineEndInfo(line_index=i, line_text=ln, end_word=word, word_char_start=abs_s, word_char_end=abs_e, token_start=None if span is None else span[0], token_end=None if span is None else span[1], phones=phones, oov=phones is None))
    partner_of: dict[int, int] = {}
    for a, b in SHAKESPEAREAN_PAIRS:
        if a < len(line_ends) and b < len(line_ends):
            partner_of[a] = b
            partner_of[b] = a
    n_cmu = sum((1 for le in line_ends if not le.oov))
    coverage = n_cmu / max(len(line_ends), 1)
    agree = 0
    pair_total = 0
    for a, b in SHAKESPEAREAN_PAIRS:
        if a >= len(line_ends) or b >= len(line_ends):
            continue
        pair_total += 1
        if phones_rhyme(line_ends[a].phones, line_ends[b].phones):
            agree += 1
        elif line_ends[a].oov or line_ends[b].oov:
            if normalize_word(line_ends[a].end_word) == normalize_word(line_ends[b].end_word):
                agree += 1
    query_token_indices: list[int] = []
    for le in line_ends:
        if le.token_end is not None and le.token_end > 0:
            query_token_indices.append(le.token_end - 1)
        elif le.token_start is not None:
            query_token_indices.append(le.token_start)
    return RhymeIndex(lines=lines, line_ends=line_ends, partner_of=partner_of, rhyme_coverage=coverage, phoneme_agree_pairs=agree, phoneme_pair_total=pair_total, query_token_indices=query_token_indices)

def rhyme_index_to_dict(idx: RhymeIndex) -> dict[str, Any]:
    return {'n_lines': len(idx.lines), 'rhyme_coverage': idx.rhyme_coverage, 'phoneme_agree_pairs': idx.phoneme_agree_pairs, 'phoneme_pair_total': idx.phoneme_pair_total, 'query_token_indices': idx.query_token_indices, 'partner_of': {str(k): v for k, v in idx.partner_of.items()}, 'line_ends': [{'line_index': le.line_index, 'end_word': le.end_word, 'token_start': le.token_start, 'token_end': le.token_end, 'oov': le.oov, 'phones': le.phones} for le in idx.line_ends]}
