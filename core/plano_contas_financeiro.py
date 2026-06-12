import re
import unicodedata


_FINANCIAL_ORIGIN_PATTERNS = (
    r"\bCAIXA\b",
    r"\bBANCOS?\s+CONTA\s+CORRENTE\b",
    r"\bBCO\b",
    r"\bBANCO\b",
    r"\bAPLICACOES?\b",
    r"\bAPLICACOES?\s+FINANCEIRAS?\b",
)


def infer_is_financial_origin(nome: str, classificacao: str) -> bool:
    text = _normalize_text(f"{nome} {classificacao}")
    return any(re.search(pattern, text) for pattern in _FINANCIAL_ORIGIN_PATTERNS)


def _normalize_text(value: str) -> str:
    without_accents = "".join(
        char
        for char in unicodedata.normalize("NFKD", value)
        if not unicodedata.combining(char)
    )
    return re.sub(r"\s+", " ", without_accents.upper()).strip()
