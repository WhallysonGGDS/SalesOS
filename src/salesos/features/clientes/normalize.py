"""Normalização de dados de clientes (Fase 02, E1).

CPF, CNPJ e telefone ficam de fora até as regras oficiais serem consultadas e aprovadas
(decisões D6, D11 e D12): não há validação improvisada desses campos.
"""

import unicodedata

EMAIL_MAX_LENGTH = 254


def normalize_email(value: str) -> str:
    """Remove espaços das pontas e passa para minúsculas; recusa estrutura inválida.

    Confere só a forma (um `@`, local e domínio preenchidos, domínio com ponto interno, sem
    espaços). Não prova que o endereço existe.
    """
    email = value.strip().lower()
    local, at, domain = email.partition("@")
    labels = domain.split(".")
    if (
        not at
        or not local
        or "@" in domain
        or len(labels) < 2
        or not all(labels)
        or any(char.isspace() for char in email)
        or len(email) > EMAIL_MAX_LENGTH
    ):
        raise ValueError("e-mail inválido")
    return email


def search_key(*parts: str | None) -> str:
    """Texto de busca: sem acentos, em `casefold` e com espaços simples."""
    text = " ".join(part for part in parts if part)
    decomposed = unicodedata.normalize("NFKD", text)
    without_marks = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(without_marks.casefold().split())


def like_contains(term: str) -> str:
    """Padrão `LIKE` para "contém", escapando `\\`, `%` e `_` (usar com `ESCAPE '\\'`)."""
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"
