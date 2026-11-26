# src/core/variety_analysis.py
"""Análisis puro (sin BD) de los nombres de variedad escritos en `plots.variety`.

Prepara la migración al catálogo de variedades: detecta grafías que son la misma variedad y nombres
que probablemente son una errata de otro.
"""
import unicodedata
from collections import Counter
from dataclasses import dataclass
from itertools import combinations

NEAR_DUPLICATE_MAX_DISTANCE = 2


def normalize_variety(name: str) -> str:
    """Minúsculas, sin acentos y con los espacios colapsados."""
    decomposed = unicodedata.normalize("NFKD", name.casefold())
    without_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    return " ".join(without_accents.split())


def edit_distance(a: str, b: str) -> int:
    """Distancia de Levenshtein."""
    previous = list(range(len(b) + 1))
    for i, char_a in enumerate(a, start=1):
        current = [i]
        for j, char_b in enumerate(b, start=1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (char_a != char_b)))
        previous = current
    return previous[-1]


@dataclass(frozen=True)
class VarietyReport:
    counts: dict[str, int]                    # nombre normalizado -> nº de lotes
    spellings: dict[str, Counter]             # nombre normalizado -> grafías originales y su frecuencia
    merged: list[str]                         # normalizados con más de una grafía distinta
    near_duplicates: list[tuple[str, str]]    # pares de normalizados distintos a distancia <= 2


def analyze_varieties(names: list[str]) -> VarietyReport:
    spellings: dict[str, Counter] = {}
    for name in names:
        spellings.setdefault(normalize_variety(name), Counter())[name] += 1
    keys = sorted(spellings)
    return VarietyReport(
        counts={k: sum(spellings[k].values()) for k in keys},
        spellings={k: spellings[k] for k in keys},
        merged=[k for k in keys if len(spellings[k]) > 1],
        near_duplicates=[(a, b) for a, b in combinations(keys, 2)
                         if edit_distance(a, b) <= NEAR_DUPLICATE_MAX_DISTANCE],
    )
